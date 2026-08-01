# WA BulkSender

A simple tool to send one WhatsApp message to a large list of numbers — paste them or upload a CSV/Excel file, write your message (with an optional file attachment), preview it, and send. Built with Flask + Selenium (drives WhatsApp Web through Chrome).

---

## ✨ Features

- **Add numbers two ways:** paste a list, or upload a `.csv` / `.xlsx` / `.xls` file
- **Works for any country** — numbers with `+countrycode` are auto-detected; numbers without one can use a default country code you set (e.g. `PK`, `US`, `IN`)
- **Duplicate & invalid numbers filtered out automatically**
- **Optional file attachment** sent as a caption along with your message
- **Live progress while sending** — sent/failed counters and a per-number log
- **Downloadable CSV log** after each run (number, status, reason, timestamp)
- **Cancel mid-run** if you need to stop

---

## 📁 Project Structure

```
wa_bulksender/
├── app.py                 # Flask backend — routes + background sending job
├── bulk_logic.py           # Core logic — parsing, validation, WhatsApp automation
├── requirements.txt
├── templates/
│   └── index.html          # The 4-step web UI
├── static/
│   ├── css/style.css        # Orange theme styling
│   └── js/script.js         # Frontend logic (API calls, live progress)
├── uploads/                 # Uploaded files + attachments (auto-created)
└── whatsapp_session/         # Saved WhatsApp Web login (auto-created after first QR scan)
```

---

## 🚀 Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Run the app**
```bash
python app.py
```

**3. Open in browser**
```
http://127.0.0.1:5000
```

> Make sure Google Chrome is installed — Selenium drives an actual Chrome window to use WhatsApp Web.

---

## 🧭 How to Use

1. **Add numbers** — paste them (one per line, or comma-separated) or upload a CSV/Excel file. If some numbers don't include a country code, set a default (e.g. `PK`) so they're still recognized.
2. **Compose** — write your message. Optionally attach an image or document — it will be sent as a caption with the file.
3. **Preview** — check the valid/invalid count and the exact message before sending.
4. **Send** — a Chrome window opens.
   - **First time only:** scan the QR code shown with WhatsApp on your phone.
   - After that, sending starts automatically and you'll see live progress + a log feed.
   - When done, download the log to see the result for every number.

---

## ⚠️ Important Notes

- **This automates WhatsApp Web, which is not an official WhatsApp business tool.** Sending too fast or to too many numbers at once increases the risk of your number being temporarily restricted by WhatsApp. The tool waits a few seconds between each message — don't remove that delay.
- **Don't delete the `whatsapp_session/` folder** — it keeps you logged in so you don't have to scan the QR code every time.
- A number showing **"Timeout - invalid number or chat did not load"** usually means that number isn't on WhatsApp (e.g. a landline), not a bug in the tool.
- WhatsApp Web occasionally changes its own page design, which can break the automation selectors (e.g. the attach button). If sending suddenly stops working, that's usually why — let me know and the selectors can be updated.
- This is a personal/internal tool. Sending unsolicited bulk messages may violate WhatsApp's Terms of Service — use it for contacts who expect to hear from you (e.g. your own leads, customers, or applicants).

---

## 🛠 Troubleshooting

| Problem | Likely Cause |
|---|---|
| `TemplateNotFound: index.html` | `templates` folder name misspelled or missing |
| CSS/JS not loading, page looks unstyled | `static/css` or `static/js` folders missing or misnamed |
| "Valid Numbers: 0" | Numbers may need a default country code set, or check the pasted format |
| Attach button errors | WhatsApp Web UI changed — the tool falls back to sending text only in this case |
| Numbers keep timing out | Those numbers likely aren't registered on WhatsApp |

---

## 📦 Requirements

- Python 3.9+
- Google Chrome installed
- See `requirements.txt` for Python packages (Flask, pandas, phonenumbers, selenium, openpyxl)
