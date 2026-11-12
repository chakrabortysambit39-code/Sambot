# TITAN AI upgrade

This branch adds a bounded agent workflow and private account-scoped memory to Sambot X while preserving existing chat, voice, file, image-generation, and image-understanding features.

## New capabilities

- **Agent mode** (`POST /api/agent/run`): Groq tool-calling loop with a strict four-round limit. The agent can use public web search and a safe arithmetic calculator. It cannot run shell commands, execute arbitrary code, access private files, or make purchases.
- **Private long-term memory** (`/api/memory`): explicitly saved facts are stored in SQLite under the signed-in email identity. Memory is not silently inferred or saved from conversations. The user can list, add, and delete individual memories. Chat uses saved facts only when a valid account token is supplied.
- **Image understanding in the composer**: image attachments are sent to the existing Groq Vision endpoint and the analysis is included with the user's question.
- **Image generation**: the existing Cloudflare FLUX.1 Schnell path remains available, with prompt validation, clearer provider errors, and a download action.
- **Quality checks**: a GitHub Actions workflow compiles Python files and runs unit tests on pushes and pull requests.

## Setup

Keep the existing Render environment variables and persistent disk configuration. Private memory shares the existing `BILLING_DB_PATH` SQLite database, so the `/var/data` persistent disk must remain mounted. To use private synced memory, configure the existing email sign-in settings (`BILLING_SESSION_SECRET`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, and `SMTP_FROM`) and sign in from Sambot's Premium panel. A paid subscription is not required merely to authenticate.

Existing AI provider settings:
- `GROQ_API_KEY` for chat, agent mode, and image understanding.
- `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` for image generation.

## Test

```bash
pip install -r requirements-render.txt
python -m compileall -q .
python -m unittest discover -s tests -v
```

## Important current limitations

- Conversation history and chat titles still live in browser local storage. Private saved memories sync by account; chat transcripts do not yet sync between devices.
- Voice input and speech output use browser speech APIs and depend on browser support and microphone permission.
- Agent tools are intentionally limited to web search and arithmetic. There is no arbitrary Python/shell execution.
- The public web-search implementation is best-effort HTML search, not a guaranteed search API. Results must be checked.
- Provider credentials are required; a code change cannot create or supply those secrets.
- This branch has not been validated against live Groq/Cloudflare credentials. Review CI and test on a preview deployment before merging.