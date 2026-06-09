from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

URL = "https://rngdle.com"
BUTTON = ("//button[contains(@class,'bg-black') and contains(@class,'uppercase') "
          "and contains(@class,'w-full')]")


def run():
    d = webdriver.Chrome()
    d.get(URL)
    WebDriverWait(d, 15).until(EC.element_to_be_clickable((By.XPATH, BUTTON))).click()
    time.sleep(1)
    d.refresh()
    time.sleep(1.5)
    d.save_screenshot("rngdle.png")
    d.quit()


if __name__ == "__main__":
    run()
