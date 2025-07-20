# main.py

import os
import io
import requests
from fastapi import FastAPI, Request
from PIL import Image
from github import Github

app = FastAPI()

# 🆕 環境変数（envがない場合はダミー値でOK）
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "dummy_token")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "dummy_token")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "darekasanga/line-ai-chatbot")
BRANCH = os.environ.get("GITHUB_BRANCH", "main")  # または file ブランチ

# 🧠 GitHub に画像を保存
def save_image_to_github(image_data: bytes, filename: str) -> str:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(GITHUB_REPO)
    path = f"images/{filename}"
    repo.create_file(
        path=path,
        message=f"Add {filename}",
        content=image_data,
        branch=BRANCH
    )
    return f"https://raw.githubusercontent.com/{GITHUB_REPO}/{BRANCH}/{path}"

# 📏 リサイズ関数
def resize_image(image_data: bytes) -> bytes:
    with Image.open(io.BytesIO(image_data)) as img:
        img.thumbnail((512, 512))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

# 💬 Flex Message 送信（最低限の構成）
def send_flex_message(reply_token, preview_url, original_url, resized_url):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    flex_message = {
        "type": "flex",
        "altText": "画像がアップロードされました！",
        "contents": {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": preview_url,
                "size": "full",
                "aspectRatio": "1.51:1",
                "aspectMode": "cover"
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "link",
                        "height": "sm",
                        "action": {"type": "uri", "label": "📷 Original", "uri": original_url}
                    },
                    {
                        "type": "button",
                        "style": "link",
                        "height": "sm",
                        "action": {"type": "uri", "label": "🖼 Resized", "uri": resized_url}
                    }
                ],
                "flex": 0
            }
        }
    }
    payload = {
        "replyToken": reply_token,
        "messages": [flex_message]
    }
    requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=payload)

# 🔁 LINE コールバック処理
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

                # 📥 LINE画像取得
                image_res = requests.get(
                    f"https://api-data.line.me/v2/bot/message/{message_id}/content",
                    headers={"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
                )
                image_bytes = image_res.content

                # GitHubに保存
                original_filename = f"{message_id}.jpg"
                original_url = save_image_to_github(image_bytes, original_filename)

                resized_bytes = resize_image(image_bytes)
                resized_filename = f"{message_id}_resized.jpg"
                resized_url = save_image_to_github(resized_bytes, resized_filename)

                # Flex Message送信
                send_flex_message(reply_token, preview_url=resized_url, original_url=original_url, resized_url=resized_url)

        return "ok"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
