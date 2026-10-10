#!/usr/bin/env python3
"""Read-only smoke check of the three public pages linked from the portfolio."""
from pathlib import Path
import time
import urllib.request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

BASE = "https://alisoneleece-source.github.io"
URLS = {
    "Portfolio": BASE + "/portfolio/",
    "Commercial PO": BASE + "/commercial-purchase-order-operations/",
    "Knowledge Wiki": BASE + "/Wiki-for-Acme-Excel/",
}
out = Path("site-check-screenshots")
out.mkdir(exist_ok=True)
results = []
def record(name, result):
    print(("PASS" if result else "FAIL") + ": " + name, flush=True)
    results.append((name, result))

for name, url in URLS.items():
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as response:
            code = response.status
            html = response.read().decode("utf-8", "replace")
        record(f"{name}: public HTTP 200 and nonempty HTML", code == 200 and "<html" in html.lower() and len(html) > 500)
    except Exception as exc:
        print(f"{name}: GET error {type(exc).__name__}: {exc}", flush=True)
        record(f"{name}: public HTTP 200 and nonempty HTML", False)

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1280,900")
driver = webdriver.Chrome(options=opts)
driver.set_page_load_timeout(65)
wait = WebDriverWait(driver, 45)
try:
    for width, label in ((1280, "desktop"), (390, "mobile")):
        driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
            "width": width, "height": 850, "deviceScaleFactor": 1,
            "mobile": width == 390,
        })
        for name, url in URLS.items():
            try:
                driver.get(url)
                wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                if name == "Knowledge Wiki":
                    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, ".top-links .top-link")) >= 8)
                else:
                    wait.until(lambda d: len(d.find_element(By.TAG_NAME, "body").text.strip()) > 100)
                driver.save_screenshot(str(out / (name.lower().replace(" ", "-") + "-" + label + ".png")))
                record(f"{name}: renders at {width}px", True)
                if name == "Portfolio":
                    found = {
                        a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "a[href]")
                    }
                    record(f"Portfolio: both live project links at {width}px",
                        URLS["Commercial PO"] in found and URLS["Knowledge Wiki"] in found)
                if name == "Knowledge Wiki" and width == 390:
                    tabs = driver.find_elements(By.CSS_SELECTOR, ".top-links .top-link")
                    nav = driver.find_element(By.CSS_SELECTOR, ".top-links")
                    shown = driver.execute_script(
                        "const e=arguments[0];const r=e.getBoundingClientRect();return getComputedStyle(e).display!=='none' && r.width>0 && r.height>0", nav
                    )
                    record("Knowledge Wiki: mobile navigation is displayed", shown and len(tabs) >= 8)
                    target = next((x for x in tabs if x.text.strip() == "Contacts"), None)
                    if target:
                        driver.execute_script("arguments[0].scrollIntoView({block:'nearest',inline:'center'});", target)
                        driver.execute_script("arguments[0].click();", target)
                        wait.until(lambda d: any(x.text.strip() == "Contacts" for x in d.find_elements(By.CSS_SELECTOR, ".top-link.active")))
                        record("Knowledge Wiki: mobile Contacts tab works", True)
                    else:
                        record("Knowledge Wiki: mobile Contacts tab works", False)
            except Exception as exc:
                print(f"{name} {label}: {type(exc).__name__}: {str(exc)[:550]}", flush=True)
                record(f"{name}: renders at {width}px", False)
                if name == "Knowledge Wiki" and width == 390:
                    record("Knowledge Wiki: mobile navigation is displayed", False)
                    record("Knowledge Wiki: mobile Contacts tab works", False)
finally:
    driver.quit()

passed = sum(ok for _, ok in results)
summary = Path("site-check-results.md")
summary.write_text(
    "# Portfolio live website check\n\n"
    + f"**{passed}/{len(results)} checks passed**\n\n"
    + "| Check | Result |\n|---|---|\n"
    + "\n".join(f"| {name} | {'PASS' if ok else 'FAIL'} |" for name, ok in results)
    + "\n\nScreenshots are included in the workflow artifacts.\n"
)
print(summary.read_text(), flush=True)
if passed != len(results):
    raise SystemExit(1)
