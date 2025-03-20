from flask import Flask, request, jsonify, send_from_directory
import os
import json
from datetime import datetime

app = Flask(__name__)

# Set the temporary upload folder (Vercel's ephemeral storage)
UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# File upload endpoint
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400

    try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        # Log the upload to a text file
        log_path = os.path.join(UPLOAD_FOLDER, "upload_log.txt")
        with open(log_path, "a") as log_file:
            log_file.write(f"{file.filename}\n")

        file_url = f"https://line-ai-chatbot.vercel.app/files/{file.filename}"
        return jsonify({"status": "success", "message": f"File uploaded", "url": file_url}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Endpoint to serve uploaded files
@app.route('/files/<filename>', methods=['GET'])
def serve_file(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# List uploaded files with URLs
@app.route('/list', methods=['GET'])
def list_files():
    try:
        log_path = os.path.join(UPLOAD_FOLDER, "upload_log.txt")
        if os.path.exists(log_path):
            with open(log_path, "r") as file:
                log_data = file.readlines()
            file_urls = [{"filename": fname.strip(), "url": f"https://line-ai-chatbot.vercel.app/files/{fname.strip()}"} for fname in log_data]
            return jsonify({"status": "success", "files": file_urls}), 200
        else:
            return jsonify({"status": "success", "files": [], "message": "No logs found"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
