from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import os
import requests
import base64
import hashlib
import hmac
import time
from PIL import Image
from io import BytesIO

app = FastAPI()

# 🧩 Config
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = "darekasanga/line-ai-chatbot"
GITHUB_BRANCH = "main"
UPLOAD_PATH = "uploaded_files"
RESIZED_PATH = "resized_files"
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

    # Upload original
    content = base64.b64encode(image_data).decode()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{UPLOAD_PATH}/{filename}"
    commit_msg = f"Upload image {filename}"
    data = {
        "message": commit_msg,
        "content": content,
        "branch": GITHUB_BRANCH
    }
    headers_upload = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    requests.put(url, headers=headers_upload, json=data)

    # 🆕 Resize and upload resized image
    try:
        img = Image.open(BytesIO(image_data))
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        while buffer.tell() > 300 * 1024:  # 300KB
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=75)
        resized_content = base64.b64encode(buffer.getvalue()).decode()
        resize_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{RESIZED_PATH}/{resized_filename}"
        resize_data = {
            "message": f"Upload resized image {resized_filename}",
            "content": resized_content,
            "branch": GITHUB_BRANCH
        }
        requests.put(resize_url, headers=headers_upload, json=resize_data)
    except:
        pass

# 🧩 Get image URLs from GitHub
def get_uploaded_image_urls():
    def fetch(path):
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        res = requests.get(url, headers=headers)
        return res.json() if res.status_code == 200 else []

    originals = fetch(UPLOAD_PATH)
    resized = fetch(RESIZED_PATH)

    resized_map = {f["name"]: f["download_url"] for f in resized if f["name"].endswith(".jpg")}
    image_pairs = []
    for f in originals:
        if f["name"].endswith(".jpg"):
            original_url = f["download_url"]
            resized_url = resized_map.get(f["name"].replace(".jpg", "_small.jpg"))
            image_pairs.append({"original": original_url, "resized": resized_url, "name": f["name"]})
    return image_pairs

# 🧩 HTML image list
@app.get("/list", response_class=HTMLResponse)
def list_images():
    items = get_uploaded_image_urls()
    html = "<h1>📸 画像一覧</h1><div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1em;'>"
    for item in items:
        html += f"""
        <div>
            <img src='{item['original']}' width='200'/><br/>
            <form action='/delete' method='post'>
                <input type='hidden' name='filename' value='{item['name']}'/>
                <button type='submit'>❌ 削除</button>
            </form>
            <p>{item['name']}</p>
            <a href='{item['original']}' target='_blank'>🔗 オリジナル</a><br/>
            {f"<a href='{item['resized']}' target='_blank'>🔗 300KB版</a>" if item['resized'] else ''}
        </div>
        """
    html += "</div>"
    return html

# 🧩 Delete image
@app.post("/delete")
def delete_file(filename: str = Form(...)):
    def delete_from(path):
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}/{filename}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            return False
        sha = res.json().get("sha")
        data = {
            "message": f"Delete {filename}",
            "sha": sha,
            "branch": GITHUB_BRANCH
        }
        return requests.delete(url, headers=headers, json=data).status_code in [200, 204]

    deleted = delete_from(UPLOAD_PATH)
    delete_from(RESIZED_PATH)  # Try resized version too
    if deleted:
        return RedirectResponse(url="/list", status_code=303)
    else:
        return HTMLResponse(content="ファイルが見つかりませんでした", status_code=404)
