# OLD
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# NEW - Add LINE Bot SDK
from linebot import LineBotApi, WebhookHandler                     # NEW
from linebot.models import MessageEvent, TextMessage, TextSendMessage  # NEW
from linebot.exceptions import InvalidSignatureError               # NEW
import os                                                          # NEW

# NEW - Get LINE secrets from environment
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")             # NEW
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN") # NEW

# NEW - Initialize LINE bot clients
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)               # NEW
handler = WebhookHandler(LINE_CHANNEL_SECRET)                      # NEW

# OLD
app = FastAPI()

# OLD
@app.get("/")
async def root():
    return {"message": "Hello from FastAPI on Vercel!"}

# CHANGED: Replacing simple JSON with LINE webhook logic
@app.post("/webhook")
async def webhook(request: Request):
    # OLD
    # data = await request.json()
    # print("Received webhook:", data)
    # return JSONResponse(content={"status": "ok"})

    # NEW - LINE-specific handling
    signature = request.headers.get("X-Line-Signature")            # NEW
    body = await request.body()                                    # NEW

    try:                                                           # NEW
        handler.handle(body.decode("utf-8"), signature)            # NEW
    except InvalidSignatureError:                                  # NEW
        return JSONResponse(status_code=400, content={"message": "Invalid signature"})  # NEW

    return JSONResponse(content={"status": "ok"})                   # NEW

# NEW - Reply when user sends text
@handler.add(MessageEvent, message=TextMessage)                    # NEW
def handle_message(event):                                         # NEW
    user_text = event.message.text                                 # NEW
    reply_text = f"✅ You said: {user_text}"                       # NEW
    line_bot_api.reply_message(                                    # NEW
        event.reply_token,                                         # NEW
        TextSendMessage(text=reply_text)                           # NEW
    )                                                              # NEW
