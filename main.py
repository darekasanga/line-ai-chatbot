from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import os
import requests
import base64

app = FastAPI()

# 環境変数
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = "darekasanga/line-ai-chatbot"
GITHUB_BRANCH = "main"
UPLOAD_PATH = "uploaded_files"  # 画像ファイルを保存するGitHub内のフォルダ

# 画像一覧を取得する関数
def get_uploaded_image_urls():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{UPLOAD_PATH}?ref={GITHUB_BRANCH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return []

    files = res.json()
    image_urls = []
    for f in files:
        if f["name"].lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
            image_urls.append(f["download_url"])
    return image_urls

# 画像一覧ページ
@app.get("/list", response_class=HTMLResponse)
def list_images():
    urls = get_uploaded_image_urls()
    html = "<h1>📸 画像一覧</h1><div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1em;'>"
    for url in urls:
        name = url.split("/")[-1]
        html += f"""
        <div>
            <img src='{url}' width='200'/><br/>
            <form action="/delete" method="post">
                <input type="hidden" name="filename" value="{name}"/>
                <button type="submit">❌ 削除</button>
            </form>
            <p>{name}</p>
        </div>
        """
    html += "</div>"
    return html

# 削除処理
@app.post("/delete")
def delete_file(filename: str = Form(...)):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{UPLOAD_PATH}/{filename}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return HTMLResponse(content="ファイルが見つかりませんでした", status_code=404)

    sha = res.json().get("sha")
    data = {
        "message": f"Delete {filename}",
        "sha": sha,
        "branch": GITHUB_BRANCH
    }

    delete_res = requests.delete(url, headers=headers, json=data)
    if delete_res.status_code in [200, 204]:
        return RedirectResponse(url="/list", status_code=303)
    else:
        return HTMLResponse(content="削除に失敗しました", status_code=500)

# 動作確認ページ
@app.get("/")
def root():
    return {"message": "GitHub画像一覧＆削除サーバー"}
