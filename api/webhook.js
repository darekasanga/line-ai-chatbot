import { middleware, Client } from "@line/bot-sdk";

const config = {
  channelAccessToken: process.env.CHANNEL_ACCESS_TOKEN,
  channelSecret: process.env.CHANNEL_SECRET,
};

const client = new Client(config);

export default async function handler(req, res) {
  if (req.method === "POST") {
    try {
      const events = req.body.events;
      for (const event of events) {
        if (event.type === "message" && event.message.type === "text") {
          await client.replyMessage(event.replyToken, {
            type: "text",
            text: `Echo: ${event.message.text}`,
          });
        }
      }
      res.status(200).send("OK");
    } catch (err) {
      console.error(err);
      res.status(500).send("Error");
    }
  } else {
    res.status(405).send("Method Not Allowed");
  }
}
