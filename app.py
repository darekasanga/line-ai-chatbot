from flask import Flask, request, jsonify, render_template
import os
import requests
import base64
from io import BytesIO
from PIL import Image

app = Flask(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = "darekasanga/line-ai-chatbot"
GITHUB_BRANCH = "file"
GITHUB_API = "https://api.github.com"
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/"

@app.route('/')
def home():
    return "Hello, GitHub File Uploader!"

@app.route('/upload.html')
def upload_page():
    return render_template("upload.html")

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    content = file.read()
    filename = file.filename

    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{filename}?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded_content = base64.b64encode(content).decode("utf-8")

    data = {
        "message": f"Add or update {filename}",
        "content": encoded_content,
        "branch": GITHUB_BRANCH
    }

    response = requests.put(url, headers=headers, json=data)
    return jsonify(response.json())

@app.route('/list')
def list_files():
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    files = response.json()

    file_list = ''
    for file in files:
        filename = file['name']
        file_url = f"{GITHUB_RAW_URL}{filename}"
        file_list += f'<li>{filename} - <a href="{file_url}" target="_blank">View</a> <button onclick="deleteFile(\'{filename}\')">Delete</button></li>'

    return f'''
    <h2>Uploaded Files</h2>
    <ul>{file_list}</ul>
    <button onclick="location.href='/upload.html'">Back to Upload</button>
    <script src="/static/delete.js"></script>
    '''

@app.route('/delete/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{filename}?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    get_response = requests.get(url, headers=headers)
    sha = get_response.json().get("sha")

    if not sha:
        return jsonify({"status": "error", "message": "File not found"}), 404

    data = {
        "message": f"Delete {filename}",
        "sha": sha,
        "branch": GITHUB_BRANCH
    }

    delete_response = requests.delete(url, headers=headers, json=data)
    if delete_response.status_code == 200:
        return jsonify({"status": "success", "message": f"Deleted {filename}"})
    else:
        return jsonify({"status": "error", "message": delete_response.json().get("message")})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
