"""
Zenith — FastAPI + WebSocket entry point.

Exposes:
  WS  /ws           – Real-time bidirectional channel for the Zen extension.
  GET /health       – Liveness probe for Docker / monitoring.
  GET /api/status   – Current agent state snapshot.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .agent import shutdown_browser
from .graph import AgentState, build_graph

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(name)s  %(levelname)s  %(message)s")

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Zenith backend starting…")
    yield
    logger.info("Zenith backend shutting down — closing browser…")
    await shutdown_browser()


app = FastAPI(title="Zenith Agent Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tightened in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compiled LangGraph runnable (stateless — state lives per-session)
agent_graph = build_graph()

# Simple in-memory store of the latest state per connection
_latest_state: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/status")
async def api_status():
    return _latest_state or {"status": "idle"}


# ---------------------------------------------------------------------------
# WebSocket — main communication channel with the extension
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    logger.info("Extension connected via WebSocket.")

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)

            msg_type = msg.get("type")
            if msg_type == "intent":
                intent_text = msg.get("payload", "")
                logger.info("Received intent: %s", intent_text)
                # Run the graph in a background task so the WS stays responsive
                asyncio.create_task(_run_graph(ws, intent_text))
            elif msg_type == "cancel":
                logger.info("Cancel requested (not yet implemented).")
                await ws.send_text(json.dumps({"type": "cancelled"}))
            elif msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
            else:
                await ws.send_text(json.dumps({"type": "error", "payload": f"Unknown message type: {msg_type}"}))
    except WebSocketDisconnect:
        logger.info("Extension disconnected.")
    except Exception:
        logger.exception("WebSocket error")


async def _run_graph(ws: WebSocket, intent: str) -> None:
    """Stream the LangGraph execution over the WebSocket."""
    global _latest_state

    initial_state: dict[str, Any] = AgentState(intent=intent).model_dump()

    try:
        # LangGraph's astream yields after each node execution
        async for step in agent_graph.astream(initial_state):
            # `step` is a dict keyed by node name → output state dict
            for node_name, node_output in step.items():
                state = AgentState(**node_output) if isinstance(node_output, dict) else None
                if state is None:
                    continue

                _latest_state = state.model_dump()

                payload = {
                    "type": "state_update",
                    "node": node_name,
                    "thought": state.thought,
                    "node_status": state.node_status,
                    "current_task_index": state.current_task_index,
                    "total_tasks": len(state.sub_tasks),
                    "sub_tasks": [
                        {"id": t.id, "desc": t.description, "status": t.status.value}
                        for t in state.sub_tasks
                    ],
                }
                await ws.send_text(json.dumps(payload))

        # Final summary
        final = AgentState(**_latest_state)
        await ws.send_text(json.dumps({
            "type": "result",
            "summary": final.summary,
        }))
    except Exception as exc:
        logger.exception("Graph execution failed")
        await ws.send_text(json.dumps({
            "type": "error",
            "payload": str(exc),
        }))


# ---------------------------------------------------------------------------
# Dev entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8765, reload=True)
