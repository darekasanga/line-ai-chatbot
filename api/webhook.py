# --- api/webhook.py ---
import os, hmac, hashlib, base64
from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse

app = FastAPI()

CHANNEL_SECRET = os.getenv("CHANNEL_SECRET", "")

def verify_signature(body: bytes, sig: str | None) -> bool:
    if not CHANNEL_SECRET or not sig:   # 環境変数やヘッダが無い時は検証しない
        return True
    mac = hmac.new(CHANNEL_SECRET.encode(), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(mac).decode(), sig)

@app.get("/")
def health():
    return {"ok": True}

# Vercel の /api/webhook に対しては、ここで "/" を定義する
@app.api_route("/", methods=["POST"])
async def webhook(request: Request, x_line_signature: str | None = Header(None)):
    body = await request.body()
    # 署名検証(無ければスキップ)
    if not verify_signature(body, x_line_signature):
        # 署名不一致でも 200 を返して Verify 落ちを防ぎたいなら True にする
        return JSONResponse({"ok": False, "reason": "bad signature"}, status_code=200)

    # JSON でない/空でも落ちないようにする
    try:
        data = await request.json()
    except Exception:
        data = {}

    # ここで実際の処理をする。今はログだけ出して 200 を返す
    print("LINE webhook hit:", data)
    return {"ok": True}
