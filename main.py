from fastapi import FastAPI, Request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, FileMessage, TextSendMessage
import base64, requests, os

app = FastAPI()

# Load from environment
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = "darekasanga/line-ai-chatbot"
GITHUB_BRANCH = "main"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    signature = request.headers["X-Line-Signature"]
    handler.handle(body.decode("utf-8"), signature)
    return "OK"

@handler.add(MessageEvent, message=FileMessage)
def handle_file(event):
    message_id = event.message.id
    file_name = event.message.file_name

    file_content = line_bot_api.get_message_content(message_id)
    binary_data = b''.join(chunk for chunk in file_content.iter_content())

    # Upload to GitHub
    upload_to_github(file_name, binary_data)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"✅ Uploaded `{file_name}` to GitHub!")
    )

def upload_to_github(filename, data):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/uploads/{filename}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "message": f"Add {filename}",
        "content": base64.b64encode(data).decode("utf-8"),
        "branch": GITHUB_BRANCH
    }
    response = requests.put(url, headers=headers, json=payload)
    if response.status_code >= 400:
        print(f"❌ GitHub upload failed: {response.json()}")
