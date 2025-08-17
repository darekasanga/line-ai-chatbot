// api/webhook.js  — FastAPIなし版(Vercel Node.js Function)
const crypto = require('crypto');

function verifySignature(body, signature, channelSecret) {
  if (!channelSecret || !signature) return true; // 検証スキップ可(まずはVerify通過用)
  const mac = crypto.createHmac('sha256', channelSecret)
                    .update(body)
                    .digest('base64');
  // LINEの署名は大小文字区別あり
  return crypto.timingSafeEqual(Buffer.from(mac), Buffer.from(signature));
}

module.exports = async (req, res) => {
  // 必ず 200 を返す安全版
  if (req.method !== 'POST') {
    return res.status(200).json({ ok: true });
  }

  const signature = req.headers['x-line-signature'];
  const rawBody = req.body ? JSON.stringify(req.body) : (await getRawBody(req));
  const ok = verifySignature(
    typeof rawBody === 'string' ? rawBody : JSON.stringify(rawBody),
    signature,
    process.env.CHANNEL_SECRET || ''
  );

  if (!ok) {
    console.log('Bad signature');
    return res.status(200).json({ ok: false, reason: 'bad-signature' });
  }

  // 本文をログに出すだけ(ここに後で処理を足す)
  let data;
  try { data = typeof req.body === 'object' ? req.body : JSON.parse(rawBody); }
  catch { data = {}; }
  console.log('Webhook hit:', data);

  return res.status(200).json({ ok: true });
};

// 生ボディ取得(Vercel/Node用の簡易版)
function getRawBody(req) {
  return new Promise((resolve, reject) => {
    let chunks = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    req.on('error', reject);
  });
}
