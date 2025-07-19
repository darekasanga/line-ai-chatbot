from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()  # これが絶対に必要！

@app.get("/")
async def root():
    return {"message": "Hello from FastAPI on Vercel!"}

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    print("Webhook received:", body)
    return JSONResponse(content={"message": "Webhook OK"})
    
# --- LINE Messaging API reply logic ---

import os
from fastapi import HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

# Set from environment (Vercel .env)
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Line-Signature")
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=401, detail="Invalid signature")
    return JSONResponse(content={"message": "OK"})

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    incoming = event.message.text
    reply = f"You said: {incoming}"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )
