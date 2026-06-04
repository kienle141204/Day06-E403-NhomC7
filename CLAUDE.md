# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MedChat** — a healthcare chatbot prototype (hackathon submission) that helps patients understand prescriptions. Users upload a prescription image, the system extracts medications via OCR, the user confirms/edits the drug list, then asks questions in a Q&A chat. The backend is not implemented; the frontend runs entirely against a mock API.

## Commands

All commands run from `codebase/frontend/`:

```bash
npm install       # Install dependencies
npm run dev       # Start Vite dev server (http://localhost:5173)
npm run build     # Production build → dist/
npm run preview   # Preview production build locally
```

## Architecture

### Frontend (`codebase/frontend/src/`)

- **`App.jsx`** — Single large component (~970 lines) containing all UI and state. All child components (`Sidebar`, `ChatWindow`, `MessageBubble`, `Composer`, `PrescriptionPanel`, etc.) are defined in this file.
- **`api/client.js`** — API adapter that checks for `VITE_API_BASE_URL`. If the env var is set, routes calls to the real backend; otherwise falls back to `mockApi`. Exposes: `scanPrescription`, `confirmPrescription`, `sendMessage`, `createReminders`, `getSpecialists`, `createAppointment`.
- **`data/mockApi.js`** — Full mock implementation with simulated delays (400–900 ms). Includes sample data: three medications (Metformin, Atorvastatin, Prednisolone) with per-drug confidence scores.

### State Management

Pure React hooks (`useState`, `useMemo`) in `App.jsx`. No external state library. All state lives at the root; child components receive props and callbacks.

### Backend (`codebase/backend/`)

Placeholder only (`.gitkeep`). The intended API surface is:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/prescriptions/scan` | OCR extraction |
| POST | `/prescriptions/{id}/confirm` | Mark as user-reviewed |
| PATCH | `/prescriptions/{id}/medications/{id}` | Edit drug name/dose |
| POST | `/chat` | LLM Q&A |
| POST | `/reminders/bulk` | Medication reminders |
| GET | `/specialists` | Find pharmacists/doctors |
| POST | `/appointments` | Book appointment |

## Key Design Principles

**Safety-first workflow:** The AI does not explain any drug until the user explicitly confirms the extracted drug names. This prevents misdiagnosis from OCR errors.

**Per-drug confidence scores** (not aggregate): Each medication has its own confidence threshold (≥80% = auto-confirmed, <80% = user must review).

**API abstraction:** Setting `VITE_API_BASE_URL` in `.env` switches the entire app from demo mode to a live backend with no code changes.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `VITE_API_BASE_URL` | Backend base URL (e.g., `http://localhost:3000`). If unset, mock API is used. |

## UI Language

All UI text is in Vietnamese. The font is **Be Vietnam Pro** (loaded from Google Fonts in `index.html`). Color coding for risk: green = normal, amber = warning, red = high-risk.

## Reference Docs

- `workflow.md` — Detailed step-by-step workflow the app enforces
- `codebase/README.md` — Run and deploy instructions
- `spec/README.md` — SPEC format requirements for hackathon submission
