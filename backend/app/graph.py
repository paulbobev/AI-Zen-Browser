"""
Zenith — LangGraph StateGraph agent workflow.

Nodes:
  1. ParseIntent   – Decompose natural-language intent into a plan of sub-tasks.
  2. BrowserAction  – Execute the next browser sub-task via browser-use.
  3. SelfCorrect    – Validate the result; retry or adjust the plan on failure.
  4. Summarize      – Aggregate findings into a concise final answer.

The graph loops BrowserAction → SelfCorrect until all sub-tasks are done,
then transitions to Summarize.
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from .agent import execute_browser_task

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class SubTask(BaseModel):
    id: int
    description: str
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None
    retries: int = 0


class AgentState(BaseModel):
    """Shared state that flows through every node in the graph."""

    intent: str = ""
    sub_tasks: list[SubTask] = Field(default_factory=list)
    current_task_index: int = 0
    findings: list[str] = Field(default_factory=list)
    summary: str = ""
    error: str | None = None
    max_retries: int = 3

    # Streaming metadata pushed over the WebSocket
    node_status: str = ""
    thought: str = ""


# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------

def _get_llm(temperature: float = 0.2) -> ChatOllama:
    """Return a ChatOllama instance pointing at the local Ollama server.

    Model preference order:
      1. gemma3        – great tool-following, fits 12 GB VRAM on RTX 5070
      2. llama3.2:11b  – solid alternative
    """
    return ChatOllama(
        model="gemma3",
        base_url="http://localhost:11434",
        temperature=temperature,
        num_gpu=99,  # offload all layers to GPU
    )


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------

PLAN_SYSTEM_PROMPT = """\
You are a browsing-task planner. Given the user's intent, decompose it into
a minimal ordered list of concrete browser sub-tasks.

Respond ONLY with a JSON array of strings — each string is one sub-task.
Example: ["Search eBay for RTX 5070", "Open the cheapest listing", ...]
"""


async def parse_intent(state: dict[str, Any]) -> dict[str, Any]:
    """Decompose the raw intent into an ordered list of sub-tasks."""
    s = AgentState(**state)
    s.node_status = "parse_intent"
    s.thought = "Breaking the request into sub-tasks…"

    llm = _get_llm(temperature=0.1)
    response = await llm.ainvoke([
        SystemMessage(content=PLAN_SYSTEM_PROMPT),
        HumanMessage(content=s.intent),
    ])

    try:
        tasks_raw: list[str] = json.loads(response.content)
    except json.JSONDecodeError:
        # Fallback: treat the whole intent as a single task
        tasks_raw = [s.intent]

    s.sub_tasks = [
        SubTask(id=i, description=desc)
        for i, desc in enumerate(tasks_raw)
    ]
    s.current_task_index = 0
    s.thought = f"Plan ready — {len(s.sub_tasks)} sub-task(s)."
    return s.model_dump()


async def browser_action(state: dict[str, Any]) -> dict[str, Any]:
    """Run the current sub-task through browser-use."""
    s = AgentState(**state)
    s.node_status = "browser_action"

    task = s.sub_tasks[s.current_task_index]
    task.status = TaskStatus.RUNNING
    s.thought = f"Executing: {task.description}"

    try:
        result = await execute_browser_task(task.description)
        task.result = result
        task.status = TaskStatus.DONE
        s.findings.append(result)
        s.thought = f"Sub-task {task.id} completed."
    except Exception as exc:
        task.status = TaskStatus.FAILED
        s.error = str(exc)
        s.thought = f"Sub-task {task.id} failed: {exc}"
        logger.exception("browser_action failed for sub-task %s", task.id)

    s.sub_tasks[s.current_task_index] = task
    return s.model_dump()


CORRECT_SYSTEM_PROMPT = """\
You are a quality-assurance reviewer for a browser automation agent.
Given the sub-task description and its result (or error), decide:
  - "ok"    → the result is satisfactory, move on.
  - "retry" → the result is wrong or empty, retry the sub-task.
  - "adjust" → the sub-task description needs rewording; provide the new description.

Respond with a JSON object: {"verdict": "ok"|"retry"|"adjust", "new_description": "..."}
"""


async def self_correct(state: dict[str, Any]) -> dict[str, Any]:
    """Validate the latest browser result; decide to proceed, retry, or adjust."""
    s = AgentState(**state)
    s.node_status = "self_correct"

    task = s.sub_tasks[s.current_task_index]

    # If task succeeded, ask the LLM to verify quality
    if task.status == TaskStatus.DONE:
        llm = _get_llm()
        verification_msg = (
            f"Sub-task: {task.description}\nResult: {task.result}"
        )
        response = await llm.ainvoke([
            SystemMessage(content=CORRECT_SYSTEM_PROMPT),
            HumanMessage(content=verification_msg),
        ])
        try:
            verdict = json.loads(response.content)
        except json.JSONDecodeError:
            verdict = {"verdict": "ok"}

        if verdict.get("verdict") == "retry" and task.retries < s.max_retries:
            task.status = TaskStatus.PENDING
            task.retries += 1
            s.thought = f"Retrying sub-task {task.id} (attempt {task.retries})…"
        elif verdict.get("verdict") == "adjust" and task.retries < s.max_retries:
            task.description = verdict.get("new_description", task.description)
            task.status = TaskStatus.PENDING
            task.retries += 1
            s.thought = f"Adjusted sub-task {task.id}: {task.description}"
        else:
            s.thought = f"Sub-task {task.id} verified."
    elif task.status == TaskStatus.FAILED:
        if task.retries < s.max_retries:
            task.status = TaskStatus.PENDING
            task.retries += 1
            s.thought = f"Retrying failed sub-task {task.id} (attempt {task.retries})…"
        else:
            s.thought = f"Sub-task {task.id} exhausted retries. Skipping."
            task.status = TaskStatus.DONE
            task.result = task.result or "[no result — max retries exceeded]"

    s.sub_tasks[s.current_task_index] = task
    return s.model_dump()


SUMMARIZE_SYSTEM_PROMPT = """\
You are a helpful research assistant. Given the collected findings from
several browsing sub-tasks, produce a clear, concise summary that directly
answers the user's original intent.
"""


async def summarize(state: dict[str, Any]) -> dict[str, Any]:
    """Aggregate all findings into a final user-facing summary."""
    s = AgentState(**state)
    s.node_status = "summarize"
    s.thought = "Compiling final summary…"

    llm = _get_llm(temperature=0.3)
    findings_text = "\n---\n".join(
        f"[Sub-task {t.id}] {t.description}\n{t.result}"
        for t in s.sub_tasks
        if t.result
    )

    response = await llm.ainvoke([
        SystemMessage(content=SUMMARIZE_SYSTEM_PROMPT),
        HumanMessage(
            content=f"Original intent: {s.intent}\n\nFindings:\n{findings_text}"
        ),
    ])

    s.summary = response.content
    s.node_status = "done"
    s.thought = "Done."
    return s.model_dump()


# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------

def _should_continue_or_summarize(state: dict[str, Any]) -> str:
    """After SelfCorrect, decide whether to loop back or move to Summarize."""
    s = AgentState(**state)
    task = s.sub_tasks[s.current_task_index]

    # If current task still needs work, loop back to BrowserAction
    if task.status == TaskStatus.PENDING:
        return "browser_action"

    # Move to next pending task
    for i, t in enumerate(s.sub_tasks):
        if t.status == TaskStatus.PENDING:
            # We'll update current_task_index inside browser_action on next call
            return "advance"

    # All tasks done
    return "summarize"


def _advance_index(state: dict[str, Any]) -> dict[str, Any]:
    """Advance `current_task_index` to the next pending sub-task."""
    s = AgentState(**state)
    for i, t in enumerate(s.sub_tasks):
        if t.status == TaskStatus.PENDING:
            s.current_task_index = i
            break
    return s.model_dump()


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """Construct and compile the Zenith agent graph."""

    graph = StateGraph(dict)

    # Register nodes
    graph.add_node("parse_intent", parse_intent)
    graph.add_node("browser_action", browser_action)
    graph.add_node("self_correct", self_correct)
    graph.add_node("advance", _advance_index)
    graph.add_node("summarize", summarize)

    # Entry
    graph.set_entry_point("parse_intent")

    # Edges
    graph.add_edge("parse_intent", "browser_action")
    graph.add_edge("browser_action", "self_correct")

    graph.add_conditional_edges(
        "self_correct",
        _should_continue_or_summarize,
        {
            "browser_action": "browser_action",
            "advance": "advance",
            "summarize": "summarize",
        },
    )
    graph.add_edge("advance", "browser_action")
    graph.add_edge("summarize", END)

    return graph.compile()
