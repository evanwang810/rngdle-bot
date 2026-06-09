import csv
import threading

stop_event = threading.Event()

_lock = threading.Lock()
_counter = 0

_csv_file = None
_csv_writer = None


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
