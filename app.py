import os
import uuid
import threading
from datetime import datetime

from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

import bulk_logic as bl

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
SESSION_DIR = os.path.join(BASE_DIR, "whatsapp_session")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# in-memory job store: { job_id: {status, total, sent, failed, log:[...], driver, ...} }
JOBS = {}


@app.route("/")
def index():
    return render_template("index.html")


# ---------- STEP 1: parse numbers (pasted text) ----------
@app.route("/api/parse-text", methods=["POST"])
def parse_text():
    data = request.get_json(force=True)
    text = data.get("text", "")
    numbers = bl.read_numbers_from_text(text)
    return jsonify({"numbers": numbers, "count": len(numbers)})


# ---------- STEP 1: parse numbers (uploaded CSV/Excel) ----------
@app.route("/api/upload", methods=["POST"])
def upload_file():
    file = request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"error": "No file provided"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)

    try:
        numbers = bl.read_numbers_from_file(filepath)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"numbers": numbers, "count": len(numbers)})


# ---------- STEP 2: validate numbers ----------
@app.route("/api/validate", methods=["POST"])
def validate_numbers():
    data = request.get_json(force=True)
    numbers = data.get("numbers", [])
    default_region = data.get("default_region") or None

    valid, invalid = bl.clean_numbers(numbers, default_region)
    return jsonify({
        "valid": valid,
        "invalid": invalid,
        "valid_count": len(valid),
        "invalid_count": len(invalid),
    })


# ---------- attachment upload (image/document to send) ----------
@app.route("/api/upload-attachment", methods=["POST"])
def upload_attachment():
    file = request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"error": "No file provided"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)

    return jsonify({"path": filepath, "name": filename})


# ---------- STEP 3: start sending job ----------
def run_sending_job(job_id, numbers, message, attachment_path):
    job = JOBS[job_id]

    try:
        job["status"] = "launching_chrome"
        driver = bl.start_driver(SESSION_DIR)
        job["driver"] = driver

        job["status"] = "waiting_for_qr"
        bl.wait_for_login(driver, timeout=120)

        job["status"] = "sending"
        results = []

        for number in numbers:
            if job.get("cancel"):
                job["status"] = "cancelled"
                break

            success, detail = bl.send_message(driver, number, message, attachment_path)
            status = "Success" if success else "Failed"

            entry = {
                "number": number,
                "status": status,
                "detail": detail,
                "time": datetime.now().strftime("%H:%M:%S"),
            }
            job["log"].append(entry)

            if success:
                job["sent"] += 1
            else:
                job["failed"] += 1

            results.append([number, status, detail, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

        log_path = os.path.join(UPLOAD_DIR, f"send_log_{job_id}.csv")
        bl.save_log(results, log_path)
        job["log_file"] = log_path

        if job["status"] != "cancelled":
            job["status"] = "completed"

        driver.quit()

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


@app.route("/api/send", methods=["POST"])
def send_messages():
    data = request.get_json(force=True)
    numbers = data.get("numbers", [])
    message = data.get("message", "")
    attachment_path = data.get("attachment_path") or None

    if not numbers or not message:
        return jsonify({"error": "Numbers and message are required"}), 400

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        "status": "starting",
        "total": len(numbers),
        "sent": 0,
        "failed": 0,
        "log": [],
        "cancel": False,
        "driver": None,
        "log_file": None,
        "error": None,
    }

    thread = threading.Thread(
        target=run_sending_job,
        args=(job_id, numbers, message, attachment_path),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


# ---------- poll progress ----------
@app.route("/api/progress/<job_id>")
def progress(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({
        "status": job["status"],
        "total": job["total"],
        "sent": job["sent"],
        "failed": job["failed"],
        "log": job["log"][-50:],  # last 50 entries
        "error": job["error"],
    })


@app.route("/api/cancel/<job_id>", methods=["POST"])
def cancel_job(job_id):
    job = JOBS.get(job_id)
    if job:
        job["cancel"] = True
    return jsonify({"ok": True})


@app.route("/api/download-log/<job_id>")
def download_log(job_id):
    job = JOBS.get(job_id)
    if not job or not job.get("log_file"):
        return jsonify({"error": "Log not available"}), 404
    return send_file(job["log_file"], as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
