import os
import sys
from dataclasses import dataclass

# turn on ANSI on win10+ (cheap hack but it works)
if os.name == "nt":
    os.system("")

USE_COLOR = sys.stdout.isatty()

def c(code, s):
    return f"\x1b[{code}m{s}\x1b[0m" if USE_COLOR else s

bold   = lambda s: c("1",  s)
dim    = lambda s: c("2",  s)
cyan   = lambda s: c("36", s)
green  = lambda s: c("32", s)
yellow = lambda s: c("33", s)
red    = lambda s: c("31", s)


@dataclass
class Config:
    workers: int
    headless: bool
    iterations: int
    post_click_delay: float
    post_reload_delay: float
    cycle_delay: float
    min_score: int | None
    reuse_driver: bool
    clear_data: bool
    # extras
    window_size: str        # e.g. "1280x900"
    disable_images: bool
    max_runtime_min: float  # 0 = no cap
    stop_at_score: int | None


def ask(prompt, default):
    raw = input(f"  {prompt} {dim('[' + default + ']')}{cyan(' >')} ").strip()
    return raw or default


def ask_bool(prompt, default):
    while True:
        v = ask(prompt + dim(" (y/n)"), default).lower()
        if v in ("y", "yes", "1", "true"):  return True
        if v in ("n", "no", "0", "false"): return False
        print("    " + red("y or n"))


def ask_int(prompt, default):
    while True:
        try:
            return int(ask(prompt, default))
        except ValueError:
            print("    " + red("need a whole number"))


def ask_float(prompt, default):
    while True:
        try:
            return float(ask(prompt, default))
        except ValueError:
            print("    " + red("need a number"))


def ask_opt_int(prompt, default):
    v = ask(prompt + dim(" (blank=off)"), default).strip().lower()
    if v in ("", "none", "off", "-"):
        return None
    try:
        return int(v)
    except ValueError:
        return None


def prompt_config():
    print()
    print(bold("rngdle auto-roller"))
    print(dim("  tip: VPN strongly recommended (Vercel rate-limits the IP)"))
    print(dim("  tip: headless usually fails the Vercel checkpoint"))
    print(dim("  tip: Ctrl+Q (or Ctrl+C) to stop"))
    print()

    clear_data = ask_bool("clear screenshots + rolls.csv first?", "n")

    workers = ask_int("workers", "1")
    if workers > 1:
        print("    " + yellow("heads up: >1 worker trips the Vercel checkpoint fast"))
        print("    " + yellow("           and barely speeds things up. 1 is usually best."))

    background  = ask_bool("background mode (headless + muted)?", "n")
    headless    = background or ask_bool("headless?", "n")
    iterations  = ask_int("iters per worker " + dim("(0=infinite)"), "0")
    post_click  = ask_float("delay after click (s)", "1.0")
    post_reload = ask_float("max wait for score (s)", "1.5")
    cycle_delay = ask_float("delay between cycles (s)", "0")
    min_score   = ask_opt_int("only save if score (EP) >=", "")
    reuse       = ask_bool("reuse Chrome between rolls?", "y")

    # extras (just press enter to skip past these)
    print(dim("  -- extras (Enter to skip) --"))
    window_size    = ask("window size", "1280x900")
    disable_images = ask_bool("disable image loading? " + dim("(faster, may flag bot)"), "n")
    max_runtime    = ask_float("max runtime (min, 0=off)", "0")
    stop_at        = ask_opt_int("stop after a roll >= (EP)", "")

    return Config(
        workers=workers, headless=headless, iterations=iterations,
        post_click_delay=post_click, post_reload_delay=post_reload,
        cycle_delay=cycle_delay, min_score=min_score, reuse_driver=reuse,
        clear_data=clear_data, window_size=window_size,
        disable_images=disable_images, max_runtime_min=max_runtime,
        stop_at_score=stop_at,
    )
