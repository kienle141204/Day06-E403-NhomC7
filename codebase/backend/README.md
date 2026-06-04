# MedChat Backend

FastAPI backend for the MedChat prototype. It serves mock prescriptions and uses the OpenAI API for medication-only chat.

## Setup

```bash
cd codebase/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Set `OPENAI_API_KEY` in `.env`, then run:

```bash
uvicorn app.main:app --reload --port 8000
```

Connect the frontend with:

```bash
set VITE_API_BASE_URL=http://localhost:8000
npm run dev
```
