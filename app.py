"""
CAN Bus Intrusion Detection System
Flask Backend — Main Application
"""

import os
import json
import uuid
import traceback
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, flash
)
from werkzeug.utils import secure_filename

from ml.predictor import CANPredictor

# ─────────────────────────────────────────
# APP CONFIG
# ─────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "canids-secret-2025")

UPLOAD_FOLDER  = os.path.join("static", "uploads")
RESULTS_FOLDER = os.path.join("static", "results")   # ← stores result JSON files
ALLOWED_EXTENSIONS    = {"csv"}
MAX_CONTENT_LENGTH    = 500 * 1024 * 1024   # 500 MB

app.config["UPLOAD_FOLDER"]      = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER,  exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Load ML model once at startup
predictor = CANPredictor()


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def allowed_file(filename: str) -> bool:
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_results(results: dict) -> str:
    """Write results dict to a JSON file; return the filename (not full path)."""
    fname = f"result_{uuid.uuid4().hex}.json"
    fpath = os.path.join(RESULTS_FOLDER, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(results, f)
    return fname


def load_results(fname: str) -> dict | None:
    """Read results from a JSON file by filename."""
    if not fname:
        return None
    fpath = os.path.join(RESULTS_FOLDER, fname)
    if not os.path.exists(fpath):
        return None
    with open(fpath, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "GET":
        return render_template("upload.html")

    if "file" not in request.files:
        flash("No file part in the request.", "error")
        return redirect(url_for("upload"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("upload"))

    if not allowed_file(file.filename):
        flash("Only .csv files are allowed.", "error")
        return redirect(url_for("upload"))

    original_name = secure_filename(file.filename)
    unique_name   = f"{uuid.uuid4().hex}_{original_name}"
    save_path     = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    file.save(save_path)

    # Only store the small file path in session (not the huge results)
    session["uploaded_file"]  = save_path
    session["original_name"]  = original_name

    return redirect(url_for("predict"))


@app.route("/predict")
def predict():
    filepath = session.get("uploaded_file")
    if not filepath or not os.path.exists(filepath):
        flash("No uploaded file found. Please upload again.", "error")
        return redirect(url_for("upload"))

    try:
        results = predictor.predict_csv(filepath)

        # ── KEY FIX: save large results to disk, store only filename in session ──
        result_file = save_results(results)
        session["result_file"] = result_file

        return redirect(url_for("dashboard"))

    except Exception as e:
        traceback.print_exc()
        flash(f"Prediction error: {str(e)}", "error")
        return redirect(url_for("upload"))


@app.route("/dashboard")
def dashboard():
    result_file = session.get("result_file")
    results     = load_results(result_file)

    if results is None:
        flash("No results found. Please upload a dataset first.", "warning")
        return redirect(url_for("upload"))

    return render_template("dashboard.html", results=results)


@app.route("/api/results")
def api_results():
    result_file = session.get("result_file")
    results     = load_results(result_file)
    if results is None:
        return jsonify({"error": "No results in session"}), 404
    return jsonify(results)


@app.route("/about")
def about():
    return render_template("index.html", scroll="about")


# ─────────────────────────────────────────
# MAIN
# ────────────────────────────────── ───────
if __name__ == "__main__":
    app.run(debug=True, port=5000)
