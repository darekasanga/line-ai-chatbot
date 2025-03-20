from flask import Flask, request, jsonify
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
GITHUB_REPO = "darekasanga/line-ai-chatbot"  # Replace with your actual username and repo name
GITHUB_BRANCH = "main"
GITHUB_API = "https://api.github.com"
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/"

# Upload file to GitHub
def upload_to_github(filename, content):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{filename}"
    encoded_content = base64.b64encode(content).decode("utf-8")
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "message": f"Add {filename}",
        "content": encoded_content,
        "branch": GITHUB_BRANCH
    }
    response = requests.put(url, headers=headers, data=json.dumps(data))
    return response

# Resize the image
def downsize_image(image_data, max_size=(800, 800)):
    image = Image.open(BytesIO(image_data))
    image.thumbnail(max_size)  # Maintain aspect ratio
    output = BytesIO()
    image.save(output, format=image.format)  # Save in the same format
    return output.getvalue()

# File upload endpoint
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400

    try:
        content = file.read()

        # Upload original file
        original_response = upload_to_github(file.filename, content)
        if original_response.status_code != 201:
            return jsonify({"status": "error", "message": original_response.json()}), 500
        original_url = f"{GITHUB_RAW_URL}{file.filename}"

        # Create downsized version
        downsized_content = downsize_image(content)
        downsized_filename = f"downsized_{file.filename}"
        downsized_response = upload_to_github(downsized_filename, downsized_content)
        if downsized_response.status_code != 201:
            return jsonify({"status": "error", "message": downsized_response.json()}), 500
        downsized_url = f"{GITHUB_RAW_URL}{downsized_filename}"

        return jsonify({
            "status": "success",
            "original_url": original_url,
            "downsized_url": downsized_url
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# File upload page
@app.route('/upload.html')
def upload_page():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>File Uploader</title>
    </head>
    <body>
        <h2>Upload a File to GitHub Pages</h2>
        <form id="uploadForm" enctype="multipart/form-data" method="POST" action="/upload">
            <input type="file" name="file" required>
            <button type="submit">Upload</button>
        </form>
    </body>
    </html>
    '''

# Home page
@app.route('/')
def home():
    return "Hello, GitHub Pages File Uploader and Chatbot are running with downsizing feature!", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
# Create a new branch from the main branch
def create_branch(branch_name):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/git/refs/heads/main"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Get the latest commit SHA of the main branch
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        sha = response.json()["object"]["sha"]
        
        # Create a new branch with the same SHA
        new_branch_url = f"{GITHUB_API}/repos/{GITHUB_REPO}/git/refs"
        data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": sha
        }
        branch_response = requests.post(new_branch_url, headers=headers, data=json.dumps(data))
        if branch_response.status_code == 201:
            print(f"Branch '{branch_name}' created successfully.")
        else:
            print(f"Branch '{branch_name}' already exists or failed to create.")
    else:
        print("Error fetching main branch SHA.")

# Upload file to GitHub on a specified branch
def upload_to_github(filename, content, branch_name):
    # Ensure the branch exists
    create_branch(branch_name)

    # Upload the file
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{filename}?ref={branch_name}"
    encoded_content = base64.b64encode(content).decode("utf-8")
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "message": f"Add {filename} to {branch_name}",
        "content": encoded_content,
        "branch": branch_name
    }
    response = requests.put(url, headers=headers, data=json.dumps(data))
    print("GitHub API Response:", response.json())  # Debugging
    return response
