# 🧠 Memanto + LangGraph Integration: Cross-Session Memory for Stateful Agents

[![LangGraph](https://img.shields.io/badge/LangGraph-✅_Compatible-blue)](https://langchain-ai.github.io/langgraph/)
[![Memanto](https://img.shields.io/badge/Memanto-✅_Powered-purple)](https://memanto.ai/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-yellow)](https://python.org)

[![Demo GIF](https://raw.githubusercontent.com/extremeWu/memanto/langgraph-memanto/assets/langgraph-memanto-demo.gif)](https://raw.githubusercontent.com/extremeWu/memanto/langgraph-memanto/assets/langgraph-memanto-demo.gif)

> **Watch the 30-second demo GIF above** — shows the full cross-session recall flow: architecture overview → morning session storing 6 typed memories → afternoon session recalling them from fresh LangGraph state → verification.

This example shows how to give **LangGraph agents** persistent, cross-session memory using **Memanto** as the external memory layer.

> **A Customer Support Agent that remembers every conversation — across sessions, threads, and days.**

This example demonstrates how to integrate **Memanto** as a persistent long-term memory layer inside a **LangGraph** stateful agent workflow. The agent uses Memanto's three primitives (`remember`, `recall`, `answer`) to maintain context across disjointed conversations — something LangGraph's built-in state alone cannot do.

## 🎯 What This Demo Shows

| Capability | Without Memanto | With Memanto |
|---|---|---|
| **Cross-session recall** | ❌ Forgets everything after reset | ✅ Remembers past conversations |
| **Typed semantic memory** | ❌ No memory categories | ✅ 13 types (fact, preference, goal, etc.) |
| **Conflict detection** | ❌ Silent contradictions | ✅ Versioned, no silent overwrites |
| **Grounded answers** | ❌ No RAG over memories | ✅ `answer()` returns LLM-grounded responses |
| **Temporal queries** | ❌ No recency awareness | ✅ Filter by time: `as-of`, `changed-since` |

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────┐
│                  LangGraph Agent                    │
│  ┌──────────┐   ┌──────────┐   ┌────────────────┐  │
│  │  State    │   │  Nodes   │   │  Edge Routing  │  │
│  │  (Thread) │──▶│(Tools)   │──▶│(Conditional)   │  │
│  └──────────┘   └──────────┘   └────────────────┘  │
│       │                                               │
│       │  Cross-session memory (not in LangGraph state)│
│       ▼                                               │
│  ┌────────────────────────────────────────────────┐   │
│  │              Memanto Memory Layer              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │   │
│  │  │remember()│  │ recall() │  │   answer()    │ │   │
│  │  │  Store   │  │  Search  │  │  RAG Grounded │ │   │
│  │  └──────────┘  └──────────┘  └──────────────┘ │   │
│  │  ┌──────────────────────────────────────────┐  │   │
│  │  │  Memory Store (typed, versioned, exact   │  │   │
│  │  │  search, temporal-aware, zero-ingestion) │  │   │
│  │  └──────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Prerequisites

```bash
pip install memanto langgraph langchain-core httpx
```

### 2. Get a Moorcheh API Key

1. Go to [Moorcheh Dashboard](https://console.moorcheh.ai/api-keys)
2. Create a new API key
3. Set it as an environment variable:

```bash
export MOORCHEH_API_KEY="your-api-key-here"
```

### 3. Run the Example

```bash
cd examples/langgraph-memanto
python agent.py
```

## 📦 What's Included

| File | Purpose |
|---|---|
| `agent.py` | Main LangGraph agent with Memanto integration |
| `memanto_tools.py` | LangGraph-compatible tool wrappers for Memanto's three primitives |
| `demo.py` | Script demonstrating cross-session capabilities |
| `requirements.txt` | Dependencies |

## 🎬 Demo Walkthrough

### Session 1 — User introduces themselves

```
User: "Hi, I'm Alice and I prefer dark mode."
Agent: Remembering fact: name=Alice, preference=dark mode
       Stored as `fact` and `preference` memory types
```

### Session 2 — (hours later, new graph state)

```
User: "What did we talk about before? Also, dark or light theme?"
Agent: Recalling from Memanto...
       Found: "Alice prefers dark mode" (preference, 3 hours ago)
       Found: "User name is Alice" (fact, 3 hours ago)
       → Cross-session recall successful!
Agent: "Hi Alice! Last time you mentioned you prefer dark mode.
        I've loaded your preferences from memory."
```

### Session 3 — Conflict detection

```
User: "Actually, I'd like light mode from now on."
Agent: Detected conflict with previous preference!
       Versioning: old=dark mode, new=light mode
       Stored: "Alice prefers light mode" (updated preference)
```

## 🔧 How It Works

### Memanto's Three Primitives (as LangGraph Tools)

```python
@tool
def memanto_remember(
    content: str,
    memory_type: str = "observation",
    title: str | None = None,
    agent_id: str | None = None,
) -> str:
    """Store a memory into Memanto's long-term memory store."""
    result = client.remember(
        agent_id=aid,
        memory_type=memory_type,
        title=title or content[:80],
        content=content[:500],
    )
    return result.get("message", f"Stored as {memory_type}")

@tool
def memanto_recall(
    query: str,
    memory_type: str | None = None,
    limit: int = 5,
    agent_id: str | None = None,
) -> str:
    """Search Memanto's long-term memory for relevant past information."""
    kwargs = {"limit": limit}
    if memory_type:
        kwargs["type"] = [memory_type]
    result = client.recall(agent_id=aid, query=query, **kwargs)
    memories = result.get("memories", [])
    if not memories:
        return "No relevant memories found."
    return json.dumps(memories, indent=2, default=str)

@tool
def memanto_answer(query: str, agent_id: str | None = None) -> str:
    """Get a grounded AI answer generated directly from Memanto's memory store."""
    result = client.answer(agent_id=aid, question=query)
    return result.get("answer", str(result))
```

### Agent Flow

```
USER INPUT
    │
    ▼
┌──────────────────┐
│  Route Input     │
│  (LLM decides)   │
└──────┬───────────┘
       │
  ┌────┴────┐
  │         │
  ▼         ▼
Recall  Process + Remember
  │         │
  └────┬────┘
       │
       ▼
  Generate Response
  (augmented with memories)
```

## 📊 Performance

Memanto achieves **89.8% on LongMemEval** and **87.1% on LoCoMo** — outperforming Mem0, Zep, and Letta. This integration ensures your LangGraph agents benefit from that SOTA performance with zero ingestion latency.

## 📹 Video Demo

*(Include a 30-second GIF or video link here showing cross-session recall)*

## 🔗 Links

- [Memanto Documentation](https://github.com/moorcheh-ai/memanto)
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [Moorcheh Dashboard](https://console.moorcheh.ai/api-keys)
- [#Memanto](https://x.com/search?q=%23Memanto) on X/Twitter

---

<p align="center">Built with ❤️ for the Memanto + LangGraph Integration Challenge</p>
