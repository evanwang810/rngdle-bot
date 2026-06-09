from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def new_driver(cfg):
    o = Options()
    o.add_argument("--incognito")
    o.add_argument("--window-size=1280,900")
    o.add_argument("--no-first-run")
    o.add_argument("--no-default-browser-check")
    o.add_argument("--mute-audio")
    if cfg.headless:
        o.add_argument("--headless=new")
        o.add_argument("--disable-gpu")
    return webdriver.Chrome(options=o)
