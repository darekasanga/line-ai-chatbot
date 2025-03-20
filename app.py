from flask import Flask, request, jsonify, redirect, url_for
import os
import json
import base64
import requests
from datetime import datetime
from io import BytesIO
from PIL import Image

app = Flask(__name__)

# GitHub repository details
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = "darekasanga/line-ai-chatbot"
GITHUB_BRANCH = "file"
GITHUB_API = "https://api.github.com"
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/"

# Create the branch if it doesn't exist
def create_branch(branch_name):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/git/refs/heads/main"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        sha = response.json()["object"]["sha"]
        branch_check_url = f"{GITHUB_API}/repos/{GITHUB_REPO}/git/refs/heads/{branch_name}"
        check_response = requests.get(branch_check_url, headers=headers)
        if check_response.status_code == 200:
            return
        new_branch_url = f"{GITHUB_API}/repos/{GITHUB_REPO}/git/refs"
        data = {"ref": f"refs/heads/{branch_name}", "sha": sha}
        requests.post(new_branch_url, headers=headers, data=json.dumps(data))

# Upload file to GitHub on the "file" branch
def upload_to_github(filename, content):
    create_branch(GITHUB_BRANCH)
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{filename}?ref={GITHUB_BRANCH}"
    encoded_content = base64.b64encode(content).decode("utf-8")
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    get_response = requests.get(url, headers=headers)
    sha = None
    if get_response.status_code == 200:
        sha = get_response.json().get("sha")
    data = {
        "message": f"Add or update {filename} to {GITHUB_BRANCH}",
        "content": encoded_content,
        "branch": GITHUB_BRANCH
    }
    if sha:
        data["sha"] = sha
    response = requests.put(url, headers=headers, data=json.dumps(data))
    return response

# Delete file from GitHub
def delete_from_github(filename):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{filename}?ref={GITHUB_BRANCH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    get_response = requests.get(url, headers=headers)
    if get_response.status_code == 200:
        sha = get_response.json().get("sha")
        data = {
            "message": f"Delete {filename}",
            "sha": sha,
            "branch": GITHUB_BRANCH
        }
        response = requests.delete(url, headers=headers, data=json.dumps(data))
        return response

# Resize the image
def downsize_image(image_data, max_size=(800, 800)):
    image = Image.open(BytesIO(image_data))
    image.thumbnail(max_size)
    output = BytesIO()
    image.save(output, format=image.format)
    return output.getvalue()

# Upload endpoint
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    content = file.read()
    original_response = upload_to_github(file.filename, content)
    downsized_content = downsize_image(content)
    downsized_filename = f"downsized_{file.filename}"
    downsized_response = upload_to_github(downsized_filename, downsized_content)
    return f'''
    <h3>Upload Complete!</h3>
    <p>Original File URL: <a href="{GITHUB_RAW_URL}{file.filename}">{file.filename}</a></p>
    <p>Downsized File URL: <a href="{GITHUB_RAW_URL}{downsized_filename}">{downsized_filename}</a></p>
    <button onclick="location.href='/upload.html'">Back to Upload</button>
    <button onclick="location.href='/list'">View Uploaded Files</button>
    '''

# List uploaded files
@app.route('/list')
def list_files():
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    files = response.json()

    file_list = ''
    for file in files:
        filename = file['name']
        original_url = f"{GITHUB_RAW_URL}{filename}"
        
        # Check if the file is downsized
        if filename.startswith("downsized_"):
            downsized_url = original_url
            original_filename = filename.replace("downsized_", "")
            original_url = f"{GITHUB_RAW_URL}{original_filename}"
            file_list += f'''
            <li>
                <p>Original: <a href="{original_url}">{original_filename}</a></p>
                <p>Downsized: <a href="{downsized_url}">{filename}</a></p>
                <button onclick="deleteFile('{filename}')">Delete</button>
            </li>
            '''
        else:
            # If it's an original file without a downsized counterpart
            downsized_filename = f"downsized_{filename}"
            downsized_url = f"{GITHUB_RAW_URL}{downsized_filename}"
            file_list += f'''
            <li>
                <p>Original: <a href="{original_url}">{filename}</a></p>
                <p>Downsized: <a href="{downsized_url}">{downsized_filename}</a></p>
                <button onclick="deleteFile('{filename}')">Delete</button>
            </li>
            '''
    return f'''
    <h2>Uploaded Files</h2>
    <ul>{file_list}</ul>
    <button onclick="location.href='/upload.html'">Back to Upload</button>
    <script>
    function deleteFile(filename) {{
        fetch('/delete/' + filename, {{ method: 'DELETE' }})
            .then(response => location.reload());
    }}
    </script>
    '''
# Home page
@app.route('/')
def home():
    return "Hello, GitHub File Uploader!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
