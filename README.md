# Zenith — Privacy-Native Browser Agent for Zen Browser

Zenith is a **zero-cloud** browser agent system that pairs a local LLM (via [Ollama](https://ollama.com)) with [browser-use](https://github.com/browser-use/browser-use) to autonomously control [Zen Browser](https://zen-browser.app). All inference stays on your machine.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Zen Browser Extension (Vite + React + Tailwind)         │
│  ┌────────────┐  ┌────────────────────────────────────┐  │
│  │ Intent Bar │  │            Agent HUD               │  │
│  │ (Ctrl+L)   │  │  thought stream · sub-task list    │  │
│  └─────┬──────┘  └──────────────────▲─────────────────┘  │
│        │  WebSocket (ws://localhost:8765/ws)  │           │
└────────┼─────────────────────────────────────┼───────────┘
         ▼                                     │
┌──────────────────────────────────────────────┴───────────┐
│  FastAPI Backend                                         │
│  ┌────────────┐  ┌──────────┐  ┌───────────┐  ┌──────┐  │
│  │ ParseIntent├─►│ Browser  ├─►│  Self     ├─►│Summa-│  │
│  │            │  │ Action   │  │  Correct  │  │ rize │  │
│  └────────────┘  └────┬─────┘  └─────┬─────┘  └──────┘  │
│        LangGraph      │  browser-use │ loop              │
│                       ▼              ▼                    │
│              Zen Browser (Playwright/Firefox)             │
│                                                           │
│  LLM ◄──── Ollama (localhost:11434) ──── RTX 5070 GPU    │
└───────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

| Dependency | Version | Notes |
|---|---|---|
| Python | 3.11+ | |
| Node.js | 20+ | For extension dev |
| Ollama | latest | `ollama pull gemma3` or `ollama pull llama3.2:11b` |
| Zen Browser | latest | [zen-browser.app](https://zen-browser.app) |
| Docker | (optional) | For containerised backend |

### 1. Start Ollama

```bash
ollama serve
ollama pull gemma3
```

### 2. Run the Backend

**With Docker:**
```bash
docker compose up --build
```

**Without Docker:**
```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python -m playwright install firefox

uvicorn app.main:app --host 0.0.0.0 --port 8765 --reload
```

### 3. Build the Extension

```bash
cd extension
npm install
npm run build
```

Then load `extension/dist` in Zen Browser:
1. Navigate to `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on**
3. Select any file inside `extension/dist`

### 4. Use It

Press **Ctrl+L** (or **Cmd+K** on macOS) to open the Intent Bar, type a task like:

> Find the cheapest RTX 5070 on eBay, check reviews on Reddit, and summarize the best deal

The Agent HUD will stream the plan, browsing actions, and final summary in real time.

## Repository Structure

```
.
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py        # FastAPI + WebSocket server
│   │   ├── graph.py        # LangGraph StateGraph workflow
│   │   └── agent.py        # browser-use + Zen Browser config
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── extension/
│   ├── manifest.json       # Firefox v3 WebExtension manifest
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── IntentBar.tsx   # Command palette component
│   │   ├── AgentHUD.tsx    # Thought-stream sidebar
│   │   ├── useWebSocket.ts # WS hook for backend communication
│   │   ├── background.ts   # Service worker
│   │   └── index.css       # Tailwind + Zen CSS variables
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Configuration

| Env Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `gemma3` | Model name (gemma3, llama3.2:11b, etc.) |
| `ZEN_BROWSER_PATH` | (auto-detected) | Absolute path to the Zen Browser binary |

## Privacy

- **Zero cloud** — all LLM inference runs locally through Ollama.
- **No telemetry** — the extension makes no external network requests beyond localhost.
- **Zen-native** — inherits Zen Browser's distraction-free design philosophy.

## License

MIT
