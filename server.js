// ✅ server.js（最新版） - LINE画像受信 → Sharpで縮小 → GitHubアップロード対応

import express from 'express';
import crypto from 'crypto';
import fetch from 'node-fetch';
import sharp from 'sharp';
import fs from 'fs';
import path from 'path';
import dotenv from 'dotenv';
dotenv.config();

const app = express();
const port = 3000;

app.use(express.raw({ type: '*/*' })); // LINE signature検証のため raw body を取得

const LINE_CHANNEL_SECRET = process.env.LINE_CHANNEL_SECRET;
const LINE_ACCESS_TOKEN = process.env.LINE_CHANNEL_ACCESS_TOKEN;
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const GITHUB_REPO = 'darekasanga/line-secure-upload'; // GitHubリポジトリ
const BRANCH = 'main';

// Webhook受信処理
app.post('/webhook', async (req, res) => {
  const signature = req.headers['x-line-signature'];
  const body = req.body.toString();

  // ✅ LINE署名チェック
  const hash = crypto.createHmac('sha256', LINE_CHANNEL_SECRET)
    .update(body).digest('base64');
  if (hash !== signature) {
    console.log('❌ 不正な署名');
    return res.status(403).send('Invalid signature');
  }

  const event = JSON.parse(body).events?.[0];
  if (!event || event.message?.type !== 'image') return res.send('Ignored');

  const messageId = event.message.id;
  const userId = event.source.userId;

  try {
    // ① LINEから画像取得
    const imageRes = await fetch(`https://api-data.line.me/v2/bot/message/${messageId}/content`, {
      headers: { 'Authorization': `Bearer ${LINE_ACCESS_TOKEN}` }
    });
    const rawBuffer = Buffer.from(await imageRes.arrayBuffer());

    // ② Sharpでサイズ縮小＋JPEG圧縮
    const buffer = await sharp(rawBuffer)
      .resize({ width: 1200 })
      .jpeg({ quality: 80 })
      .toBuffer();

    // ③ ファイル名生成（UUID＋拡張子）
    const filename = `${crypto.randomUUID()}.jpg`;
    const savePath = path.join('uploads', filename);
    fs.mkdirSync('uploads', { recursive: true });
    fs.writeFileSync(savePath, buffer);

    // ④ GitHubへアップロード
    const content = buffer.toString('base64');
    const uploadRes = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/contents/uploads/${filename}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${GITHUB_TOKEN}`,
        'Accept': 'application/vnd.github+json'
      },
      body: JSON.stringify({
        message: `Upload from ${userId}`,
        content,
        branch: BRANCH
      })
    });

    if (!uploadRes.ok) {
      console.log(await uploadRes.text());
      return res.status(500).send('GitHub upload failed');
    }

    // ⑤ LINEへ返信
    const url = `https://raw.githubusercontent.com/${GITHUB_REPO}/${BRANCH}/uploads/${filename}`;
    await fetch('https://api.line.me/v2/bot/message/reply', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${LINE_ACCESS_TOKEN}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        replyToken: event.replyToken,
        messages: [{ type: 'text', text: `✅ アップロード完了：\n${url}` }]
      })
    });

    res.send('OK');
  } catch (err) {
    console.error(err);
    res.status(500).send('Error');
  }
});

app.listen(port, () => {
  console.log(`✅ Server running at http://localhost:${port}`);
});
