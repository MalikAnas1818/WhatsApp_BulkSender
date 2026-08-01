# import pandas as pd
# import re
# import phonenumbers
# import time
# import os
# import csv
# from datetime import datetime


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
# # SAVE LOG
# # =========================================

# def save_log(results, filepath):
#     with open(filepath, "w", newline="", encoding="utf-8") as f:
#         writer = csv.writer(f)
#         writer.writerow(["Number", "Status", "Detail", "Timestamp"])
#         for row in results:
#             writer.writerow(row)


# # =========================================================================
# # NEECHE WALA SELENIUM SECTION SIRF LOCAL PC PE CHALEGA (Colab mein NAHI)
# # Chrome + QR code login ke liye GUI/display zaroori hai jo Colab mein
# # available nahi hoti. Isliye ye functions sirf DEFINE ho rahe hain yahan,
# # taake poori file ek hi jagah rahe - inhe RUN sirf apne PC pe karna hai.
# # =========================================================================

# try:
#     from selenium import webdriver
#     from selenium.webdriver.common.by import By
#     from selenium.webdriver.common.keys import Keys
#     from selenium.webdriver.support.ui import WebDriverWait
#     from selenium.webdriver.support import expected_conditions as EC
#     from selenium.common.exceptions import TimeoutException
#     SELENIUM_AVAILABLE = True
# except ImportError:
#     SELENIUM_AVAILABLE = False


# def start_driver(session_dir):
#     options = webdriver.ChromeOptions()
#     options.add_argument(f"--user-data-dir={session_dir}")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--start-maximized")
#     try:
#         driver = webdriver.Chrome(options=options)
#     except Exception as e:
#         raise RuntimeError(f"Chrome start nahi hua: {e}")
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


# def _type_message(msg_box, message):
#     """Types the message exactly as given, using Shift+Enter for line breaks
#     so newlines don't trigger an early send and formatting stays intact.
#     Har character ke beech chhota delay diya gaya hai taake WhatsApp Web ka
#     rich-text editor (bold *asterisks* wagera) sahi tarike se process kare."""
#     lines = message.split("\n")
#     for i, line in enumerate(lines):
#         if line:
#             for ch in line:
#                 msg_box.send_keys(ch)
#                 time.sleep(0.01)
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

#     try:
#         doc_option = _find_first(driver, [
#             '//div[@aria-label="Document"]',
#             '//span[text()="Document"]',
#             '//div[contains(@aria-label,"Document")]',
#         ], timeout=3)
#         doc_option.click()
#         time.sleep(1)
#     except Exception:
#         pass  # some versions attach the file input directly, no submenu

#     file_input = _find_first(driver, [
#         '//input[@accept]',
#         '//input[@type="file"]',
#     ], timeout=6)
#     file_input.send_keys(os.path.abspath(file_path))
#     time.sleep(3)

#     if message:
#         try:
#             caption_box = _find_first(driver, [
#                 '//div[@contenteditable="true"][@data-tab="10"]',
#                 '//div[@aria-label="Add a caption"]',
#                 '//div[@contenteditable="true"][@aria-label="Type a message"]',
#             ], timeout=5)
#             caption_box.click()
#             _type_message(caption_box, message)
#         except Exception:
#             pass  # continue without caption if the box can't be found

#     send_btn = _find_first(driver, [
#         '//span[@data-icon="send"]',
#         '//button[@aria-label="Send"]',
#         '//div[@aria-label="Send"]',
#     ], timeout=wait_time)
#     send_btn.click()


# def send_message(driver, number, message, file_path=None, wait_time=20):
#     try:
#         clean_number = number.replace("+", "")
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


# # =========================================================================
# # TESTING SECTION - Colab mein ye hi chalega (Selenium wala hissa skip
# # ho jayega automatically agar Chrome/GUI available nahi hai)
# # =========================================================================

# if __name__ == "__main__":
#     print("=" * 60)
#     print("TEST 1: read_numbers_from_text()")
#     print("=" * 60)
#     sample_text = """
#     +923001234567,
#     +923111234567
#     03211234567
#     +971 50 782 1690
#     """
#     text_numbers = read_numbers_from_text(sample_text)
#     for n in text_numbers:
#         print(n)

#     print("\n" + "=" * 60)
#     print("TEST 2: read_numbers_from_file()")
#     print("=" * 60)
#     test_csv = "test_numbers.csv"
#     with open(test_csv, "w") as f:
#         f.write("Name,Phone Number\n")
#         f.write("Ali,+923001234567\n")
#         f.write("Sara,03211234567\n")
#         f.write("Wael,+971507821690\n")

#     file_numbers = read_numbers_from_file(test_csv)
#     for n in file_numbers:
#         print(n)

#     print("\n" + "=" * 60)
#     print("TEST 3: clean_numbers()")
#     print("=" * 60)
#     all_numbers = text_numbers + file_numbers
#     valid, invalid = clean_numbers(all_numbers, default_region="PK")

#     print("Valid:")
#     for v in valid:
#         print(v)
#     print("\nInvalid:")
#     for i in invalid:
#         print(i)

#     print("\n" + "=" * 60)
#     print("TEST 4: save_log()")
#     print("=" * 60)
#     fake_results = [
#         (v, "Sent", "Test message sent successfully", datetime.now().isoformat())
#         for v in valid
#     ]
#     log_path = "test_log.csv"
#     save_log(fake_results, log_path)
#     print(f"Log saved to: {log_path}")
#     with open(log_path, "r", encoding="utf-8") as f:
#         print(f.read())

#     print("\n" + "=" * 60)
#     print("SELENIUM FUNCTIONS (start_driver, send_message, etc.)")
#     print("=" * 60)
#     if SELENIUM_AVAILABLE:
#         print("Selenium installed hai, lekin QR-login ke liye GUI zaroori hai.")
#         print("Ye functions sirf apne LOCAL PC pe chalayein, Colab mein nahi.")
#     else:
#         print("Selenium is environment mein installed nahi hai (Colab mein normal hai).")
#         print("Ye functions apne LOCAL PC pe chalayenge jahan Chrome + GUI available ho.")

import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


# =========================================
# SETTINGS - IN DO CHEEZON KO CHANGE KAREIN
# =========================================

SESSION_DIR = os.path.abspath("whatsapp_session")   # aapka existing session folder
TEST_NUMBER = "+923279115785"                        # <-- YAHAN APNA TEST NUMBER DALEIN
TEST_MESSAGE = "Salam! Ye ek test message hai *bold text* ke sath check karne ke liye."


# =========================================
# START CHROME WITH EXISTING SESSION
# =========================================

def start_driver(session_dir):
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={session_dir}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        raise RuntimeError(f"Chrome start nahi hua: {e}")
    driver.get("https://web.whatsapp.com")
    return driver


def wait_for_login(driver, timeout=90):
    print("WhatsApp Web load ho raha hai... agar QR scan karna pade to abhi kar lein.")
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, '//div[@id="pane-side"]'))
    )
    print("Login confirm ho gaya (ya session pehle se saved thi).")


def _type_message(msg_box, message):
    """Har character ke beech chhota delay - taake WhatsApp ka editor
    bold (*text*) formatting sahi tarike se process kare."""
    lines = message.split("\n")
    for i, line in enumerate(lines):
        if line:
            for ch in line:
                msg_box.send_keys(ch)
                time.sleep(0.01)
        if i < len(lines) - 1:
            msg_box.send_keys(Keys.SHIFT, Keys.ENTER)
            time.sleep(0.05)


def send_test_message(driver, number, message, wait_time=20):
    try:
        clean_number = number.replace("+", "")
        url = f"https://web.whatsapp.com/send?phone={clean_number}"
        driver.get(url)

        msg_box = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located(
                (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
            )
        )
        time.sleep(2)

        msg_box.click()
        _type_message(msg_box, message)
        msg_box.send_keys(Keys.ENTER)

        time.sleep(3)
        return True, "Sent"

    except TimeoutException:
        return False, "Timeout - invalid number ya chat load nahi hui"
    except Exception as e:
        return False, str(e)


# =========================================
# RUN TEST
# =========================================

if __name__ == "__main__":
    print("=" * 60)
    print("SELENIUM TEST - Ek single message bhejne ka test")
    print("=" * 60)

    print(f"\nUsing session folder: {SESSION_DIR}")
    print(f"Test number: {TEST_NUMBER}")
    print(f"Test message: {TEST_MESSAGE}\n")

    driver = start_driver(SESSION_DIR)

    try:
        wait_for_login(driver, timeout=90)

        print("\nTest message bheja ja raha hai...")
        success, detail = send_test_message(driver, TEST_NUMBER, TEST_MESSAGE)

        print("\n" + "=" * 60)
        print("RESULT")
        print("=" * 60)
        print(f"Success: {success}")
        print(f"Detail: {detail}")

        if success:
            print("\n✅ Message chala gaya! WhatsApp pe check karein ke formatting")
            print("   (*bold text*) sahi dikh rahi hai ya nahi.")
        else:
            print("\n❌ Message send nahi ho saka. Upar wali 'Detail' line dekhein.")

    finally:
        print("\n10 seconds mein browser band ho jayega (result check karne ke liye)...")
        time.sleep(10)
        driver.quit()