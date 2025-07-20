import os
import io
import base64
import datetime
import requests
from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from github import Github
import json

# .env 読み込みはオプションに変更
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    print("⚠️ dotenv 読み込みスキップ")

# 🆕 環境変数がない場合はデフォルト値に fallback
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "your_token_here")
REPO_NAME = os.getenv("REPO_NAME", "your_username/your_repo")
BRANCH_NAME = os.getenv("BRANCH_NAME", "main")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "your_line_token")

LINE_REPLY_ENDPOINT = "https://api.line.me/v2/bot/message/reply"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
}

# GitHub連携
g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)
