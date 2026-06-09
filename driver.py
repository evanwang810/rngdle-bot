import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from . import state

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

STEALTH = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [
  {name:'PDF Viewer', filename:'internal-pdf-viewer', description:''},
  {name:'Chrome PDF Viewer', filename:'internal-pdf-viewer', description:''},
  {name:'Chromium PDF Viewer', filename:'internal-pdf-viewer', description:''},
  {name:'Microsoft Edge PDF Viewer', filename:'internal-pdf-viewer', description:''},
  {name:'WebKit built-in PDF', filename:'internal-pdf-viewer', description:''},
]});
Object.defineProperty(navigator, 'languages', { get: () => ['en-US','en'] });
if (!window.chrome) window.chrome = { runtime: {} };
const q = window.navigator.permissions && window.navigator.permissions.query;
if (q) {
  window.navigator.permissions.query = (p) =>
    p && p.name === 'notifications'
      ? Promise.resolve({ state: Notification.permission })
      : q(p);
}
const gp = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(p) {
  if (p === 37445) return 'Intel Inc.';
  if (p === 37446) return 'Intel Iris OpenGL Engine';
  return gp.call(this, p);
};
"""


def _make_userdir():
    p = Path(tempfile.gettempdir()) / f"rngdle-{uuid.uuid4().hex[:10]}"
    p.mkdir(parents=True, exist_ok=True)
    state.remember_userdir(str(p))
    return p


def _options(cfg, userdir):
    o = Options()
    o.page_load_strategy = "eager"
    o.add_argument(f"--user-data-dir={userdir}")
    o.add_argument("--window-size=1280,900")
    o.add_argument("--no-first-run")
    o.add_argument("--no-default-browser-check")
    o.add_argument("--mute-audio")
    o.add_argument("--disable-background-networking")
    o.add_argument("--disable-sync")
    o.add_argument("--disable-translate")
    o.add_argument("--disable-default-apps")
    o.add_argument("--no-pings")
    o.add_argument(f"--user-agent={UA}")
    o.add_argument("--disable-blink-features=AutomationControlled")
    o.add_experimental_option("excludeSwitches", ["enable-automation"])
    o.add_experimental_option("useAutomationExtension", False)
    if cfg.headless:
        o.add_argument("--headless=new")
        o.add_argument("--disable-gpu")
    return o


def new_driver(cfg):
    ud = _make_userdir()
    d = webdriver.Chrome(options=_options(cfg, ud))
    try:
        d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": STEALTH})
        d.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": UA,
            "acceptLanguage": "en-US,en;q=0.9",
            "platform": "Win32",
        })
    except Exception as e:
        print(f"stealth inject failed: {e}", flush=True)
    try:
        state.remember_pid(d.service.process.pid)
    except Exception:
        pass
    return d


def forget_driver(d):
    try:
        state.forget_pid(d.service.process.pid)
    except Exception:
        pass


def reset_session(d):
    try:
        d.delete_all_cookies()
    except Exception:
        pass
    try:
        d.execute_script("try{localStorage.clear()}catch(e){}try{sessionStorage.clear()}catch(e){}")
    except Exception:
        pass


def _kill_pid(pid):
    subprocess.run(
        ["taskkill", "/T", "/F", "/PID", str(pid)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def _kill_by_userdir(ud):
    if sys.platform != "win32":
        return
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe' OR Name='chromedriver.exe'\" "
        "| Where-Object { $_.CommandLine -like '*" + ud.replace("'", "''") + "*' } "
        "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def kill_stragglers():
    if sys.platform != "win32":
        return
    for pid in state.drain_pids():
        try: _kill_pid(pid)
        except Exception: pass
    for d in state.drain_userdirs():
        try: _kill_by_userdir(d)
        except Exception: pass
        shutil.rmtree(d, ignore_errors=True)
