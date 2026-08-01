# import pandas as pd
# import re
# import phonenumbers
# import time
# import os
# import csv
# from datetime import datetime

# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException


# # =========================================
# # READ NUMBERS FROM PASTED TEXT
# # =========================================

# def read_numbers_from_text(text):
#     numbers = []
#     raw_numbers = re.split(r'[,\n]+', text)

#     for num in raw_numbers:
#         num = num.strip()
#         num = num.replace(" ", "")
#         if num:
#             numbers.append(num)

#     return numbers


# # =========================================
# # READ NUMBERS FROM CSV / EXCEL FILE
# # =========================================

# def read_numbers_from_file(filepath):
#     ext = os.path.splitext(filepath)[1].lower()

#     if ext == ".csv":
#         df = pd.read_csv(filepath, dtype=str)
#     elif ext in (".xlsx", ".xls"):
#         df = pd.read_excel(filepath, dtype=str)
#     else:
#         raise ValueError("Unsupported file type. Please use .csv, .xlsx or .xls")

#     possible_names = ["number", "numbers", "phone", "phone number", "mobile", "contact", "whatsapp"]
#     col = None
#     for c in df.columns:
#         if str(c).strip().lower() in possible_names:
#             col = c
#             break

#     if col is None:
#         col = df.columns[0]

#     numbers = df[col].dropna().astype(str).tolist()
#     return numbers


# # =========================================
# # CLEAN & VALIDATE NUMBERS (ANY COUNTRY)
# # =========================================

# def clean_numbers(numbers, default_region=None):
#     valid_numbers = []
#     invalid_numbers = []
#     seen = set()

#     for raw in numbers:
#         try:
#             num = str(raw).replace(" ", "").replace("-", "")

#             if num.startswith("00"):
#                 num = "+" + num[2:]

#             region_to_use = None if num.startswith("+") else default_region

#             phone = phonenumbers.parse(num, region_to_use)

#             if phonenumbers.is_valid_number(phone):
#                 formatted = phonenumbers.format_number(
#                     phone, phonenumbers.PhoneNumberFormat.E164
#                 )
#                 if formatted not in seen:
#                     seen.add(formatted)
#                     valid_numbers.append(formatted)
#             else:
#                 invalid_numbers.append(raw)

#         except Exception:
#             invalid_numbers.append(raw)

#     return valid_numbers, invalid_numbers


# # =========================================
# # SELENIUM: START / LOGIN
# # =========================================

# def start_driver(session_dir):
#     options = webdriver.ChromeOptions()
#     options.add_argument(f"--user-data-dir={session_dir}")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--start-maximized")
#     try:
#         driver = webdriver.Chrome(options=options)
#     except Exception as e:
#         raise RuntimeError(
#             f"Chrome start nahi hua: {e}\n"
#             f"-> Sab chrome.exe/chromedriver.exe processes band karein (Task Manager)\n"
#             f"-> Ya '{session_dir}' folder rename kar ke fresh session try karein"
#         )
#     driver.get("https://web.whatsapp.com")
#     return driver


# def wait_for_login(driver, timeout=90):
#     WebDriverWait(driver, timeout).until(
#         EC.presence_of_element_located((By.XPATH, '//div[@id="pane-side"]'))
#     )


# def is_logged_in(driver):
#     try:
#         driver.find_element(By.XPATH, '//div[@id="pane-side"]')
#         return True
#     except Exception:
#         return False


# # =========================================
# # SEND A SINGLE MESSAGE - HELPERS
# # =========================================

# def _find_first(driver, xpaths, timeout=6):
#     """Try a list of possible xpaths (WhatsApp Web changes its DOM/selectors
#     periodically) and return the first element found, waiting briefly for each."""
#     last_error = None
#     for xp in xpaths:
#         try:
#             el = WebDriverWait(driver, timeout).until(
#                 EC.presence_of_element_located((By.XPATH, xp))
#             )
#             return el
#         except Exception as e:
#             last_error = e
#             continue
#     raise last_error if last_error else Exception("Element not found")


# _FORMAT_CHARS = {"*", "_", "~", "`"}


# def _type_message(msg_box, message):
#     """Types the message EXACTLY as given. Normal text is sent in one fast
#     chunk (send_keys handles plain text fine at full speed). Only right after
#     a formatting character (* for bold, _ for italic, ~ for strikethrough,
#     ` for monospace) do we pause briefly - that's the exact moment WhatsApp
#     Web's rich-text editor needs a beat to process the format toggle, and
#     without that pause the character can get dropped or duplicated. This
#     keeps long messages fast while still protecting formatting.
#     Shift+Enter is used for line breaks so newlines don't trigger an early send."""
#     lines = message.split("\n")
#     for i, line in enumerate(lines):
#         buffer = ""
#         for ch in line:
#             buffer += ch
#             if ch in _FORMAT_CHARS:
#                 msg_box.send_keys(buffer)
#                 buffer = ""
#                 time.sleep(0.05)
#         if buffer:
#             msg_box.send_keys(buffer)
#         if i < len(lines) - 1:
#             msg_box.send_keys(Keys.SHIFT, Keys.ENTER)
#             time.sleep(0.05)


# def _attach_file(driver, file_path, message, wait_time):
#     """Opens the attach menu, picks 'Document', types the message as a caption,
#     and sends. Uses several fallback selectors since WhatsApp Web updates its UI often."""

#     attach_btn = _find_first(driver, [
#         '//div[@title="Attach"]',
#         '//button[@aria-label="Attach"]',
#         '//div[@aria-label="Attach"]',
#         '//span[@data-icon="plus-rounded"]',
#         '//span[@data-icon="plus"]',
#         '//span[@data-icon="clip"]',
#     ], timeout=8)
#     attach_btn.click()
#     time.sleep(1)

#     # NOTE: We deliberately do NOT click the "Document" submenu option here.
#     # On this WhatsApp Web version, clicking it triggers a REAL native OS
#     # "Open File" dialog (since it's wired to genuinely click the hidden
#     # <input type="file">). Selenium cannot see or control that native
#     # window, so it sits on top of Chrome and blocks every click afterward
#     # (including the Send button) until a human manually closes it.
#     # Instead, we go straight to the hidden file input element and use
#     # send_keys() to set the file path directly - this sets the file
#     # without ever opening any visible dialog.

#     file_input = _find_first(driver, [
#         '//input[@accept]',
#         '//input[@type="file"]',
#     ], timeout=8)
#     file_input.send_keys(os.path.abspath(file_path))
#     time.sleep(2)

#     # The Attach dropdown menu (Document/Photos/Camera/etc.) only auto-closes
#     # when a menu item is actually clicked. Since we skip clicking "Document"
#     # (to avoid triggering the native OS file dialog), this menu can stay
#     # open on top of the page and block clicks on whatever is underneath it
#     # (including Send). We only try to close it if it's ACTUALLY still
#     # visible (checked first) - and we use the Escape key rather than
#     # clicking document.body, because clicking the body was found to also
#     # dismiss the file preview itself, not just the small dropdown menu.
#     try:
#         leftover_menu_items = driver.find_elements(By.XPATH, '//span[text()="Document"]')
#         if any(el.is_displayed() for el in leftover_menu_items):
#             from selenium.webdriver.common.action_chains import ActionChains
#             ActionChains(driver).send_keys(Keys.ESCAPE).perform()
#             time.sleep(1)
#     except Exception:
#         pass

#     if message:
#         try:
#             caption_box = _find_first(driver, [
#                 '//div[@contenteditable="true"][@data-tab="10"]',
#                 '//div[@aria-label="Add a caption"]',
#                 '//div[@contenteditable="true"][@aria-label="Type a message"]',
#             ], timeout=5)
#             caption_box.click()
#             _type_message(caption_box, message)
#             time.sleep(1)  # let the editor finish rendering before we hit send
#         except Exception:
#             pass  # continue without caption if the box can't be found

#     _click_send_button(driver, wait_time)


# def _click_send_button(driver, wait_time):
#     """When a file/attachment preview is open, WhatsApp Web's DOM can contain
#     more than one element matching the 'Send' selectors at the same time
#     (the normal chat's send button plus the preview overlay's send button).
#     Blindly clicking whichever matches first can silently click the wrong
#     one - no error is raised, but nothing actually sends. To fix this: find
#     ALL matching elements, keep only the ones that are actually visible on
#     screen, and click the bottom-rightmost of those (the preview overlay's
#     send button is reliably positioned there, at the bottom-right corner)."""
#     xpath = '//span[@data-icon="send"] | //button[@aria-label="Send"] | //div[@aria-label="Send"]'

#     try:
#         WebDriverWait(driver, 8).until(
#             EC.presence_of_element_located((By.XPATH, xpath))
#         )
#         candidates = driver.find_elements(By.XPATH, xpath)
#         visible = [el for el in candidates if el.is_displayed()]
#         if visible:
#             target = max(visible, key=lambda el: (el.location["y"], el.location["x"]))
#             try:
#                 target.click()
#             except Exception:
#                 driver.execute_script("arguments[0].click();", target)
#             return
#     except Exception:
#         pass

#     # FALLBACK: none of the known selectors matched (WhatsApp Web may have
#     # renamed its icon attributes in this version). Instead of a specific
#     # selector, look at every clickable-looking element on the page and
#     # pick the one furthest toward the bottom-right corner - that position
#     # is consistently where the Send button sits in the file-preview view,
#     # regardless of what internal name WhatsApp gives it.
#     candidates = driver.find_elements(
#         By.XPATH, '//button | //div[@role="button"] | //span[@data-icon]'
#     )
#     visible = [el for el in candidates if el.is_displayed() and el.size["width"] > 0]

#     if not visible:
#         raise Exception("Send button bilkul nahi mila - koi clickable element hi nahi mila")

#     target = max(visible, key=lambda el: (el.location["y"], el.location["x"]))
#     try:
#         target.click()
#     except Exception:
#         driver.execute_script("arguments[0].click();", target)


# # =========================================
# # SEND A SINGLE MESSAGE
# # =========================================

# def send_message(driver, number, message, file_path=None, wait_time=20):
#     try:
#         clean_number = number.replace("+", "")
#         # phone-only URL - the message is typed in directly below rather than
#         # passed through the URL, so formatting/links/newlines stay intact
#         url = f"https://web.whatsapp.com/send?phone={clean_number}"
#         driver.get(url)

#         msg_box = WebDriverWait(driver, wait_time).until(
#             EC.presence_of_element_located(
#                 (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
#             )
#         )
#         time.sleep(2)

#         if file_path:
#             try:
#                 _attach_file(driver, file_path, message, wait_time)
#                 time.sleep(3)
#                 return True, "Sent with attachment"
#             except Exception as attach_error:
#                 # attachment UI failed - fall back to sending just the text
#                 # so the message isn't lost
#                 try:
#                     msg_box = driver.find_element(
#                         By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'
#                     )
#                     msg_box.click()
#                     _type_message(msg_box, message)
#                     msg_box.send_keys(Keys.ENTER)
#                     time.sleep(3)
#                     return True, f"Sent as text only (attachment failed: {attach_error})"
#                 except Exception as fallback_error:
#                     return False, f"Attachment and fallback both failed: {fallback_error}"
#         else:
#             msg_box.click()
#             _type_message(msg_box, message)
#             msg_box.send_keys(Keys.ENTER)

#         time.sleep(3)
#         return True, "Sent"

#     except TimeoutException:
#         return False, "Timeout - invalid number or chat did not load"
#     except Exception as e:
#         return False, str(e)


# # =========================================
# # SAVE LOG
# # =========================================

# def save_log(results, filepath):
#     with open(filepath, "w", newline="", encoding="utf-8") as f:
#         writer = csv.writer(f)
#         writer.writerow(["Number", "Status", "Detail", "Timestamp"])
#         for row in results:
#             writer.writerow(row)

########### NEW CODE BELOW ############

import pandas as pd
import re
import phonenumbers
import time
import os
import csv
import random
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


# =========================================
# ANTI-BOT STEALTH (har naye page par inject hota hai)
# =========================================

STEALTH_JS = """
// 1) navigator.webdriver = Selenium ka sab se bada detection point
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 2) Normal Chrome me plugins/languages hoti hain, bot me nahi
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5]
});
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
});

// 3) window.chrome runtime - bot browsers me missing hota hai
window.chrome = window.chrome || { runtime: {} };

// 4) Permissions API ka normal behavior
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters)
);
"""


# =========================================
# HUMAN-LIKE BEHAVIOR HELPERS
# =========================================

def human_delay(lo=1.5, hi=4.0):
    """Fixed sleep ki jagah random human-like pause.
    Bot checker exact same timings ko flag karta hai."""
    time.sleep(random.uniform(lo, hi))


def sleep_chunked(total):
    """Bade wait ko chhote random chunks me todo - network jitter jaisa
    lage, 'fixed 30s sleep' jaisa nahi."""
    while total > 0:
        chunk = min(random.uniform(0.8, 4.0), total)
        time.sleep(chunk)
        total -= chunk


def random_mouse_jitter(driver):
    """Halki mouse movement - 'bilkul still' screen bhi ek signal hai."""
    try:
        from selenium.webdriver.common.action_chains import ActionChains
        ActionChains(driver).move_by_offset(
            random.randint(-70, 70), random.randint(-70, 70)
        ).perform()
    except Exception:
        pass


# =========================================
# READ NUMBERS FROM PASTED TEXT
# =========================================

def read_numbers_from_text(text):
    numbers = []
    raw_numbers = re.split(r'[,\n]+', text)

    for num in raw_numbers:
        num = num.strip()
        num = num.replace(" ", "")
        if num:
            numbers.append(num)

    return numbers


# =========================================
# READ NUMBERS FROM CSV / EXCEL FILE
# =========================================

def read_numbers_from_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".csv":
        df = pd.read_csv(filepath, dtype=str)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(filepath, dtype=str)
    else:
        raise ValueError("Unsupported file type. Please use .csv, .xlsx or .xls")

    possible_names = ["number", "numbers", "phone", "phone number", "mobile", "contact", "whatsapp"]
    col = None
    for c in df.columns:
        if str(c).strip().lower() in possible_names:
            col = c
            break

    if col is None:
        col = df.columns[0]

    numbers = df[col].dropna().astype(str).tolist()
    return numbers


# =========================================
# CLEAN & VALIDATE NUMBERS (ANY COUNTRY)
# =========================================

def clean_numbers(numbers, default_region=None):
    valid_numbers = []
    invalid_numbers = []
    seen = set()

    for raw in numbers:
        try:
            num = str(raw).replace(" ", "").replace("-", "")

            if num.startswith("00"):
                num = "+" + num[2:]

            region_to_use = None if num.startswith("+") else default_region

            phone = phonenumbers.parse(num, region_to_use)

            if phonenumbers.is_valid_number(phone):
                formatted = phonenumbers.format_number(
                    phone, phonenumbers.PhoneNumberFormat.E164
                )
                if formatted not in seen:
                    seen.add(formatted)
                    valid_numbers.append(formatted)
            else:
                invalid_numbers.append(raw)

        except Exception:
            invalid_numbers.append(raw)

    return valid_numbers, invalid_numbers


# =========================================
# SELENIUM: START / LOGIN (anti-bot ke saath)
# =========================================

def start_driver(session_dir):
    options = webdriver.ChromeOptions()

    # SAME session folder reuse karo - naya folder = naya device fingerprint
    options.add_argument(f"--user-data-dir={session_dir}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")

    # ---- ANTI-BOT FLAGS ----
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--lang=en-US")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        raise RuntimeError(
            f"Chrome start nahi hua: {e}\n"
            f"-> Sab chrome.exe/chromedriver.exe processes band karein (Task Manager)\n"
            f"-> Ya '{session_dir}' folder rename kar ke fresh session try karein"
        )

    # webdriver flag ko CDP se override - har naye page/document par apply hota hai
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": STEALTH_JS
    })

    driver.get("https://web.whatsapp.com")
    return driver


def wait_for_login(driver, timeout=90):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, '//div[@id="pane-side"]'))
    )


def is_logged_in(driver):
    try:
        driver.find_element(By.XPATH, '//div[@id="pane-side"]')
        return True
    except Exception:
        return False


# =========================================
# SEND A SINGLE MESSAGE - HELPERS
# =========================================

def _find_first(driver, xpaths, timeout=6):
    last_error = None
    for xp in xpaths:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xp))
            )
            return el
        except Exception as e:
            last_error = e
            continue
    raise last_error if last_error else Exception("Element not found")


_FORMAT_CHARS = {"*", "_", "~", "`"}


def _type_message(msg_box, message):
    """Human-like typing: word-by-word, random speed, kabhi-kabhi 'sochne'
    ka pause. Pura message ek saath chunk me bhejna = instant-paste pattern
    jo bot checker turant pakad leta hai."""
    lines = message.split("\n")
    next_think = random.randint(12, 18)
    word_count = 0

    for i, line in enumerate(lines):
        parts = re.split(r'(\s+)', line)
        for part in parts:
            if not part:
                continue
            msg_box.send_keys(part)
            if part.isspace():
                time.sleep(random.uniform(0.05, 0.15))
            elif any(ch in _FORMAT_CHARS for ch in part):
                time.sleep(random.uniform(0.05, 0.12))
            else:
                time.sleep(random.uniform(0.01, 0.04))

            word_count += 1
            # har ~12-18 words ke baad ek 'insaan soch raha hai' pause
            if word_count >= next_think:
                time.sleep(random.uniform(0.4, 1.2))
                next_think = word_count + random.randint(12, 18)

        if i < len(lines) - 1:
            msg_box.send_keys(Keys.SHIFT, Keys.ENTER)
            time.sleep(random.uniform(0.1, 0.3))


def _handle_new_chat_prompt(driver):
    """Naye number ke liye WhatsApp 'Continue to chat' button dikhata hai.
    Ise click kiye bina chat load nahi hoti - pehle wale code me ye missing
    tha, isliye kai numbers fail ho jate the."""
    try:
        btns = driver.find_elements(
            By.XPATH, '//div[@role="button"][contains(., "Continue to chat")]'
        )
        if btns and btns[0].is_displayed():
            btns[0].click()
            human_delay(1.5, 3.0)
    except Exception:
        pass


def _attach_file(driver, file_path, message, wait_time):
    attach_btn = _find_first(driver, [
        '//div[@title="Attach"]',
        '//button[@aria-label="Attach"]',
        '//div[@aria-label="Attach"]',
        '//span[@data-icon="plus-rounded"]',
        '//span[@data-icon="plus"]',
        '//span[@data-icon="clip"]',
    ], timeout=8)
    attach_btn.click()
    human_delay(0.8, 1.5)

    # NOTE: 'Document' submenu click NAHI karte - isse native OS file dialog
    # khulta hai jo Selenium control nahi kar sakta. Seedha hidden file input
    # par send_keys() se path set karo.

    file_input = _find_first(driver, [
        '//input[@accept]',
        '//input[@type="file"]',
    ], timeout=8)
    file_input.send_keys(os.path.abspath(file_path))
    human_delay(1.5, 3.0)

    # Attach dropdown agar khula ho to Escape se band karo
    try:
        leftover_menu_items = driver.find_elements(By.XPATH, '//span[text()="Document"]')
        if any(el.is_displayed() for el in leftover_menu_items):
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            human_delay(0.8, 1.5)
    except Exception:
        pass

    if message:
        try:
            caption_box = _find_first(driver, [
                '//div[@contenteditable="true"][@data-tab="10"]',
                '//div[@aria-label="Add a caption"]',
                '//div[@contenteditable="true"][@aria-label="Type a message"]',
            ], timeout=5)
            caption_box.click()
            _type_message(caption_box, message)
            human_delay(0.8, 1.8)
        except Exception:
            pass

    _click_send_button(driver, wait_time)


def _click_send_button(driver, wait_time):
    xpath = '//span[@data-icon="send"] | //button[@aria-label="Send"] | //div[@aria-label="Send"]'

    try:
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        candidates = driver.find_elements(By.XPATH, xpath)
        visible = [el for el in candidates if el.is_displayed()]
        if visible:
            target = max(visible, key=lambda el: (el.location["y"], el.location["x"]))
            try:
                target.click()
            except Exception:
                driver.execute_script("arguments[0].click();", target)
            return
    except Exception:
        pass

    candidates = driver.find_elements(
        By.XPATH, '//button | //div[@role="button"] | //span[@data-icon]'
    )
    visible = [el for el in candidates if el.is_displayed() and el.size["width"] > 0]

    if not visible:
        raise Exception("Send button bilkul nahi mila - koi clickable element hi nahi mila")

    target = max(visible, key=lambda el: (el.location["y"], el.location["x"]))
    try:
        target.click()
    except Exception:
        driver.execute_script("arguments[0].click();", target)


# =========================================
# SEND A SINGLE MESSAGE (human pacing ke saath)
# =========================================

def send_message(driver, number, message, file_path=None, wait_time=20):
    try:
        clean_number = number.replace("+", "")
        url = f"https://web.whatsapp.com/send?phone={clean_number}"
        driver.get(url)

        # Page load ke baad turant type mat karo - insaan rukta hai
        human_delay(2.5, 5.0)
        random_mouse_jitter(driver)

        # Naye number ke liye 'Continue to chat' prompt handle karo
        _handle_new_chat_prompt(driver)

        msg_box = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located(
                (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
            )
        )
        # Chat khulne ke baad bhi ek pause
        human_delay(1.0, 2.5)

        if file_path:
            try:
                _attach_file(driver, file_path, message, wait_time)
                human_delay(2.5, 4.0)
                return True, "Sent with attachment"
            except Exception as attach_error:
                try:
                    msg_box = driver.find_element(
                        By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'
                    )
                    msg_box.click()
                    _type_message(msg_box, message)
                    msg_box.send_keys(Keys.ENTER)
                    human_delay(2.5, 4.0)
                    return True, f"Sent as text only (attachment failed: {attach_error})"
                except Exception as fallback_error:
                    return False, f"Attachment and fallback both failed: {fallback_error}"
        else:
            msg_box.click()
            _type_message(msg_box, message)
            # Send dabane se pehle chhota random pause
            human_delay(0.5, 1.5)
            msg_box.send_keys(Keys.ENTER)

        human_delay(2.5, 4.0)
        return True, "Sent"

    except TimeoutException:
        return False, "Timeout - invalid number or chat did not load"
    except Exception as e:
        return False, str(e)


# =========================================
# CAMPAIGN LOOP (warm-up + random gaps)
# =========================================

def run_campaign(driver, numbers, message, file_path=None,
                 min_gap=25, max_gap=50, warmup_count=8, daily_cap=None):
    """Ek message ko jitne chahe numbers par bhejo - lekin bot checker ko
    pattern mat do:
      - Pehle kuch numbers slow (warm-up)
      - Har number ke beech RANDOM gap (fixed gap = bot pattern)
      - daily_cap lagana (naya number ke liye safe)"""
    results = []
    total = len(numbers)

    if daily_cap:
        numbers = numbers[:daily_cap]
        total = len(numbers)
        print(f"Daily cap applied -> sirf {total} numbers bhejenge.")

    for idx, number in enumerate(numbers):
        print(f"[{idx+1}/{total}] Sending to {number} ...")
        ok, detail = send_message(driver, number, message, file_path)
        results.append([
            number,
            "OK" if ok else "FAIL",
            detail,
            datetime.now().isoformat(timespec="seconds"),
        ])
        print(f"    -> {detail}")

        if idx < total - 1:
            if idx < warmup_count:
                gap = random.uniform(45, 90)
            else:
                gap = random.uniform(min_gap, max_gap)
            print(f"    waiting {gap:.0f}s (human-like random gap) ...")
            sleep_chunked(gap)

    return results


# =========================================
# SAVE LOG
# =========================================

def save_log(results, filepath):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Number", "Status", "Detail", "Timestamp"])
        for row in results:
            writer.writerow(row)


# =========================================
# EXAMPLE USAGE (main)
# =========================================

if __name__ == "__main__":
    # Ya file se load karo: numbers = read_numbers_from_file("list.xlsx")
    numbers = ["+919876543210", "+919876543211"]
    valid, invalid = clean_numbers(numbers, default_region="IN")

    driver = start_driver("wa_session")          # SAME session folder reuse karo
    wait_for_login(driver)                       # QR scan karo (pehli baar)

    message = "Hello! Ye ek test message hai."

    results = run_campaign(
        driver,
        valid,
        message,
        min_gap=25,      # normal gap: 25-50 sec RANDOM
        max_gap=50,
        warmup_count=5,  # pehle 5 numbers: 45-90 sec gap
        daily_cap=50,    # naya number: din ka 50 cap (safe)
        # daily_cap=None  -> unlimited (lekin ban ka risk)
    )
    save_log(results, "log.csv")