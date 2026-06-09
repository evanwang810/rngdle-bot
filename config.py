from dataclasses import dataclass


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
