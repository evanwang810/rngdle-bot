import csv
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL = "https://rngdle.com"
BUTTON = ("//button[contains(@class,'bg-black') and contains(@class,'uppercase') "
          "and contains(@class,'w-full')]")
SCORE_RE = re.compile(r"([\d,]+)\s*EP\b")
OUT_DIR = Path(__file__).parent / "screenshots"
LOG = Path(__file__).parent / "rolls.csv"

stop_event = threading.Event()
_lock = threading.Lock()
_counter = 0


@dataclass
class Config:
    workers: int
    headless: bool
    iterations: int
    post_click_delay: float
    post_reload_delay: float
    cycle_delay: float
    min_score: int | None


def ask(p, default):
    v = input(f"  {p} [{default}]: ").strip()
    return v or default


def ask_bool(p, default):
    return ask(p + " (y/n)", default).lower().startswith("y")


def ask_int(p, default):
    return int(ask(p, default))


def ask_float(p, default):
    return float(ask(p, default))


def ask_opt_int(p, default):
    v = ask(p, default).strip()
    if not v or v.lower() in ("none", "off", "-"):
        return None
    try:
        return int(v)
    except ValueError:
        return None


def prompt_config():
    print("rngdle auto-roller")
    workers = ask_int("workers", "1")
    headless = ask_bool("headless?", "n")
    iterations = ask_int("iters per worker (0=infinite)", "0")
    post_click = ask_float("delay after click (s)", "1.0")
    post_reload = ask_float("max wait for score (s)", "1.5")
    cycle_delay = ask_float("delay between cycles (s)", "0")
    min_score = ask_opt_int("only save if score (EP) >= (blank=off)", "")
    return Config(workers, headless, iterations, post_click, post_reload, cycle_delay, min_score)


def next_idx():
    global _counter
    with _lock:
        _counter += 1
        return _counter


def extract_score(text):
    m = SCORE_RE.search(text)
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


def log_row(row):
    new = not LOG.exists()
    with _lock:
        with open(LOG, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["ts", "worker", "idx", "score", "status", "file"])
            w.writerow(row)


def new_driver(cfg):
    o = Options()
    o.add_argument("--incognito")
    o.add_argument("--window-size=1280,900")
    if cfg.headless:
        o.add_argument("--headless=new")
        o.add_argument("--disable-gpu")
    return webdriver.Chrome(options=o)


def one_cycle(d, cfg, wid):
    d.get(URL)
    WebDriverWait(d, 15).until(EC.element_to_be_clickable((By.XPATH, BUTTON))).click()
    if cfg.post_click_delay > 0:
        time.sleep(cfg.post_click_delay)
    d.refresh()
    time.sleep(cfg.post_reload_delay)
    text = d.find_element(By.TAG_NAME, "body").text
    score = extract_score(text)
    idx = next_idx()
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    keep = cfg.min_score is None or (score is not None and score >= cfg.min_score)
    fname = ""
    if keep:
        out = OUT_DIR / f"rngdle-{ts}-w{wid}-{idx:05d}.png"
        d.save_screenshot(str(out))
        fname = out.name
    log_row([ts, wid, idx, score, "kept" if keep else "skipped", fname])
    print(f"[w{wid}] {idx:>4}  {score} EP" + ("" if keep else " (skipped)"))


def worker(cfg, wid):
    done = 0
    while not stop_event.is_set():
        if cfg.iterations and done >= cfg.iterations:
            return
        d = new_driver(cfg)
        try:
            one_cycle(d, cfg, wid)
            done += 1
        except Exception as e:
            print(f"[w{wid}] err: {e}")
        finally:
            try:
                d.quit()
            except Exception:
                pass
        if cfg.cycle_delay > 0 and not stop_event.is_set():
            stop_event.wait(cfg.cycle_delay)


def main():
    OUT_DIR.mkdir(exist_ok=True)
    cfg = prompt_config()
    threads = [threading.Thread(target=worker, args=(cfg, i + 1), daemon=True)
               for i in range(cfg.workers)]
    for t in threads:
        t.start()
    try:
        while any(t.is_alive() for t in threads):
            for t in threads:
                t.join(timeout=0.25)
    except KeyboardInterrupt:
        stop_event.set()
        for t in threads:
            t.join(timeout=10)


if __name__ == "__main__":
    main()
