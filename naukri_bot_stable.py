"""
Naukri Quick Apply Bot — STABLE VERSION (No Chrome Crashes)
============================================================
Logs into Naukri, searches for matching jobs, and Quick Applies automatically.

CRASH FIXES:
- Removed ALL aggressive GPU/memory flags
- Using vanilla Chrome with minimal options
- No headless mode (visible browser only)
- Proper resource cleanup
- Slower, safer automation

Requirements:
    pip install selenium webdriver-manager pandas colorama
"""

import time, csv, os, json, random, sys
from datetime import datetime, date
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager
from colorama import Fore, Style, init

init(autoreset=True)

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
CONFIG = {
    "email":    "Preamkumar990@gmail.com",
    "password": "",          # ← PUT YOUR PASSWORD HERE

    "search_queries": [
        "Data Engineer",
        "Azure Data Engineer",
        "QA Analyst Automation",
        "ETL Developer Azure",
        "Data Pipeline Engineer",
        "QA Automation Engineer Selenium",
    ],
    "location": "Bengaluru",
    "experience_years": "3",

    "min_ctc_lpa": 12,
    "max_ctc_lpa": 20,

    "daily_limit": 30,
    "delay_between_apps": (5, 10),
    "delay_between_searches": (3, 7),

    "log_file": "applications_log.csv",
    "applied_ids_file": "applied_job_ids.json",
}

LOG_FIELDS = ["date", "time", "company", "role", "location",
              "experience", "ctc", "skills", "job_id", "status", "url", "notes"]

# ─────────────────────────────────────────────
#  LOGGER
# ─────────────────────────────────────────────
def log(msg, level="INFO"):
    now = datetime.now().strftime("%H:%M:%S")
    colors = {"INFO": Fore.CYAN, "OK": Fore.GREEN, "WARN": Fore.YELLOW,
              "ERR": Fore.RED, "BOT": Fore.MAGENTA}
    c = colors.get(level, Fore.WHITE)
    print(f"{Fore.WHITE}[{now}] {c}[{level}]{Style.RESET_ALL} {msg}")

# ─────────────────────────────────────────────
#  CSV LOGGING
# ─────────────────────────────────────────────
def init_csv(path):
    if not Path(path).exists():
        with open(path, "w", newline="", encoding="utf-8") as f:
            __import__('csv').DictWriter(f, fieldnames=LOG_FIELDS).writeheader()
        log(f"Created log file: {path}", "OK")

def append_csv(path, row):
    with open(path, "a", newline="", encoding="utf-8") as f:
        __import__('csv').DictWriter(f, fieldnames=LOG_FIELDS).writerow(row)

# ─────────────────────────────────────────────
#  APPLIED IDs TRACKER
# ─────────────────────────────────────────────
def load_applied_ids(path):
    if Path(path).exists():
        with open(path) as f:
            return set(json.load(f))
    return set()

def save_applied_ids(path, ids):
    with open(path, "w") as f:
        json.dump(list(ids), f)

def get_today_count(log_path):
    today = date.today().isoformat()
    count = 0
    if Path(log_path).exists():
        with open(log_path, newline="", encoding="utf-8") as f:
            for row in __import__('csv').DictReader(f):
                if row.get("date") == today and row.get("status") == "Applied":
                    count += 1
    return count

# ─────────────────────────────────────────────
#  BROWSER SETUP - STABLE (NO CRASH)
# ─────────────────────────────────────────────
def create_driver():
    """
    MINIMAL Chrome setup - no crashes
    Keep it SIMPLE
    """
    opts = Options()
    
    # ONLY add essential options - remove everything else
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-notifications")
    
    # Real user agent
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
        
        # Timeouts
        driver.set_page_load_timeout(30)
        driver.set_script_timeout(30)
        
        log("✓ Browser launched successfully", "OK")
        return driver
    except Exception as e:
        log(f"Failed to create driver: {e}", "ERR")
        raise

def quit_driver(driver):
    """Clean shutdown"""
    try:
        if driver:
            driver.quit()
            time.sleep(2)
    except:
        pass

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def sleep_human(min_s, max_s):
    time.sleep(random.uniform(min_s, max_s))

def type_human(element, text):
    element.clear()
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.12))

def safe_click(driver, element):
    try:
        element.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", element)
    except:
        pass

def wait_for(driver, by, selector, timeout=15):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
    except:
        return None

# ─────────────────────────────────────────────
#  LOGIN
# ─────────────────────────────────────────────
def login(driver, email, password):
    log("🔓 Logging into Naukri.com …", "BOT")
    try:
        driver.get("https://www.naukri.com/nlogin/login")
        sleep_human(2, 3)

        # Close popup if exists
        try:
            driver.find_element(By.CSS_SELECTOR, "[class*='close']").click()
            sleep_human(0.5, 1)
        except:
            pass

        # Email
        email_field = wait_for(driver, By.CSS_SELECTOR, "input[placeholder*='Email']", 10)
        if not email_field:
            email_field = wait_for(driver, By.CSS_SELECTOR, "input[name*='email'], input[type='email']", 10)
        
        if not email_field:
            log("Email field not found", "ERR")
            return False

        type_human(email_field, email)
        sleep_human(1, 2)

        # Password
        pwd_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        type_human(pwd_field, password)
        sleep_human(1, 2)

        # Click submit
        btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        safe_click(driver, btn)
        sleep_human(4, 6)

        # Verify login
        if "login" not in driver.current_url.lower():
            log("✓ Login successful", "OK")
            return True
        else:
            log("⚠ Check browser for CAPTCHA - waiting 30s …", "WARN")
            time.sleep(30)
            return True

    except Exception as e:
        log(f"Login failed: {e}", "ERR")
        return False

# ─────────────────────────────────────────────
#  SEARCH JOBS
# ─────────────────────────────────────────────
def search_jobs(driver, query, location, experience):
    log(f"🔍 Searching: '{query}' in {location} …", "BOT")
    try:
        url = (
            f"https://www.naukri.com/{query.lower().replace(' ', '-')}-jobs-in-{location.lower()}"
            f"?experience={experience}&salary={CONFIG['min_ctc_lpa']},{CONFIG['max_ctc_lpa']}&jobAge=7"
        )
        driver.get(url)
        sleep_human(3, 4)

        # Wait for jobs to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".jobTuple, article, .job-card"))
        )
        
        # Get job cards - try multiple selectors
        cards = None
        for selector in [".jobTuple", "article.jobTupleHeader", ".job-tuple-wrapper"]:
            try:
                cards = driver.find_elements(By.CSS_SELECTOR, selector)
                if cards:
                    log(f"Found {len(cards)} jobs", "INFO")
                    return cards[:20]  # Limit to 20 per search
            except:
                continue
        
        return cards or []

    except Exception as e:
        log(f"Search error: {e}", "WARN")
        return []

# ─────────────────────────────────────────────
#  EXTRACT JOB INFO
# ─────────────────────────────────────────────
def extract_job_info(card):
    info = {
        "company": "", "role": "", "location": "", "experience": "",
        "ctc": "", "skills": "", "job_id": "", "url": ""
    }
    try:
        # Role
        try:
            title_elem = card.find_element(By.CSS_SELECTOR, "a.title, .jobTitle, a[class*='title']")
            info["role"] = title_elem.text.strip()
            info["url"] = title_elem.get_attribute("href") or ""
        except:
            pass

        # Company
        try:
            info["company"] = card.find_element(By.CSS_SELECTOR, ".subTitle, .companyName").text.strip()
        except:
            pass

        # Experience
        try:
            info["experience"] = card.find_element(By.CSS_SELECTOR, ".exp, .expwdth").text.strip()
        except:
            pass

        # CTC
        try:
            info["ctc"] = card.find_element(By.CSS_SELECTOR, ".salary, .sal").text.strip()
        except:
            pass

        # Location
        try:
            info["location"] = card.find_element(By.CSS_SELECTOR, ".location, .loc").text.strip()
        except:
            pass

        # Skills
        try:
            skills = card.find_elements(By.CSS_SELECTOR, ".tag, .skill-badge, li")
            info["skills"] = ", ".join([s.text.strip() for s in skills[:5] if s.text.strip()])
        except:
            pass

        # Job ID
        if info["url"]:
            parts = info["url"].split("-")
            for p in reversed(parts):
                if p.isdigit() and len(p) > 4:
                    info["job_id"] = p
                    break

    except:
        pass

    return info

# ─────────────────────────────────────────────
#  QUICK APPLY
# ─────────────────────────────────────────────
def quick_apply(driver, card, job_info):
    try:
        # Find apply button
        apply_btn = None
        
        # Try to find on card
        for selector in ["button.btn-secondary", "button[class*='apply']", ".apply-btn"]:
            try:
                btn = card.find_element(By.CSS_SELECTOR, selector)
                if "apply" in btn.text.lower():
                    apply_btn = btn
                    break
            except:
                continue

        if not apply_btn:
            return False, "No apply button"

        # Scroll and click
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", apply_btn)
        sleep_human(0.5, 1)
        safe_click(driver, apply_btn)
        sleep_human(2, 3)

        # Handle modal
        try:
            # Look for success
            driver.find_element(By.CSS_SELECTOR, "[class*='success'], [class*='applied']")
            return True, "Applied"
        except:
            # Try to confirm
            try:
                confirm = driver.find_element(By.CSS_SELECTOR, "button[class*='apply'], button[class*='submit']")
                safe_click(driver, confirm)
                sleep_human(2, 3)
                return True, "Applied"
            except:
                return True, "Applied (no confirmation visible)"

    except Exception as e:
        return False, str(e)[:50]

# ─────────────────────────────────────────────
#  MAIN BOT
# ─────────────────────────────────────────────
def run_bot():
    if not CONFIG["password"]:
        log("❌ Set password in CONFIG!", "ERR")
        sys.exit(1)

    init_csv(CONFIG["log_file"])
    applied_ids = load_applied_ids(CONFIG["applied_ids_file"])
    today_count = get_today_count(CONFIG["log_file"])

    log(f"Applied today: {today_count}/{CONFIG['daily_limit']}", "INFO")

    if today_count >= CONFIG["daily_limit"]:
        log("Daily limit reached", "WARN")
        return

    driver = None
    try:
        driver = create_driver()
        
        if not login(driver, CONFIG["email"], CONFIG["password"]):
            log("Login failed", "ERR")
            return

        sleep_human(2, 3)

        for query in CONFIG["search_queries"]:
            if today_count >= CONFIG["daily_limit"]:
                break

            cards = search_jobs(driver, query, CONFIG["location"], CONFIG["experience_years"])

            if not cards:
                log(f"No jobs for '{query}'", "WARN")
                sleep_human(*CONFIG["delay_between_searches"])
                continue

            for idx, card in enumerate(cards):
                if today_count >= CONFIG["daily_limit"]:
                    break

                job_info = extract_job_info(card)

                if not job_info["role"]:
                    continue

                # Skip if already applied
                if job_info["job_id"] and job_info["job_id"] in applied_ids:
                    continue

                log(f"  {job_info['company']} | {job_info['role'][:40]}", "INFO")

                success, note = quick_apply(driver, card, job_info)

                now = datetime.now()
                row = {
                    "date": now.date().isoformat(),
                    "time": now.strftime("%H:%M:%S"),
                    "company": job_info["company"][:50],
                    "role": job_info["role"][:50],
                    "location": job_info["location"][:30],
                    "experience": job_info["experience"][:20],
                    "ctc": job_info["ctc"][:20],
                    "skills": job_info["skills"][:100],
                    "job_id": job_info["job_id"],
                    "status": "Applied" if success else "Failed",
                    "url": job_info["url"],
                    "notes": note[:100],
                }
                append_csv(CONFIG["log_file"], row)

                if success:
                    today_count += 1
                    if job_info["job_id"]:
                        applied_ids.add(job_info["job_id"])
                        save_applied_ids(CONFIG["applied_ids_file"], applied_ids)
                    log(f"    ✅ Applied [{today_count}/{CONFIG['daily_limit']}]", "OK")
                else:
                    log(f"    ❌ Failed: {note}", "WARN")

                sleep_human(*CONFIG["delay_between_apps"])

            sleep_human(*CONFIG["delay_between_searches"])

        log("=" * 60, "INFO")
        log(f"Done! Applied {today_count} jobs today", "OK")

    except KeyboardInterrupt:
        log("Stopped by user", "WARN")
    except Exception as e:
        log(f"Error: {e}", "ERR")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            quit_driver(driver)
            log("Browser closed", "INFO")

if __name__ == "__main__":
    run_bot()
