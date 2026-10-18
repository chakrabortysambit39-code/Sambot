# Deploy the SAMBOT X web app on Render

This repository contains both a desktop assistant and a browser-based app. For Render, deploy the browser app in `web_app.py` (FastAPI), not the desktop entry point `app.py`.

## Render settings

- **Service type:** Web Service
- **Runtime:** Python
- **Build command:** `pip install -r requirements-render.txt`
- **Start command:** `uvicorn sambot_server:app --host 0.0.0.0 --port $PORT`
- **Health check path:** `/health`

The checked-in `render.yaml` contains these web-service settings, so you can also use Render's Blueprint flow to create the service from the repository.

## Environment variables

Add these in the Render service's Environment settings:

- `GROQ_API_KEY` — required for AI chat. Create the key in your Groq account and keep it private; never paste it into source code or commit it to GitHub.
- `GROQ_MODEL` — optional; the repository currently defaults to `openai/gpt-oss-120b`.
- `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` — optional; required only for the image-generation endpoint.

The current web interface stores chat history and its simple memory in the browser's `localStorage`, so history is per-browser and does not automatically sync across devices. Do not store passwords, API keys, or other secrets in that local memory.

## Verify the deployment

1. Wait for the Render build and deploy to finish.
2. Open `https://YOUR-RENDER-SERVICE.onrender.com/health`.
3. Check that the response contains `\"ok\": true` and `\"groq_configured\": true`.
4. Open the service root URL and send a test message.

If chat returns an API error, open Render's logs and verify the key, the selected model, and the HTTP status returned by Groq. The repository's current file upload endpoint supports extracting text from TXT, Markdown, CSV, JSON, Python, JavaScript, HTML, CSS, PDF, DOCX, and XLSX files; it does not perform OCR on scanned images or PDFs.

## Current browser features

The Render entry point `sambot_server.py` adds the model picker, image understanding, and streaming chat API on top of `web_app.py`. The browser app supports streaming replies with a Stop button, local chat history, chat import/export, Markdown/code formatting, custom instructions, local memory, file uploads, web search, browser speech input, read-aloud, and optional Cloudflare image generation. Chat history and preferences remain in that browser unless exported; this setup does not include user accounts or cross-device sync.

## Voice mode

The browser UI includes hands-free voice mode using the browser's Web Speech APIs. Use a current desktop Chrome/Edge browser, allow microphone access, and keep the tab open. Voice mode listens for a spoken turn, sends it to the configured Groq model, reads the answer aloud, and resumes listening. The browser's speech recognition and speech synthesis are browser-provided services, not OpenAI real-time voice infrastructure; support and language availability vary by browser. Click **Stop voice** to stop listening and speech. Voice audio is processed by the browser's speech service and chat text is sent to Sambot's configured AI provider.
