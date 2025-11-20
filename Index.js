const express = require("express");
const axios = require("axios");
const bodyParser = require("body-parser");

const app = express();
app.use(bodyParser.json());

// === CONFIG ===
const VERIFY_TOKEN = "miverificacion"; // ESTE es el token para META
const WHATSAPP_TOKEN = process.env.EAAQDANGmCF8BP0Y4WMAZA9z55DMtMfCZAI9GREQUtvSxprwvYtIm9zRoJfZA9X4VNYZByIKfYv5ZA8FZCpPs9uAfA2JErcVKMVtlAsXwSljb2vy2G4ms2HknnLRMAw3WG6QkMtkTX2EeMHIyhUvY9qupB7LnK9ZBXUrAY5cV1EqCgGco9ERwjht1ioNlUgPnwSUpCqib9G9b96jaKwJiciwPyOrjSwWyrZCZA25XghgkZAO8Yzx2Pm50Dyxfw34xjXK3fOm1NGEL6UiRSO6DrWEzQ9RAQx;
const PHONE_NUMBER_ID = process.env.813230988549762;
const GEMINI_API_KEY = process.env.AIzaSyDEQBd0OiMq9VqFeIbY3_-kSWLt-DEug7w;

// RESPONDER A META PARA VERIFICAR WEBHOOK
app.get("/webhook", (req, res) => {
    const mode = req.query["hub.mode"];
    const challenge = req.query["hub.challenge"];
    const token = req.query["hub.verify_token"];

    if (mode === "subscribe" && token === VERIFY_TOKEN) {
        console.log("WEBHOOK VERIFICADO");
        res.status(200).send(challenge);
    } else {
        res.sendStatus(403);
    }
});

// === WHATSAPP ENVÍA MENSAJES AQUÍ ===
app.post("/webhook", async (req, res) => {
    try {
        const data = req.body;

        if (data.entry &&
            data.entry[0].changes &&
            data.entry[0].changes[0].value.messages) {

            const message = data.entry[0].changes[0].value.messages[0];
            const from = message.from;
            const text = message.text?.body;

            if (!text) return res.sendStatus(200);

            // Comandos
            if (text.startsWith("img ")) {
                const prompt = text.slice(4);
                const url = await generateImage(prompt);
                await sendImage(from, url);
            } else {
                const reply = await generateText(text);
                await sendText(from, reply);
            }
        }

        res.sendStatus(200);
    } catch (e) {
        console.log("ERROR:", e);
        res.sendStatus(500);
    }
});

// === ENVIAR TEXTO ===
async function sendText(to, message) {
    await axios.post(
        `https://graph.facebook.com/v19.0/${PHONE_NUMBER_ID}/messages`,
        {
            messaging_product: "whatsapp",
            to,
            text: { body: message }
        },
        { headers: { Authorization: `Bearer ${WHATSAPP_TOKEN}` } }
    );
}

// === ENVIAR IMAGEN ===
async function sendImage(to, url) {
    await axios.post(
        `https://graph.facebook.com/v19.0/${PHONE_NUMBER_ID}/messages`,
        {
            messaging_product: "whatsapp",
            to,
            type: "image",
            image: { link: url }
        },
        { headers: { Authorization: `Bearer ${WHATSAPP_TOKEN}` } }
    );
}

// === GEMINI TEXTO ===
async function generateText(prompt) {
    const response = await axios.post(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=${GEMINI_API_KEY}`,
        { contents: [{ parts: [{ text: prompt }] }] }
    );

    return response.data.candidates[0].content.parts[0].text;
}

// === GEMINI IMAGEN ===
async function generateImage(prompt) {
    const response = await axios.post(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateImage?key=${GEMINI_API_KEY}`,
        { prompt: { text: prompt } }
    );

    return response.data.generatedImages[0].url;
}

// SERVIDOR
app.listen(3000, () => console.log("BOT WHATSAPP + GEMINI LISTO 🔥"));￼Enter
