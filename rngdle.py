import re
import time
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL = "https://rngdle.com"
BUTTON = ("//button[contains(@class,'bg-black') and contains(@class,'uppercase') "
          "and contains(@class,'w-full')]")
SCORE_RE = re.compile(r"([\d,]+)\s*EP\b")
OUT_DIR = Path(__file__).parent / "screenshots"


def extract_score(text):
    m = SCORE_RE.search(text)
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


def run():
    OUT_DIR.mkdir(exist_ok=True)
    d = webdriver.Chrome()
    try:
        d.get(URL)
        WebDriverWait(d, 15).until(EC.element_to_be_clickable((By.XPATH, BUTTON))).click()
        time.sleep(1)
        d.refresh()
        time.sleep(1.5)
        text = d.find_element(By.TAG_NAME, "body").text
        score = extract_score(text)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = OUT_DIR / f"rngdle-{ts}.png"
        d.save_screenshot(str(out))
        print(f"score: {score} EP")
    finally:
        d.quit()


if __name__ == "__main__":
    while True:
        run()
        time.sleep(1)
