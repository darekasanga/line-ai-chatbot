import os
import base64
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, ImageMessage
from linebot.exceptions import InvalidSignatureError
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Environment variables
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = "darekasanga/line-ai-chatbot"
GITHUB_BRANCH = "file"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.get("/")
def root():
    return {"message": "Hello from FastAPI on Vercel!"}

@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Line-Signature")
    body = await request.body()

    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        return JSONResponse(status_code=400, content={"message": "Invalid signature"})

    return {"message": "OK"}

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    message_id = event.message.id
    image_content = line_bot_api.get_message_content(message_id)
    local_path = f"/tmp/{message_id}.jpg"

    with open(local_path, "wb") as f:
        for chunk in image_content.iter_content():
            f.write(chunk)

    # Upload to GitHub
    upload_to_github(local_path, f"{message_id}.jpg")

def upload_to_github(local_path, repo_path):
    with open(local_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    data = {
        "message": f"Upload {repo_path}",
        "content": content,
        "branch": GITHUB_BRANCH
    }

    res = requests.put(url, headers=headers, json=data)
    print(res.status_code, res.json())
