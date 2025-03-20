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

# Upload file to GitHub on the "file" branch
def upload_to_github(filename, content):
    try:
        create_branch(GITHUB_BRANCH)
        url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{filename}?ref={GITHUB_BRANCH}"
        print(f"Uploading to URL: {url}")
        encoded_content = base64.b64encode(content).decode("utf-8")
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }

        get_response = requests.get(url, headers=headers)
        print(f"GET Response Status: {get_response.status_code}")
        print(f"GET Response Text: {get_response.text}")

        sha = None
        if get_response.status_code == 200:
            sha = get_response.json().get("sha")
            print(f"Existing file SHA: {sha}")

        data = {
            "message": f"Add or update {filename} to {GITHUB_BRANCH}",
            "content": encoded_content,
            "branch": GITHUB_BRANCH
        }
        if sha:
            data["sha"] = sha

        response = requests.put(url, headers=headers, data=json.dumps(data))
        print(f"Upload Response Status: {response.status_code}")
        print(f"Upload Response Text: {response.text}")
        return response
    except Exception as e:
        print(f"Error during upload: {str(e)}")
        return None

# Resize the image with adaptive settings to limit size to 300 KB
def downsize_image(image_data, max_size=(800, 800), target_size=300 * 1024):
    try:
        image = Image.open(BytesIO(image_data))
        image = image.convert("RGB")
        image.thumbnail(max_size, Image.ANTIALIAS)

        quality = 95
        output = BytesIO()

        while quality > 5:
            output.seek(0)
            output.truncate()
            image.save(output, format="JPEG", quality=quality)
            size = output.tell()
            print(f"Trying quality {quality}: {size} bytes")

            if size <= target_size:
                print(f"Successfully downsized image to {size} bytes")
                return output.getvalue()

            quality -= 5

        print(f"Final downsized size: {size} bytes")
        return output.getvalue()
    except Exception as e:
        print(f"Error during image downsizing: {str(e)}")
        return image_data

# List uploaded files
@app.route('/list')
def list_files():
    try:
        url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents?ref={GITHUB_BRANCH}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(url, headers=headers)

        print(f"List Page URL: {url}")
        print(f"List Page Response Status: {response.status_code}")
        print(f"List Page Response Text: {response.text}")

        if response.status_code != 200:
            return f"Error fetching file list: {response.json().get('message', 'Unknown error')}", 500

        files = response.json()
        file_list = ''.join(f'''
            <li>
                <p>Original: <a href="{GITHUB_RAW_URL}{file['name']}">{file['name']}</a></p>
                <p>Downsized: <a href="{GITHUB_RAW_URL}downsized_{file['name']}">downsized_{file['name']}</a></p>
                <button onclick="deleteFile('{file['name']}')">Delete</button>
            </li>
        ''' for file in files)

        return f'''
        <h2>Uploaded Files</h2>
        <ul>{file_list}</ul>
        <button onclick="location.href='/upload.html'">Back to Upload</button>
        '''
    except Exception as e:
        print(f"Error during list page generation: {str(e)}")
        return f"Internal Server Error: {str(e)}", 500

# Upload endpoint
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400

    file = request.files['file']
    content = file.read()

    original_response = upload_to_github(file.filename, content)
    downsized_content = downsize_image(content)
    downsized_filename = f"downsized_{file.filename}"
    downsized_response = upload_to_github(downsized_filename, downsized_content)

    return f'''
    <h3>Upload Complete!</h3>
    <p>Original URL: <a href="{GITHUB_RAW_URL}{file.filename}">{file.filename}</a></p>
    <p>Downsized URL: <a href="{GITHUB_RAW_URL}{downsized_filename}">{downsized_filename}</a></p>
    <button onclick="location.href='/upload.html'">Back to Upload</button>
    <button onclick="location.href='/list'">View Uploaded Files</button>
    '''

@app.route('/upload.html')
def upload_page():
    upload_page_json = {
        "type": "flex",
        "altText": "Upload File",
        "contents": {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "Upload a File",
                        "weight": "bold",
                        "size": "xl",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "Select a file to upload:",
                                "size": "sm",
                                "margin": "md"
                            },
                            {
                                "type": "input",
                                "name": "file",
                                "label": "Choose File",
                                "accept": "image/*",
                                "action": {
                                    "type": "uri",
                                    "label": "Browse",
                                    "uri": "/upload"
                                }
                            }
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "button",
                                "action": {
                                    "type": "message",
                                    "label": "Upload",
                                    "text": "Upload"
                                },
                                "style": "primary",
                                "color": "#1DB446",
                                "margin": "sm"
                            },
                            {
                                "type": "button",
                                "action": {
                                    "type": "uri",
                                    "label": "View Uploaded Files",
                                    "uri": "/list"
                                },
                                "style": "secondary",
                                "margin": "sm"
                            }
                        ],
                        "margin": "md"
                    }
                ]
            }
        }
    }
    return jsonify(upload_page_json)

# Home page
@app.route('/')
def home():
    return "Hello, GitHub File Uploader!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
from flask import send_from_directory

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)
