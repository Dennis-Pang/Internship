# Voice Chatbot Dashboard Frontend

A modern web interface for visualizing real-time emotion analysis and personality insights from the voice chatbot.

## Features

- **Real-time Updates**: Server-Sent Events (SSE) for live data streaming
- **Emotion Visualization**: Dual radar charts for speech and text emotion analysis
- **Personality Insights**: Big5 personality trait visualization
- **Memory Viewer**: Browse user profiles and conversation events from MemoBase
- **Beautiful UI**: Glassmorphism design with smooth animations

## Tech Stack

- **Frontend**: React 18 + TypeScript + Vite
- **UI**: Tailwind CSS with custom glassmorphism effects
- **Charts**: Recharts for radar visualizations
- **Backend**: Flask API with SSE support
- **State**: React hooks for local state management

## Installation

```bash
cd frontend
npm install
```

## Running the Application

### Option 1: Start All Components (Recommended)

From the project root:
```bash
./start_all.sh
```

This launches:
- Backend API (port 5000)
- Frontend Dashboard (port 3000)
- Chatbot (interactive mode)

### Option 2: Start Components Individually

**1. Start the Backend API**

```bash
cd chatbot
./start_backend.sh
```

The API will start on `http://localhost:5000`

**2. Start the Frontend Dev Server**

```bash
cd frontend
npm run dev
```

The dashboard will open at `http://localhost:3000`

**3. Run the Chatbot** (optional for real-time updates)

In a separate terminal:

```bash
cd chatbot
python main.py
```

## API Endpoints

### REST Endpoints

- `GET /api/dashboard/<user_id>` - Get current dashboard data
- `GET /api/memories/<user_id>` - Get user memories (profiles + events)
- `GET /health` - Health check

### Streaming Endpoint

- `GET /api/stream/<user_id>` - SSE stream for real-time updates

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Dashboard.tsx           # Main dashboard container
│   │   ├── RadarChart.tsx          # Emotion/personality radar chart
│   │   ├── TranscriptionDisplay.tsx # User input display
│   │   └── MemoryViewer.tsx        # Memory browser (profiles/events)
│   ├── api/
│   │   └── client.ts               # API client and SSE subscription
│   ├── types/
│   │   └── index.ts                # TypeScript type definitions
│   ├── styles/
│   │   └── index.css               # Global styles + Tailwind
│   ├── App.tsx                     # Root component
│   └── main.tsx                    # Entry point
├── package.json                    # NPM dependencies
├── vite.config.ts                  # Vite configuration
└── tailwind.config.js              # Tailwind configuration

../chatbot/
└── backend_api.py                  # Flask backend server (separate process)
```

## Data Flow

1. User speaks → Chatbot processes input
2. Chatbot updates `memory_cache.json` with:
   - Transcribed text
   - Speech emotion probabilities
   - Text emotion probabilities
   - Updated Big5 traits (stored in SQLite)
3. Backend API detects file change
4. SSE stream pushes update to frontend
5. Dashboard UI updates in real-time

## Configuration

Create a `.env` file in the frontend directory:

```env
VITE_API_URL=http://localhost:5000/api
```

## Features in Detail

### Radar Charts

Three synchronized radar charts display:
- **Speech Emotion**: 7 dimensions (anger, disgust, fear, happy, neutral, sad, surprise)
- **Text Emotion**: 7 dimensions (same as speech)
- **Big5 Personality**: 5 dimensions (Extroversion, Neuroticism, Agreeableness, Conscientiousness, Openness)

### Memory Viewer

- **Profiles Tab**: Grouped by topic, expandable/collapsible
- **Events Tab**: Chronological list with tags and tips
- **Real-time Sync**: Updates when chatbot creates new memories

### Transcription Display

Shows the latest user input with timestamp, refreshes on new conversation turns.

## Development

### Build for Production

```bash
npm run build
```

Built files will be in `dist/`

### Preview Production Build

```bash
npm run preview
```

## Integration with Chatbot

The dashboard automatically connects to:
- `../chatbot/memory_cache.json` for conversation data
- `../chatbot/memories.sqlite` for Big5 personality traits
- MemoBase API (via chatbot modules) for user memories

Ensure the chatbot is running and properly configured with MemoBase before starting the dashboard.

## Troubleshooting

### Backend API not responding

Check if the backend is running:

```bash
curl http://localhost:5000/health
```

If not, start it:

```bash
cd chatbot
./start_backend.sh
```

### SSE connection fails

Check CORS settings in `backend_api.py` and ensure the API URL in `.env` matches the backend server.

### Charts not displaying

Verify that emotion data in `memory_cache.json` is properly formatted as JSON strings.

## Future Enhancements

- User authentication and multi-user support
- Historical data visualization (time-series charts)
- Export conversation transcripts
- Custom emotion/personality model selection
- Dark/light theme toggle
