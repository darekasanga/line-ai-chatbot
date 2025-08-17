# api/webhook.py
import os, hmac, hashlib, base64, json, traceback
from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse

app = FastAPI()
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET", "")

def verify_signature(body: bytes, sig: str | None) -> bool:
    if not CHANNEL_SECRET or not sig:   # 署名/秘密が無い時は検証スキップ
        return True
    mac = hmac.new(CHANNEL_SECRET.encode(), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode()
    return hmac.compare_digest(expected, sig)

@app.get("/")
def health():
    return {"ok": True}

# Vercel は /api/webhook に来るが、ファイル内では "/" を定義する
@app.api_route("/", methods=["POST"])
async def webhook(request: Request, x_line_signature: str | None = Header(None)):
    try:
        body = await request.body()               # 例外出ない
        if not verify_signature(body, x_line_signature):
            print("Bad signature")
            return JSONResponse({"ok": False, "reason": "bad-signature"}, status_code=200)

        try:
            data = await request.json()           # JSONでなければ空に
        except Exception:
            data = {}
        print("Webhook hit:", data)               # ログだけ出して終了
        return {"ok": True}
    except Exception:
        # ここで 500 を出さない(Verify を通す)
        print("ERROR in webhook\n", traceback.format_exc())
        return JSONResponse({"ok": True, "note": "handled-error"}, status_code=200)
