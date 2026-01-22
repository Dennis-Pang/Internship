# Voice Chatbot Dashboard

React + Vite UI for live emotion/personality telemetry and memory management.

## Features
- Live updates via SSE (`/api/stream/{userId}`) with REST snapshot fallback (`/api/dashboard/{userId}`).
- Dual emotion radar (speech/text), Big Five traits, streaming transcription, memory profiles/events.
- `VITE_API_URL` overrides the backend base URL (defaults to `/api`, proxied to `http://localhost:5000/api`).

## Quick Start
```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

## Key Files
- `src/App.tsx` – layout and data wiring.
- `src/components/` – `Dashboard`, `DualRadarChart`, `RadarChart`, `MemoryViewer`, `TranscriptionDisplay`.
- `src/api/client.ts` – REST client + SSE subscription helper.
