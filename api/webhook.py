import base64
import hashlib
import hmac
import io
import os
import time
import uuid
import requests
from datetime import datetime
from PIL import Image, ImageOps
from fastapi import FastAPI, Header, Request, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from github import Github, GithubException

load_dotenv()
app = FastAPI()

# ---- ENV ----
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET       = os.getenv("CHANNEL_SECRET")
GH_TOKEN             = os.getenv("GH_TOKEN")
REPO_OWNER           = os.getenv("REPO_OWNER")
REPO_NAME            = os.getenv("REPO_NAME")
BRANCH               = os.getenv("BRANCH", "main")

# ---- Image options ----
DOWNSIZE_WIDTH  = 1600
JPEG_Q_ORIG     = 95
JPEG_Q_SMALL    = 90

# ---- LINE helpers ----
def verify_line_signature(body: bytes, x_line_signature: str | None) -> bool:
    mac = hmac.new(CHANNEL_SECRET.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode("utf-8")
    return hmac.compare_digest(expected, x_line_signature or "")

def line_get_content(message_id: str) -> bytes:
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    headers = {"Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"}
    r = requests.get(url, headers=headers, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"get content failed: {r.status_code} {r.text}")
    return r.content

def line_reply(reply_token: str, messages: list):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
    }
    payload = {"replyToken": reply_token, "messages": messages}
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"LINE reply failed: {r.status_code} {r.text}")

# ---- Image helpers ----
def to_jpeg_bytes(src_bytes: bytes, quality: int = JPEG_Q_ORIG) -> bytes:
    img = Image.open(io.BytesIO(src_bytes))
    img = ImageOps.exif_transpose(img).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()

def make_small(jpeg_bytes: bytes, target_w: int) -> bytes:
    img = Image.open(io.BytesIO(jpeg_bytes))
    w, h = img.size
    if w > target_w:
        new_h = int(h * (target_w / float(w)))
        img = img.resize((target_w, new_h), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_Q_SMALL)
    return buf.getvalue()

# ---- GitHub helpers ----
def get_repo_client():
    if not GH_TOKEN:
        raise RuntimeError("GH_TOKEN is missing")
    if not REPO_OWNER or not REPO_NAME:
        raise RuntimeError("REPO_OWNER/REPO_NAME are missing")
    g = Github(GH_TOKEN)
    try:
        return g.get_repo(f"{REPO_OWNER}/{REPO_NAME}")
    except GithubException as e:
        raise RuntimeError(f"get_repo failed: {e.data}") from e

def gh_create_file(repo, path: str, content_bytes: bytes, message: str):
    repo.create_file(path, message, content_bytes, branch=BRANCH)

# ---- Flex builder ----
def build_flex(title_text: str, thumb_url: str, orig_url: str, small_url: str):
    return {
      "type": "flex",
      "altText": title_text,
      "contents": {
        "type": "bubble",
        "hero": {
          "type": "image",
          "url": thumb_url,
          "size": "full",
          "aspectRatio": "16:9",
          "aspectMode": "cover",
          "action": {"type": "uri", "label": "Open", "uri": orig_url}
        },
        "body": {
          "type": "box",
          "layout": "vertical",
          "contents": [
            {"type": "text", "text": title_text, "weight": "bold", "size": "md", "wrap": True},
            {"type": "text", "text": "Uploaded to GitHub", "size": "sm", "color": "#888888"}
          ]
        },
        "footer": {
          "type": "box",
          "layout": "vertical",
          "spacing": "sm",
          "contents": [
            {"type": "button", "style": "primary", "height": "sm",
             "action": {"type": "uri", "label": "Open Original", "uri": orig_url}},
            {"type": "button", "style": "secondary", "height": "sm",
             "action": {"type": "uri", "label": "Open Small", "uri": small_url}}
          ],
          "flex": 0
        }
      }
    }

# ---- 共通処理関数 ----
async def handle_webhook(request: Request, x_line_signature: str | None):
    body_bytes = await request.body()
    if not verify_line_signature(body_bytes, x_line_signature):
        raise HTTPException(status_code=401, detail="bad signature")

    data = await request.json()
    repo = get_repo_client()

    try:
        for ev in data.get("events", []):
            if ev.get("type") != "message":
                continue
            msg = ev.get("message", {})
            if msg.get("type") not in ("image", "file"):
                continue

            reply_token = ev.get("replyToken")
            message_id  = msg.get("id")

            # 1) 画像取得
            raw = line_get_content(message_id)

            # 2) 変換 & 縮小
            orig_jpeg  = to_jpeg_bytes(raw, JPEG_Q_ORIG)
            small_jpeg = make_small(orig_jpeg, DOWNSIZE_WIDTH)

            # 3) パス生成(年/月)
            ts  = time.strftime("%Y%m%d-%H%M%S")
            uid = uuid.uuid4().hex[:8]
            y   = datetime.utcnow().strftime("%Y")
            m   = datetime.utcnow().strftime("%m")
            folder     = f"uploads/{y}/{m}"
            orig_name  = f"{ts}-{uid}.jpg"
            small_name = f"{ts}-{uid}-small.jpg"
            orig_path  = f"{folder}/{orig_name}"
            small_path = f"{folder}/{small_name}"

            # 4) GitHub へアップロード
            gh_create_file(repo, orig_path,  orig_jpeg,  f"Add {orig_name}")
            gh_create_file(repo, small_path, small_jpeg, f"Add {small_name}")

            # 5) 公開URL
            raw_base  = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}"
            orig_url  = f"{raw_base}/{orig_path}"
            small_url = f"{raw_base}/{small_path}"

            # 6) Flex返信
            title = f"Uploaded {orig_name}"
            flex  = build_flex(title, small_url, orig_url, small_url)
            line_reply(reply_token, [flex])

    except Exception as e:
        # ← ここが修正点("" を消す)
        print("ERROR:", e)

    return JSONResponse({"ok": True})

# ---- Routes ----
@app.get("/")
def root():
    return {"ok": True}

@app.get("/api/webhook")
def root_alias():
    return {"ok": True}

@app.post("/")
async def webhook_root(request: Request, x_line_signature: str = Header(None)):
    return await handle_webhook(request, x_line_signature)

@app.post("/api/webhook")
async def webhook_alias(request: Request, x_line_signature: str = Header(None)):
    return await handle_webhook(request, x_line_signature)
