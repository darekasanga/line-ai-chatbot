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

# Resize the image with adaptive settings to limit size to 300 KB
def downsize_image(image_data, max_size=(800, 800), target_size=300 * 1024):
    try:
        image = Image.open(BytesIO(image_data))
        image = image.convert("RGB")  # Convert to RGB for JPEG compatibility
        image.thumbnail(max_size, Image.ANTIALIAS)  # Efficient scaling

        # Adaptive quality reduction to reach the target size
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

            quality -= 5  # Reduce quality and try again

        print(f"Final downsized size: {size} bytes")
        return output.getvalue()

    except Exception as e:
        print(f"Error during image downsizing: {str(e)}")
        return image_data

# Delete file from GitHub
def delete_from_github(filename):
    print(f"Attempting to delete file: {filename}")

    encoded_filename = requests.utils.quote(filename, safe='')
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{encoded_filename}?ref={GITHUB_BRANCH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    get_response = requests.get(url, headers=headers)
    print(f"GET Response Status: {get_response.status_code}")
    print(f"GET Response Text: {get_response.text}")

    if get_response.status_code == 200:
        sha = get_response.json().get("sha")
        if not sha:
            print(f"Error: SHA not found for file {filename}")
            return jsonify({"status": "error", "message": "SHA not found"}), 404

        print(f"Deleting file {filename} with SHA {sha}")
        data = {
            "message": f"Delete {filename}",
            "sha": sha,
            "branch": GITHUB_BRANCH
        }

        delete_response = requests.delete(url, headers=headers, data=json.dumps(data))
        print(f"Delete Response Status: {delete_response.status_code}")
        print(f"Delete Response Text: {delete_response.text}")

        if delete_response.status_code == 200:
            print(f"Successfully deleted {filename}")
            return jsonify({"status": "success", "message": f"Deleted {filename}"})
        else:
            print(f"Failed to delete {filename}: {delete_response.text}")
            return jsonify({"status": "error", "message": delete_response.json().get("message", "Failed to delete file")})
    else:
        print(f"File {filename} not found for deletion.")
        return jsonify({"status": "error", "message": "File not found"}), 404

# List uploaded files
@app.route('/list')
def list_files():
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)

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

# Upload page
@app.route('/upload.html')
def upload_page():
    return '''
    <h2>Upload a File</h2>
    <form method="POST" enctype="multipart/form-data" action="/upload">
        <input type="file" name="file" required>
        <button type="submit">Upload</button>
    </form>
    <button onclick="location.href='/list'">View Uploaded Files</button>
    '''

# Home page
@app.route('/')
def home():
    return "Hello, GitHub File Uploader!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
