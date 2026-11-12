# Sambot X — TITAN AI

Sambot X is a browser-based AI workspace powered by Groq and Cloudflare AI. The repository also contains an older desktop assistant codebase; the deployed Render app is the Sambot X web application.

## What it can do

- Streaming AI chat with selectable Groq models
- Image generation with Cloudflare FLUX.1 Schnell
- Image understanding through Groq Vision, including uploaded and pasted images
- Voice input, hands-free browser voice mode, and read-aloud
- File uploads for text, PDF, DOCX, and spreadsheets
- CSV statistics and safe arithmetic
- Best-effort public web search
- Agent mode with bounded tool calling for web search and arithmetic
- Explicitly saved, private, account-scoped long-term memory
- Browser-local chat history, export/import, and workspace utilities

See [TITAN_AI.md](TITAN_AI.md) for the new agent and memory architecture, environment setup, tests, and current limitations.

## Local development

```bash
pip install -r requirements-render.txt
set GROQ_API_KEY=your_groq_key
uvicorn sambot_server:app --reload
```

On PowerShell, set the key for the current terminal with:

```powershell
$env:GROQ_API_KEY = "your_groq_key"
uvicorn sambot_server:app --reload
```

Add `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` to enable image generation. Email sign-in and private synced memory require `BILLING_SESSION_SECRET`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, and `SMTP_FROM`. Keep secrets in environment variables; never commit API keys.

## Run checks

```bash
python -m compileall -q .
python -m unittest discover -s tests -v
```

## Deployment

Render uses `render.yaml`. The persistent disk mounted at `/var/data` stores the SQLite billing and private-memory database. Configure the required environment variables in the Render dashboard before testing optional services.

## Security and limitations

- Agent mode is intentionally restricted to web search and arithmetic. It does not execute shell commands or arbitrary code.
- Saved memory is opt-in, account-scoped, and deletable. Chat transcripts remain in browser local storage and do not sync between devices yet.
- Voice capabilities depend on browser support and microphone permissions.
- Web search is best-effort and sources should be checked.
- A successful deployment requires valid provider credentials; this repository does not contain or generate secrets.
- Test a preview deployment with real provider credentials before merging changes to the production branch.