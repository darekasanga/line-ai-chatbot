# main.py complete version
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello from FastAPI on Vercel!"}

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    print("Received webhook:", data)
    return JSONResponse(content={"status": "ok"})
