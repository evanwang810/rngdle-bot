import csv
import threading

stop_event = threading.Event()

_lock = threading.Lock()
_counter = 0
_top = None
_score_sum = 0
_score_n = 0
_saved = 0

_csv_file = None
_csv_writer = None

_pids = set()
_userdirs = set()

# used by the chromedriver-patch race when uc was around; harmless now but keep it
driver_init_lock = threading.Lock()


def next_index():
    global _counter
    with _lock:
        _counter += 1
        return _counter


def total():
    return _counter


def open_log(path):
    global _csv_file, _csv_writer
    new = not path.exists()
    _csv_file = path.open("a", newline="", encoding="utf-8")
    _csv_writer = csv.writer(_csv_file)
    if new:
        _csv_writer.writerow(["ts", "worker", "idx", "score", "status", "file"])
        _csv_file.flush()


def log_row(row):
    with _lock:
        if _csv_writer is not None:
            _csv_writer.writerow(row)
            _csv_file.flush()


def close_log():
    if _csv_file is not None:
        _csv_file.close()


def record_roll(score, kept):
    global _top, _score_sum, _score_n, _saved
    with _lock:
        if score is not None:
            _score_sum += score
            _score_n += 1
            if _top is None or score > _top:
                _top = score
        if kept:
            _saved += 1
        avg = _score_sum / _score_n if _score_n else 0.0
        return avg, _top or 0, _saved


def peek_stats():
    with _lock:
        avg = _score_sum / _score_n if _score_n else 0.0
        return avg, _top or 0, _saved


def final_stats():
    with _lock:
        return {
            "rolls": _score_n,
            "screenshots": _saved,
            "top": _top,
            "avg": (_score_sum / _score_n) if _score_n else 0.0,
            "total_ep": _score_sum,
        }


def remember_pid(pid):
    with _lock:
        _pids.add(pid)

def forget_pid(pid):
    with _lock:
        _pids.discard(pid)

def drain_pids():
    with _lock:
        out = list(_pids)
        _pids.clear()
        return out


def remember_userdir(p):
    with _lock:
        _userdirs.add(p)

def drain_userdirs():
    with _lock:
        out = list(_userdirs)
        _userdirs.clear()
        return out
