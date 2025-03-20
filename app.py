from flask import Flask, request, jsonify, send_from_directory
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
    try:
        url = f"{GITHUB_API}/repos/{GITHUB_REPO}/git/refs/heads/main"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        response = requests.get(url, headers=headers)
        print(f"Main branch response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            sha = response.json()["object"]["sha"]
            branch_check_url = f"{GITHUB_API}/repos/{GITHUB_REPO}/git/refs/heads/{branch_name}"
            check_response = requests.get(branch_check_url, headers=headers)
            print(f"Check branch response: {check_response.status_code} - {check_response.text}")

            if check_response.status_code != 200:
                new_branch_url = f"{GITHUB_API}/repos/{GITHUB_REPO}/git/refs"
                data = {"ref": f"refs/heads/{branch_name}", "sha": sha}
                create_response = requests.post(new_branch_url, headers=headers, data=json.dumps(data))
                print(f"Branch creation response: {create_response.status_code} - {create_response.text}")
    except Exception as e:
        print(f"Error during branch creation: {str(e)}")

# Test endpoint to check if the server is running
@app.route('/test')
def test():
    return "Test endpoint is working!"

# Serve static files (like JavaScript)
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# Upload page (HTML template)
@app.route('/upload.html')
def upload_page():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Upload Page</title>
        <script src="/static/render_upload.js"></script>
    </head>
    <body>
        <div id="upload-container">Loading...</div>
    </body>
    </html>
    '''

# Render the upload page using JSON (Flex Message format)
@app.route('/upload_page_json')
def upload_page_json():
    try:
        upload_page_json = {
            "altText": "Upload File",
            "contents": {
                "body": {
                    "contents": [
                        {
                            "margin": "md",
                            "size": "xl",
                            "text": "Upload a File",
                            "type": "text",
                            "weight": "bold"
                        },
                        {
                            "contents": [
                                {
                                    "margin": "md",
                                    "size": "sm",
                                    "text": "Select a file to upload:",
                                    "type": "text"
                                },
                                {
                                    "accept": "image/*",
                                    "action": {
                                        "label": "Browse",
                                        "type": "uri",
                                        "uri": "/upload"
                                    },
                                    "label": "Choose File",
                                    "name": "file",
                                    "type": "input"
                                }
                            ],
                            "layout": "vertical",
                            "type": "box"
                        },
                        {
                            "contents": [
                                {
                                    "action": {
                                        "label": "Upload",
                                        "text": "Upload",
                                        "type": "message"
                                    },
                                    "color": "#1DB446",
                                    "margin": "sm",
                                    "style": "primary",
                                    "type": "button"
                                },
                                {
                                    "action": {
                                        "label": "View Uploaded Files",
                                        "type": "uri",
                                        "uri": "/list"
                                    },
                                    "margin": "sm",
                                    "style": "secondary",
                                    "type": "button"
                                }
                            ],
                            "layout": "horizontal",
                            "margin": "md",
                            "type": "box"
                        }
                    ],
                    "layout": "vertical",
                    "type": "box"
                },
                "type": "bubble"
            },
            "type": "flex"
        }
        print(f"Upload Page JSON: {json.dumps(upload_page_json, indent=2)}")
        return jsonify(upload_page_json)
    except Exception as e:
        print(f"Error generating upload page JSON: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Upload file endpoint
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400

    file = request.files['file']
    content = file.read()

    original_filename = file.filename
    downsized_filename = f"downsized_{original_filename}"
    print(f"Received file: {original_filename}")

    # Upload original file
    response = upload_to_github(original_filename, content)
    print(f"Upload response: {response.status_code} - {response.text}")

    return f'''
    <h3>Upload Complete!</h3>
    <p>Original URL: <a href="{GITHUB_RAW_URL}{original_filename}">{original_filename}</a></p>
    <button onclick="location.href='/upload.html'">Back to Upload</button>
    <button onclick="location.href='/list'">View Uploaded Files</button>
    '''

# List uploaded files
@app.route('/list')
def list_files():
    try:
        url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents?ref={GITHUB_BRANCH}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(url, headers=headers)

        print(f"List files response: {response.status_code} - {response.text}")

        if response.status_code != 200:
            return f"Error fetching file list: {response.json().get('message', 'Unknown error')}", 500

        files = response.json()
        file_list = ''.join(f'<li><a href="{GITHUB_RAW_URL}{file["name"]}">{file["name"]}</a></li>' for file in files)

        return f'''
        <h2>Uploaded Files</h2>
        <ul>{file_list}</ul>
        <button onclick="location.href='/upload.html'">Back to Upload</button>
        '''
    except Exception as e:
        print(f"Error during list page generation: {str(e)}")
        return f"Internal Server Error: {str(e)}", 500

# Home page
@app.route('/')
def home():
    return "Hello, GitHub File Uploader!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
