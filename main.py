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
    
