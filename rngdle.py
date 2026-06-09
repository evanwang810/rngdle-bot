# run with `python -m rngdle` or just `python rngdle\rngdle.py`
if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "rngdle"

import atexit
import os
import threading
import time
from pathlib import Path

from . import state, worker as worker_mod
from .config import bold, dim, green, prompt_config, yellow
from .driver import kill_stragglers
from .worker import OUT_DIR, worker

LOG_CSV = Path(__file__).parent / "rolls.csv"


def wipe_data():
    n = 0
    if OUT_DIR.exists():
        for p in OUT_DIR.glob("*.png"):
            try:
                p.unlink()
                n += 1
            except Exception:
                pass
    csv_gone = False
    if LOG_CSV.exists():
        try:
            LOG_CSV.unlink()
            csv_gone = True
        except Exception:
            pass
    msg = f"  cleared {n} screenshot(s)"
    if csv_gone:
        msg += ", deleted rolls.csv"
    print(dim(msg))


def kill_switch():
    """Ctrl+Q (or Ctrl+\\) to stop. Windows only."""
    if os.name != "nt":
        return
    try:
        import msvcrt
    except ImportError:
        return
    while not state.stop_event.is_set():
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            # Ctrl+Q = 0x11, Ctrl+\ = 0x1c
            if ch in (b"\x11", b"\x1c"):
                print("\n" + yellow("kill switch -- stopping"), flush=True)
                state.stop_event.set()
                return
        time.sleep(0.05)


def print_summary(elapsed, log_path):
    s = state.final_stats()
    print()
    print(bold("--- summary ---"))
    print(f"  runtime           {bold(f'{elapsed:.1f}s')}")
    print(f"  total cycles      {bold(str(state.total()))}")
    print(f"  rolls with score  {bold(str(s['rolls']))}")
    print(f"  screenshots saved {bold(green(str(s['screenshots'])))}")
    if s["top"] is not None:
        print(f"  top score         {bold(green(str(s['top']) + ' EP'))}")
    if s["rolls"]:
        print(f"  average score     {bold(str(int(s['avg'])) + ' EP')}")
        print(f"  total EP rolled   {bold(str(s['total_ep']))}")
    print(f"  log file          {dim(log_path.name)}")
    print()


def main():
    OUT_DIR.mkdir(exist_ok=True)
    cfg = prompt_config()
    if cfg.clear_data:
        wipe_data()
    actual_log = state.open_log(LOG_CSV)
    atexit.register(kill_stragglers)

    # set worker module globals (live status only when single worker - otherwise
    # multiple threads would smash the same line)
    worker_mod.LIVE_STATUS = (cfg.workers == 1)
    worker_mod.MAX_RUNTIME_S = cfg.max_runtime_min * 60.0
    worker_mod.STOP_AT_SCORE = cfg.stop_at_score

    iters = "infinite" if cfg.iterations == 0 else str(cfg.iterations)
    print(green("> starting") + dim(
        f"  workers={cfg.workers}  iters={iters}  "
        f"headless={'y' if cfg.headless else 'n'}  "
        f"min_score={cfg.min_score}  cycle_delay={cfg.cycle_delay}s"
    ))
    print(dim("  Ctrl+Q  or  Ctrl+C  to stop"))
    print()

    t0 = time.monotonic()
    worker_mod.START_TIME = t0

    threads = [
        threading.Thread(target=worker, args=(cfg, i + 1), daemon=True)
        for i in range(cfg.workers)
    ]
    for t in threads:
        t.start()
    threading.Thread(target=kill_switch, daemon=True).start()

    try:
        while any(t.is_alive() for t in threads):
            for t in threads:
                t.join(timeout=0.25)
    except KeyboardInterrupt:
        print("\n" + yellow("Ctrl+C -- stopping"), flush=True)
        state.stop_event.set()
        for t in threads:
            t.join(timeout=10)

    state.close_log()
    kill_stragglers()
    print_summary(time.monotonic() - t0, actual_log)

    try:
        input(dim("press Enter to close..."))
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    main()
