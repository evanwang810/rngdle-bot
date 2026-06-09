import csv
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from selenium import webdriver
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
                w.writerow(["ts", "worker", "idx", "score", "file"])
            w.writerow(row)


def one_cycle(wid):
    d = webdriver.Chrome()
    try:
        d.get(URL)
        WebDriverWait(d, 15).until(EC.element_to_be_clickable((By.XPATH, BUTTON))).click()
        time.sleep(1)
        d.refresh()
        time.sleep(1.5)
        text = d.find_element(By.TAG_NAME, "body").text
        score = extract_score(text)
        idx = next_idx()
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = OUT_DIR / f"rngdle-{ts}-w{wid}-{idx:05d}.png"
        d.save_screenshot(str(out))
        log_row([ts, wid, idx, score, out.name])
        print(f"[w{wid}] {idx:>4}  {score} EP")
    finally:
        try:
            d.quit()
        except Exception:
            pass


def worker(wid):
    while not stop_event.is_set():
        try:
            one_cycle(wid)
        except Exception as e:
            print(f"[w{wid}] err: {e}")
        stop_event.wait(1)


def main():
    OUT_DIR.mkdir(exist_ok=True)
    n = int(input("workers: ") or "1")
    threads = [threading.Thread(target=worker, args=(i + 1,), daemon=True) for i in range(n)]
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
