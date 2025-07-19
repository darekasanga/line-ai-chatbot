from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import hashlib, hmac, os, requests, base64, time

app = FastAPI()

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = "darekasanga/line-ai-chatbot"
GITHUB_BRANCH = "main"
UPLOAD_PATH = "uploaded_files"

@app.get("/")
def root():
    return {"message": "Hello from FastAPI on Vercel!"}

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    signature = request.headers.get("x-line-signature", "")
    
    if not is_valid_signature(body, signature):
        return JSONResponse(status_code=403, content={"message": "Invalid signature"})

    events = (await request.json()).get("events", [])
    for event in events:
        if event["type"] == "message":
            user_id = event["source"]["userId"]
            msg_type = event["message"]["type"]
            if msg_type == "text":
                user_msg = event["message"]["text"]
                background_tasks.add_task(respond_and_upload_text, user_id, user_msg)
            elif msg_type == "image":
                message_id = event["message"]["id"]
                background_tasks.add_task(handle_image_upload, user_id, message_id)

    return JSONResponse(content={"message": "OK"})

def is_valid_signature(body: bytes, signature: str) -> bool:
    hash = hmac.new(LINE_CHANNEL_SECRET.encode(), body, hashlib.sha256).digest()
    encoded = base64.b64encode(hash).decode()
    return hmac.compare_digest(encoded, signature)

def respond_and_upload_text(user_id: str, msg: str):
    # 1. reply to user
    reply_msg = f"You said: {msg}"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": reply_msg}]
    }
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=payload)

    # 2. upload to GitHub
    filename = f"{int(time.time())}.txt"
    content = base64.b64encode(msg.encode()).decode()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{UPLOAD_PATH}/{filename}"
    commit_msg = f"Upload from LINE user {user_id}"
    data = {
        "message": commit_msg,
        "content": content,
        "branch": GITHUB_BRANCH
    }
    headers["Authorization"] = f"token {GITHUB_TOKEN}"
    requests.put(url, headers=headers, json=data)

def handle_image_upload(user_id: str, message_id: str):
    # 1. Get image binary from LINE server
    content_url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    res = requests.get(content_url, headers=headers)
    if res.status_code != 200:
        return

    image_data = res.content
    encoded_image = base64.b64encode(image_data).decode()
    filename = f"{int(time.time())}.jpg"

    # 2. Upload to GitHub
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{UPLOAD_PATH}/{filename}"
    commit_msg = f"Image upload from LINE user {user_id}"
    data = {
        "message": commit_msg,
        "content": encoded_image,
        "branch": GITHUB_BRANCH
    }
    gh_headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    requests.put(url, headers=gh_headers, json=data)

    # 3. Reply to user
    reply_headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    reply_payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": "画像を受け取り、アップロードしました！"}]
    }
    requests.post("https://api.line.me/v2/bot/message/push", headers=reply_headers, json=reply_payload)
