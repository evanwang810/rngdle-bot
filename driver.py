from selenium import webdriver
from selenium.webdriver.chrome.options import Options

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# injected before any page script so navigator.webdriver etc. are already hidden
# by the time vercel's challenge code runs.
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


def _options(cfg):
    o = Options()
    o.page_load_strategy = "eager"
    o.add_argument("--incognito")
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
    d = webdriver.Chrome(options=_options(cfg))
    try:
        d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": STEALTH})
        d.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": UA,
            "acceptLanguage": "en-US,en;q=0.9",
            "platform": "Win32",
        })
    except Exception as e:
        print(f"stealth inject failed: {e}", flush=True)
    return d


def reset_session(d):
    try:
        d.delete_all_cookies()
    except Exception:
        pass
    try:
        d.execute_script("try{localStorage.clear()}catch(e){}try{sessionStorage.clear()}catch(e){}")
    except Exception:
        pass
