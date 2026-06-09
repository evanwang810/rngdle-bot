# rngdle auto-roller

Parallel auto-roller for [rngdle.com](https://rngdle.com). Drives Chrome through
the site, clicks Generate, screenshots the result, and logs every roll to CSV.

## Setup

1. Install [Python 3.11+](https://www.python.org/downloads/) and [Google Chrome](https://www.google.com/chrome/).
2. Clone the repo, then from inside it:
   ```
   pip install -r requirements.txt
   ```
   Selenium 4 includes Selenium Manager, which auto-downloads the matching
   chromedriver. No manual driver setup.

## Run

From the parent directory of the `rngdle/` package:

```
python -m rngdle
```

Or run the script file directly from anywhere:

```
python path\to\rngdle\rngdle.py
```

Both work, the entrypoint self-bootstraps its package.

> **Tip: VPN strongly recommended.** rngdle is hosted on Vercel, whose bot
> checkpoint trips on repeated requests from one IP. Without a VPN you'll hit
> the rate limit after a few rolls.

> **Note: headless is unreliable.** Vercel fingerprints headless Chrome. If
> the run gets stuck on the checkpoint with headless on, just run headed.

## Controls

- `Ctrl+C`: stop after the current roll finishes.
- `Ctrl+Q` (or `Ctrl+\`): same thing, no Enter needed (Windows only).

## Config options

Asked interactively on startup. Press Enter to accept the default.

| Option | Default | Meaning |
| --- | --- | --- |
| clear all data first | n | Delete every `.png` in `screenshots/` and remove `rolls.csv` before starting. |
| workers | 1 | Parallel Chrome instances. **More than 1 will trip Vercel's checkpoint fast and barely speeds things up so its recommended to just  stick with 1.** |
| background mode | n | Forces headless + muted. Usually fails Vercel. |
| headless | n | Run Chrome without a visible window. |
| iterations per worker | 0 | 0 = infinite. |
| delay after click | 1.0 | Seconds before reloading. |
| max wait for score | 1.5 | Polls until the EP score appears or this timeout. |
| delay between cycles | 0 | Sleep N seconds between rolls. Bump it if rate-limited. |
| min score (EP) | (blank) | Only save screenshots at or above this EP. Blank = save all. |
| reuse Chrome between rolls | y | Keep Chrome open across cycles, just clear cookies. Much faster. |
| window size | 1280x900 | `<width>x<height>`. |
| disable image loading | n | Faster cycles but bot-detection may flag it. |
| max runtime (min) | 0 | Stop after N minutes. 0 = no cap. |
| stop after a roll >= (EP) | (blank) | Auto-stop the moment any roll scores at least this much. |

## Output

- `screenshots/rngdle-<timestamp>-w<worker>-<idx>.png` — one PNG per kept roll.
- `rolls.csv` — append-only log: `ts, worker, idx, score, status, file`.

During the run each roll prints its score plus live stats (running average,
top score, screenshots saved). At the end you get a full summary block.

## Files

```
rngdle/
  rngdle.py    # entrypoint — orchestration, kill switch, summary
  config.py    # interactive prompts + Config dataclass + ANSI helpers
  driver.py    # Chrome factory with CDP stealth, session reset, process cleanup
  worker.py    # per-thread roll loop: navigate → click → reload → extract → screenshot
  state.py     # shared state: locks, counter, CSV log, stats, PID + userdir tracking
  __main__.py  # so `python -m rngdle` works
  __init__.py  # marks the folder as a package
```

### How the stealth works

`driver.py` uses Chrome DevTools Protocol's `Page.addScriptToEvaluateOnNewDocument`
to inject a script that runs **before** any page JS on every navigation. It
patches the standard automation tells: `navigator.webdriver`, `plugins`,
`languages`, `window.chrome`, the Permissions API notifications quirk, and the
WebGL vendor/renderer. Same approach `undetected-chromedriver` uses, just
inlined so there's no extra dependency.

### How process cleanup works

Each Chrome instance is launched with a unique `--user-data-dir` under
`%TEMP%\rngdle-<uuid>`. Every `chromedriver` PID is tracked too. On shutdown
(graceful exit, Ctrl+C, Q, or crash):

1. `taskkill /T /F` walks every tracked chromedriver process tree.
2. A PowerShell sweep finds any surviving `chrome.exe` / `chromedriver.exe`
   whose command line references one of our temp dirs and kills those too —
   this catches the orphan case where chromedriver died first.
3. The temp dirs are removed.

## Troubleshooting

- **"attempted relative import with no known parent package"** — you ran
  `python rngdle.py` from inside the package folder. Either go up one level
  (`python -m rngdle`) or use the full path (`python C:\path\to\rngdle\rngdle.py`).
- **`PermissionError: chromedriver.exe ... being used by another process`** — a
  prior run left Chrome around. Open Task Manager, end stray `chrome.exe` /
  `chromedriver.exe`, retry.
- **Always stuck on Vercel checkpoint** — VPN on, drop `workers` to 1, raise
  `delay between cycles` to 3–5s.
- **Same score over and over** — rngdle gives one roll per day per session;
  once you've hit the cap the page just keeps returning your last result.
  Use the "stop after a roll >= (EP)" option if you want to stop on a good score.

## License

MIT.
