export default async function handler(req, res) {
  // Verifyボタンや疎通確認用
  if (req.method === "GET") {
    return res.status(200).json({ ok: true, runtime: "node" });
  }

  // LINEプラットフォームからのPOST本体
  if (req.method === "POST") {
    try {
      // ここで必要ならログを見る
      // console.log("headers:", req.headers);
      // console.log("body:", req.body);

      // まだ署名検証や返信はせず、まず200を返す
      return res.status(200).json({ ok: true });
    } catch (e) {
      console.error(e);
      return res.status(200).json({ ok: true }); // リトライ地獄回避のため200
    }
  }

  // それ以外
  return res.status(405).json({ ok: false, message: "Method Not Allowed" });
}
