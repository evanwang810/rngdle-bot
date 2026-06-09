import re
import sys
import time
from datetime import datetime
from pathlib import Path

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from . import state
from .config import bold, cyan, dim, green, red, yellow
from .driver import forget_driver, new_driver, reset_session

URL = "https://rngdle.com"
BUTTON = ("//button[contains(@class,'bg-black') and contains(@class,'uppercase') "
          "and contains(@class,'w-full')]")
OUT_DIR = Path(__file__).parent / "screenshots"
SCORE_RE = re.compile(r"([\d,]+)\s*EP\b")
CHECKPOINT_WAIT = 30

# set by main() before workers start
LIVE_STATUS = False  # only do carriage-return tricks when workers==1
START_TIME = 0.0
MAX_RUNTIME_S = 0.0
STOP_AT_SCORE = None


def extract_score(text):
    # skip the lifetime EP line ("0 EP\nYOUR LIFETIME EP") - rngdle renders it
    # before the actual roll score, and the old regex grabbed it half the time
    for m in SCORE_RE.finditer(text):
        ahead = text[m.end():m.end()+20].lstrip().upper()
        if ahead.startswith("YOUR LIFETIME"):
            continue
        try:
            return int(m.group(1).replace(",", ""))
        except ValueError:
            pass
    return None


def click_generate(d):
    try:
        WebDriverWait(d, CHECKPOINT_WAIT).until(
            EC.element_to_be_clickable((By.XPATH, BUTTON))
        ).click()
        return True
    except TimeoutException:
        return False


def _status_line(wid, idx, phase):
    avg, top, saved = state.peek_stats()
    return (f"{dim(f'[w{wid}]')} {cyan(f'{idx:>4}')}  "
            f"{dim(phase):<22}"
            f"{dim(f'  avg {int(avg)}  top {top}  saved {saved}')}")


def _final_line(wid, idx, score, keep):
    sc = bold(green(f"{score} EP")) if score is not None else red("?? EP")
    skip = "" if keep else " " + dim("(skipped)")
    return f"{dim(f'[w{wid}]')} {cyan(f'{idx:>4}')}  {sc}{skip}"


def status(wid, idx, phase):
    if not LIVE_STATUS:
        return
    sys.stdout.write("\r" + _status_line(wid, idx, phase) + "\x1b[K")
    sys.stdout.flush()


def commit(wid, idx, score, keep):
    line = _final_line(wid, idx, score, keep)
    if LIVE_STATUS:
        sys.stdout.write("\r" + line + "\x1b[K\n")
        sys.stdout.flush()
    else:
        print(line, flush=True)


def one_cycle(d, cfg, wid):
    idx = state.next_index()

    status(wid, idx, "navigating...")
    d.get(URL)

    status(wid, idx, "waiting for button...")
    if not click_generate(d):
        status(wid, idx, "checkpoint? retrying...")
        time.sleep(3)
        d.get(URL)
        if not click_generate(d):
            commit(wid, idx, None, False)
            print(dim(f"  [w{wid}] still blocked, skipping"), flush=True)
            return

    status(wid, idx, "clicked, waiting...")
    if cfg.post_click_delay > 0:
        time.sleep(cfg.post_click_delay)

    status(wid, idx, "reloading...")
    d.refresh()

    status(wid, idx, "reading score...")
    text = ""
    score = None
    deadline = time.monotonic() + max(cfg.post_reload_delay, 0.2)
    while time.monotonic() < deadline:
        try:
            text = d.execute_script("return document.body.innerText") or ""
        except Exception:
            text = ""
        score = extract_score(text)
        if score is not None:
            break
        time.sleep(0.05)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
    keep = cfg.min_score is None or (score is not None and score >= cfg.min_score)

    fname = ""
    if keep:
        status(wid, idx, "saving screenshot...")
        out = OUT_DIR / f"rngdle-{ts}-w{wid}-{idx:05d}.png"
        d.save_screenshot(str(out))
        fname = out.name

    state.log_row([ts, wid, idx, score, "kept" if keep else "skipped", fname])
    state.record_roll(score, keep)
    commit(wid, idx, score, keep)

    # auto-stop checks
    if STOP_AT_SCORE is not None and score is not None and score >= STOP_AT_SCORE:
        print(yellow(f"[w{wid}] hit target {STOP_AT_SCORE} EP, stopping"), flush=True)
        state.stop_event.set()
        return
    if MAX_RUNTIME_S > 0 and (time.monotonic() - START_TIME) >= MAX_RUNTIME_S:
        print(yellow(f"[w{wid}] runtime cap hit, stopping"), flush=True)
        state.stop_event.set()


def worker(cfg, wid):
    done = 0
    d = None
    try:
        while not state.stop_event.is_set():
            if cfg.iterations and done >= cfg.iterations:
                return
            if d is None:
                try:
                    d = new_driver(cfg)
                except Exception as e:
                    print(f"[w{wid}] launch failed: {e}", flush=True)
                    state.stop_event.wait(2)
                    continue
            try:
                one_cycle(d, cfg, wid)
                done += 1
                if cfg.reuse_driver:
                    reset_session(d)
                else:
                    forget_driver(d)
                    try: d.quit()
                    except Exception: pass
                    d = None
                if cfg.cycle_delay > 0 and not state.stop_event.is_set():
                    state.stop_event.wait(cfg.cycle_delay)
            except Exception as e:
                print(f"[w{wid}] error: {e}", flush=True)
                forget_driver(d)
                try: d.quit()
                except Exception: pass
                d = None
    finally:
        if d is not None:
            forget_driver(d)
            try: d.quit()
            except Exception: pass
