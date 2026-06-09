import re
import time
from datetime import datetime
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from . import state
from .driver import new_driver

URL = "https://rngdle.com"
BUTTON = ("//button[contains(@class,'bg-black') and contains(@class,'uppercase') "
          "and contains(@class,'w-full')]")
OUT_DIR = Path(__file__).parent / "screenshots"
SCORE_RE = re.compile(r"([\d,]+)\s*EP\b")


def extract_score(text):
    m = SCORE_RE.search(text)
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


def one_cycle(d, cfg, wid):
    d.get(URL)
    WebDriverWait(d, 15).until(
        EC.element_to_be_clickable((By.XPATH, BUTTON))
    ).click()
    if cfg.post_click_delay > 0:
        time.sleep(cfg.post_click_delay)
    d.refresh()
    time.sleep(cfg.post_reload_delay)
    text = d.find_element(By.TAG_NAME, "body").text
    score = extract_score(text)
    idx = state.next_index()
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    keep = cfg.min_score is None or (score is not None and score >= cfg.min_score)
    fname = ""
    if keep:
        out = OUT_DIR / f"rngdle-{ts}-w{wid}-{idx:05d}.png"
        d.save_screenshot(str(out))
        fname = out.name
    state.log_row([ts, wid, idx, score, "kept" if keep else "skipped", fname])
    print(f"[w{wid}] {idx:>4}  {score} EP" + ("" if keep else " (skipped)"))


def worker(cfg, wid):
    done = 0
    while not state.stop_event.is_set():
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
        if cfg.cycle_delay > 0 and not state.stop_event.is_set():
            state.stop_event.wait(cfg.cycle_delay)
