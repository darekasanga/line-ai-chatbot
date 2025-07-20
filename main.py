import os
import io
import base64
import datetime
import requests
from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from github import Github
from dotenv import load_dotenv
import json

# .envの読み込み
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("REPO_NAME")
BRANCH_NAME = os.getenv("BRANCH_NAME", "main")

# LINE設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_REPLY_ENDPOINT = "https://api.line.me/v2/bot/message/reply"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
}

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# GitHubリポジトリの取得
g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

# GitHubに画像保存
def save_image_to_github(image_data: bytes, filename: str):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    path = f"images/{filename}"
    repo.create_file(path, f"Upload {filename}", image_data, branch=BRANCH_NAME)
    return f"https://raw.githubusercontent.com/{REPO_NAME}/{BRANCH_NAME}/{path}"

# 画像リサイズ（最大300KB）
def resize_image(image_bytes: bytes, max_kb=300):
    image = Image.open(io.BytesIO(image_bytes))
    image_format = image.format
    quality = 85
    for _ in range(10):
        buffer = io.BytesIO()
        image.save(buffer, format=image_format, quality=quality)
        data = buffer.getvalue()
        if len(data) <= max_kb * 1024:
            return data
        quality -= 10
    return data  # 最後の品質でもダメならそのまま

# FlexMessage送信
def send_flex_message(reply_token: str, preview_url: str, original_url: str, resized_url: str):
    with open("flex_template.json", "r", encoding="utf-8") as f:
        flex_json = f.read()

    now = datetime.datetime.now()
    post_date = now.strftime("%Y/%m/%d %H:%M")
    delete_date = (now + datetime.timedelta(days=30)).strftime("%Y/%m/%d")

    flex_filled = flex_json.replace("{{preview_url}}", preview_url)
    flex_filled = flex_filled.replace("{{original_url}}", original_url)
    flex_filled = flex_filled.replace("{{resized_url}}", resized_url)
    flex_filled = flex_filled.replace("{{post_date}}", post_date)
    flex_filled = flex_filled.replace("{{delete_date}}", delete_date)

        print("📦 Flex送信内容:", flex_filled)  # ← ここを追加

    payload = {
        "replyToken": reply_token,
        "messages": [json.loads(flex_filled)]
    }
    requests.post(LINE_REPLY_ENDPOINT, headers=HEADERS, data=json.dumps(payload))

# LINE Webhook
@app.post("/callback")
async def callback(request: Request):
    body = await request.json()
    print("LINE受信内容:", body)  # ←追加
    events = body.get("events", [])
    for event in events:
        if event["type"] == "message" and event["message"]["type"] == "image":
            reply_token = event["replyToken"]
            message_id = event["message"]["id"]

            image_res = requests.get(
                f"https://api-data.line.me/v2/bot/message/{message_id}/content",
                headers={"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
            )
            image_bytes = image_res.content

            # オリジナル画像をGitHubに保存
            original_filename = f"{message_id}.jpg"
            original_url = save_image_to_github(image_bytes, original_filename)

            # 圧縮画像を作成し保存
            resized_data = resize_image(image_bytes)
            resized_filename = f"{message_id}_resized.jpg"
            resized_url = save_image_to_github(resized_data, resized_filename)

            # FlexMessage送信
            send_flex_message(reply_token, preview_url=resized_url,
                              original_url=original_url, resized_url=resized_url)
    return "ok"

# HTMLページ（画像一覧）
@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    contents = repo.get_contents("images", ref=BRANCH_NAME)
    image_urls = []
    for content in contents:
        if content.name.endswith(".jpg"):
            image_urls.append(content.download_url)
    return templates.TemplateResponse("index.html", {"request": request, "images": image_urls})
