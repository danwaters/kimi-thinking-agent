# 🔮 Kimi Thinking Agent

A deep market research agent powered by [Kimi K2-Thinking](https://www.moonshot.ai/) via Together AI. Watch the AI reason through complex competitive analysis in real-time.

## Features

- **Thinking Visualization**: See the model's reasoning process in collapsible panels
- **Tool Calls**: Watch as the agent gathers competitor data, financials, and news
- **Streaming**: Real-time updates as the analysis progresses
- **Beautiful UI**: Modern dark theme with syntax highlighting

## Project Structure

```
kimi-thinking-agent/
├── backend/           # FastAPI Python backend
│   ├── main.py       # API server with streaming agent
│   ├── pyproject.toml
│   └── .env          # Your TOGETHER_API_KEY goes here
├── frontend/          # React + Vite + Tailwind UI
│   ├── src/
│   └── package.json
└── README.md
```

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Create .env with your API key
echo "TOGETHER_API_KEY=your_key_here" > .env

# Install dependencies and run
uv sync
uv run main.py
```

Backend runs at http://localhost:8000

### 2. Frontend Setup

```bash
cd frontend

# Install and run
npm install
npm run dev
```

Frontend runs at http://localhost:5173

## Usage

1. Enter a company name (e.g., "Tesla", "Apple", "Netflix")
2. Click "Analyze" to start the research
3. Watch the thinking process unfold turn by turn
4. See tool calls and their results in real-time
5. Read the final comprehensive analysis

## API Endpoints

- `POST /analyze/stream` - Stream analysis with thinking tokens and tool calls

## Tech Stack

- **Backend**: FastAPI, Together AI SDK, uvicorn
- **Frontend**: React, Vite, Tailwind CSS, react-markdown
- **Model**: Kimi K2-Thinking (moonshotai/Kimi-K2-Thinking)

