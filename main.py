from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import os
import requests
import base64
import hashlib
import hmac
import time
from PIL import Image  # 🆕 画像処理
import io

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
                background_tasks.add_task(handle_image, message_id)

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

# 🆕 Resize image to under 300KB
def resize_image_to_under_300kb(image_data: bytes) -> bytes:
    image = Image.open(io.BytesIO(image_data)).convert("RGB")
    quality = 95
    while quality > 10:
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality)
        if buffer.tell() <= 300 * 1024:
            return buffer.getvalue()
        quality -= 5
    return buffer.getvalue()

# 🧩 Handle image message
def handle_image(message_id: str):
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    res = requests.get(f"https://api-data.line.me/v2/bot/message/{message_id}/content", headers=headers)
    if res.status_code != 200:
        return

    image_data = res.content
    timestamp = int(time.time())
    filename = f"image_{timestamp}.jpg"
    resized_filename = f"image_{timestamp}_small.jpg"

    content = base64.b64encode(image_data).decode()
    resized_image_data = resize_image_to_under_300kb(image_data)
    resized_content = base64.b64encode(resized_image_data).decode()

    upload_to_github(filename, content)
    upload_to_github(resized_filename, resized_content)

# 🆕 Upload helper
def upload_to_github(filename: str, content: str):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{UPLOAD_PATH}/{filename}"
    data = {
        "message": f"Upload {filename}",
        "content": content,
        "branch": GITHUB_BRANCH
    }
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    requests.put(url, headers=headers, json=data)

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
            image_urls.append((f["name"], f["download_url"]))
    return image_urls

# 🧩 HTML image list
@app.get("/list", response_class=HTMLResponse)
def list_images():
    items = get_uploaded_image_urls()
    html = "<h1>📸 画像一覧</h1><div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1em;'>"
    grouped = {}
    for name, url in items:
        base = name.replace("_small", "").rsplit(".", 1)[0]
        grouped.setdefault(base, {})
        if "_small" in name:
            grouped[base]["small"] = (name, url)
        else:
            grouped[base]["original"] = (name, url)

    for base, versions in grouped.items():
        html += "<div>"
        if "original" in versions:
            html += f"<img src='{versions['original'][1]}' width='200'/><br/>"
        html += "<form action='/delete' method='post'>"
        if "original" in versions:
            html += f"<input type='hidden' name='filename' value='{versions['original'][0]}'/>"
            html += f"<button type='submit'>❌ Delete Original</button><br/>"
            html += f"<a href='{versions['original'][1]}' target='_blank'>🔗 Original URL</a><br/>"
        if "small" in versions:
            html += f"<input type='hidden' name='filename' value='{versions['small'][0]}'/>"
            html += f"<button type='submit'>❌ Delete Small</button><br/>"
            html += f"<a href='{versions['small'][1]}' target='_blank'>🔗 Small URL</a>"
        html += "</form></div>"
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
