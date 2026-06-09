if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "rngdle"

import atexit
import threading
from pathlib import Path

from . import state
from .config import prompt_config
from .driver import kill_stragglers
from .worker import OUT_DIR, worker

LOG_CSV = Path(__file__).parent / "rolls.csv"


def main():
    OUT_DIR.mkdir(exist_ok=True)
    cfg = prompt_config()
    state.open_log(LOG_CSV)
    atexit.register(kill_stragglers)

    threads = [threading.Thread(target=worker, args=(cfg, i + 1), daemon=True)
               for i in range(cfg.workers)]
    for t in threads:
        t.start()
    try:
        while any(t.is_alive() for t in threads):
            for t in threads:
                t.join(timeout=0.25)
    except KeyboardInterrupt:
        state.stop_event.set()
        for t in threads:
            t.join(timeout=10)

    state.close_log()
    kill_stragglers()
    print(f"done. total cycles: {state.total()}")


if __name__ == "__main__":
    main()
