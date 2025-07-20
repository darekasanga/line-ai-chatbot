import os
import io
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from PIL import Image
from github import Github
from datetime import datetime, timedelta

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# ✅ 環境変数の代わりにハードコーディング（安全のため本番では使わないでね!）
LINE_CHANNEL_ACCESS_TOKEN = "YOUR_LINE_CHANNEL_ACCESS_TOKEN"
GITHUB_TOKEN = "YOUR_GITHUB_PERSONAL_ACCESS_TOKEN"
REPO_NAME = "darekasanga/line-ai-chatbot"
BRANCH_NAME = "file"

# ✅ GitHub 操作用
github = Github(GITHUB_TOKEN)
repo = github.get_repo(REPO_NAME)

def resize_image(image_data):
    image = Image.open(io.BytesIO(image_data))
    image.thumbnail((512, 512))
    output = io.BytesIO()
    image.save(output, format="JPEG")
    return output.getvalue()

def save_image_to_github(image_data, filename):
    now = datetime.now().isoformat()
    path = f"images/{filename}"
    message = f"Upload {filename} at {now}"
    repo.create_file(path, message, image_data, branch=BRANCH_NAME)
    return f"https://raw.githubusercontent.com/{REPO_NAME}/{BRANCH_NAME}/{path}"

def send_flex_message(reply_token, preview_url, original_url, resized_url):
    today = datetime.now().strftime("%Y-%m-%d")
    delete_day = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    flex_template = {
        "type": "flex",
        "altText": "Image uploaded",
        "contents": {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": preview_url,
                "size": "full",
                "aspectRatio": "1:1",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "✅ 投稿画像", "weight": "bold", "size": "lg"},
                    {"type": "text", "text": f"投稿日: {today}"},
                    {"type": "text", "text": f"削除予定: {delete_day}"},
                    {"type": "text", "text": f"Original: {original_url}", "wrap": True, "size": "xs"},
                    {"type": "text", "text": f"Resized: {resized_url}", "wrap": True, "size": "xs"}
                ]
            }
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "replyToken": reply_token,
        "messages": [flex_template]
    }
    requests.post("https://api.line.me/v2/bot/message/reply", json=payload, headers=headers)

@app.post("/callback")
async def callback(request: Request):
    try:
        body = await request.json()
        print("LINE受信内容:", body)

        events = body.get("events", [])
        for event in events:
            if event["type"] == "message" and event["message"]["type"] == "image":
                reply_token = event["replyToken"]
                message_id = event["message"]["id"]

                res = requests.get(
                    f"https://api-data.line.me/v2/bot/message/{message_id}/content",
                    headers={"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
                )
                image_bytes = res.content

                original_filename = f"{message_id}.jpg"
                original_url = save_image_to_github(image_bytes, original_filename)

                resized_data = resize_image(image_bytes)
                resized_filename = f"{message_id}_resized.jpg"
                resized_url = save_image_to_github(resized_data, resized_filename)

                send_flex_message(reply_token, preview_url=resized_url, original_url=original_url, resized_url=resized_url)

        return "ok"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    contents = repo.get_contents("images", ref=BRANCH_NAME)
    image_urls = []
    for content in contents:
        if content.name.endswith(".jpg"):
            image_urls.append(content.download_url)
    return templates.TemplateResponse("index.html", {"request": request, "images": image_urls})
