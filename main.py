from fastapi import FastAPI, Request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, FileMessage, TextSendMessage
import base64, requests, os, threading

app = FastAPI()

@app.get("/")
def root():
    return {"message": "LINE Chatbot is live!"}

# Environment variables (set in Vercel)
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
    signature = request.headers.get("X-Line-Signature")

    # Handle in background thread to avoid timeout
    def handle_async():
        try:
            handler.handle(body.decode("utf-8"), signature)
        except Exception as e:
            print(f"❌ Error in handler: {e}")

    threading.Thread(target=handle_async).start()

    return "OK"

@handler.add(MessageEvent, message=FileMessage)
def handle_file(event):
    message_id = event.message.id
    file_name = event.message.file_name

    try:
        # Get file content
        file_content = line_bot_api.get_message_content(message_id)
        binary_data = b''.join(chunk for chunk in file_content.iter_content())

        # Upload to GitHub
        success = upload_to_github(file_name, binary_data)

        # Respond to user
        if success:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"✅ File `{file_name}` uploaded to GitHub!")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"❌ Failed to upload `{file_name}`.")
            )

    except Exception as e:
        print(f"❌ File handler error: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="⚠️ Error processing your file.")
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
    print(f"📤 GitHub response: {response.status_code} {response.text}")
    return response.status_code in [200, 201]
