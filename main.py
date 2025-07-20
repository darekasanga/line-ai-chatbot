from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import os
import requests
import base64
import hashlib
import hmac
import time
import json
from datetime import datetime, timedelta

app = FastAPI()

# 🧩 Config
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = "darekasanga/line-ai-chatbot"
GITHUB_BRANCH = "main"
UPLOAD_PATH = "uploaded_files"
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

# 🧩 Home route
@app.get("/")
def root():
    return {"message": "LINE Bot with image upload + HTML list"}

# 🧩 Webhook from LINE
@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    signature = request.headers.get("x-line-signature", "")

    if not is_valid_signature(body, signature):
        return JSONResponse(status_code=403, content={"message": "Invalid signature"})

    events = (await request.json()).get("events", [])
    for event in events:
        if event["type"] == "message":
            if event["message"]["type"] == "text":
                user_id = event["source"]["userId"]
                user_msg = event["message"]["text"]
                background_tasks.add_task(reply_text, user_id, user_msg)
            elif event["message"]["type"] == "image":
                user_id = event["source"]["userId"]
                message_id = event["message"]["id"]
                background_tasks.add_task(handle_image, message_id, user_id)

    return JSONResponse(content={"message": "OK"})

# 🧩 Validate LINE Signature
def is_valid_signature(body: bytes, signature: str) -> bool:
    hash = hmac.new(LINE_CHANNEL_SECRET.encode(), body, hashlib.sha256).digest()
    encoded = base64.b64encode(hash).decode()
    return hmac.compare_digest(encoded, signature)

# 🧩 Reply to LINE text
def reply_text(user_id: str, msg: str):
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": f"You said: {msg}"}]
    }
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=payload)

# 🧩 Handle image message
def handle_image(message_id: str, user_id: str):
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    res = requests.get(f"https://api-data.line.me/v2/bot/message/{message_id}/content", headers=headers)
    if res.status_code != 200:
        return
    image_data = res.content
    timestamp = int(time.time())
    filename = f"image_{timestamp}.jpg"
    content = base64.b64encode(image_data).decode()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{UPLOAD_PATH}/{filename}"
    commit_msg = f"Upload image {filename}"
    data = {
        "message": commit_msg,
        "content": content,
        "branch": GITHUB_BRANCH
    }
    gh_headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    res_upload = requests.put(url, headers=gh_headers, json=data)
    if res_upload.status_code in [200, 201]:
        base_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{UPLOAD_PATH}/{filename}"
        send_flex_message(user_id, base_url, base_url, base_url)

# 🆕 Load Flex Message Template and fill in
def load_flex_message(original_url, small_url, preview_url):
    with open("flex_message.json", "r", encoding="utf-8") as f:
        raw_json = f.read()

    now = datetime.now()
    post_date = now.strftime("%Y-%m-%d %H:%M")
    expire_date = (now + timedelta(days=30)).strftime("%Y-%m-%d")

    filled_json = raw_json.replace("{{original_url}}", original_url) \
                          .replace("{{small_url}}", small_url) \
                          .replace("{{preview_url}}", preview_url) \
                          .replace("{{post_date}}", post_date) \
                          .replace("{{expire_date}}", expire_date)

    return json.loads(filled_json)

# 🆕 Send Flex Message to LINE
def send_flex_message(user_id, original_url, small_url, preview_url):
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    flex_content = load_flex_message(original_url, small_url, preview_url)
    payload = {
        "to": user_id,
        "messages": [{
            "type": "flex",
            "altText": "画像を保存しました",
            "contents": flex_content
        }]
    }
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=payload)

# 🧩 Get image URLs from GitHub
def get_uploaded_image_urls():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{UPLOAD_PATH}?ref={GITHUB_BRANCH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return []
    files = res.json()
    image_urls = []
    for f in files:
        if f["name"].lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
            image_urls.append(f["download_url"])
    return image_urls

# 🧩 HTML image list
@app.get("/list", response_class=HTMLResponse)
def list_images():
    urls = get_uploaded_image_urls()
    html = "<h1>📸 画像一覧</h1><div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1em;'>"
    for url in urls:
        name = url.split("/")[-1]
        html += f"""
        <div>
            <img src='{url}' width='200'/><br/>
            <form action='/delete' method='post'>
                <input type='hidden' name='filename' value='{name}'/>
                <button type='submit'>❌ 削除</button>
            </form>
            <p>{name}</p>
        </div>
        """
    html += "</div>"
    return html

# 🧩 Delete image
@app.post("/delete")
def delete_file(filename: str = Form(...)):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{UPLOAD_PATH}/{filename}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return HTMLResponse(content="ファイルが見つかりませんでした", status_code=404)

    sha = res.json().get("sha")
    data = {
        "message": f"Delete {filename}",
        "sha": sha,
        "branch": GITHUB_BRANCH
    }

    delete_res = requests.delete(url, headers=headers, json=data)
    if delete_res.status_code in [200, 204]:
        return RedirectResponse(url="/list", status_code=303)
    else:
        return HTMLResponse(content="削除に失敗しました", status_code=500)
