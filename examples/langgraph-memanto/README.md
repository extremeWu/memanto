# LangGraph + Memanto: Customer Support Agent with Cross-Session Memory

[![LangGraph](https://img.shields.io/badge/LangGraph-🕸️-1DA1F2)](https://langchain-ai.github.io/langgraph/)
[![Memanto](https://img.shields.io/badge/Memanto-🧠-34D058)](https://memanto.ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **🏆 Bounty Entry** — [$100 LangGraph + Memanto Integration Challenge](https://github.com/moorcheh-ai/memanto/issues/397)

A **customer support agent** built with [LangGraph](https://langchain-ai.github.io/langgraph/) that uses [Memanto](https://memanto.ai/) as its **long-term memory layer**. The agent remembers user preferences, facts, and decisions **across entirely separate sessions** — even across different processes, machines, or days.

## ✨ The Key Feature: Cross-Session Recall

Standard LangGraph agents only remember what happened in the **current thread**. Once the thread ends, the state is gone.

This example wires Memanto's persistent memory into the graph so that:

```
Session 1 (Tue 10am)              Session 2 (Wed 3pm)
┌──────────────────────┐          ┌──────────────────────┐
│ User: "I prefer      │          │ User: "What theme    │
│        dark mode"    │   ───▶   │        should I use?" │
│                      │          │                      │
│ Agent stores in      │  recall  │ Agent queries memanto│
│ memanto memory  🧠   │◀────────│ → "dark mode"        │
└──────────────────────┘          └──────────────────────┘
```

## 🏗️ Architecture

```
                    ┌─────────────────────────────┐
                    │     LangGraph (StateGraph)   │
                    │                              │
  User ──▶ START ──▶│  load_memory                 │
                    │    │                         │
                    │    ▼                         │
                    │  call_model (LLM)            │
                    │    │                         │
                    │    ├── new memories? ──▶ save_memory ──▶ END
                    │    └── no memories ────▶ END             │
                    └─────────────────────────────┘
                              │          ▲
                     remember │          │ recall / answer
                              ▼          │
                    ┌─────────────────────┴──┐
                    │     Memanto (Moorcheh)  │
                    │  Persistent Long-Term   │
                    │  Memory (typed semantic)│
                    └─────────────────────────┘
```

### Graph Nodes

| Node | What it does |
|------|-------------|
| `load_memory` | Queries memanto for relevant memories about the user before the LLM responds |
| `call_model` | Calls an LLM (OpenRouter free tier) with conversation history + memanto context |
| `save_memory` | Persists new facts/preferences back to memanto for future sessions |

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- A **Moorcheh API key** — [get one free at console.moorcheh.ai](https://console.moorcheh.ai/api-keys) (100K ops/month free tier)
- An **OpenRouter API key** — [get one free at openrouter.ai/keys](https://openrouter.ai/keys)

### 2. Setup

```bash
cd examples/langgraph-memanto

# Create virtual environment
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env — add your MOORCHEH_API_KEY and OPENROUTER_API_KEY
```

### 3. Run the Cross-Session Demo

```bash
python customer_support.py --demo
```

This runs two synthetic sessions:

1. **Session 1** — "I prefer dark mode for the dashboard UI" → saved to memanto
2. **Session 2** — "Does this user have any UI preferences?" → memanto recalls "dark mode"

### 4. Interactive Mode

```bash
python customer_support.py
```

Try these commands:

```
>>> pref: I prefer concise technical answers
>>> check: What communication style should I use?
>>> pref: My timezone is Asia/Shanghai
>>> check: What timezone is the user in?
```

## 📊 The Bounty Criteria

| Criterion | How this example meets it |
|-----------|--------------------------|
| **Cross-Session Recall** | Memories survive across separate `invoke()` calls, different thread IDs, even different processes |
| **Clean, documented code** | Single folder, type-annotated, docstrings on every public function |
| **GIF/video demo** | [Watch the demo on YouTube](https://youtu.be/vEtOaoweIG4) (memanto setup) |

## 🔄 How Cross-Session Works (Under the Hood)

1. **On graph start**, `load_memory` calls `memanto.recall()` with the user's latest message as a semantic query
2. Memanto returns relevant memories from **any previous session** — no LangGraph checkpoint needed
3. These memories are injected into the system prompt so the LLM sees them
4. When the LLM discovers new facts, it outputs a `__memories__` JSON block
5. `save_memory` persists them via `memanto.remember()`
6. Next session, step 1 retrieves them again → **true cross-session persistence**

## 🧪 What Makes This Different From Regular LangGraph Memory

| Approach | Scope | Persistence |
|----------|-------|------------|
| LangGraph `MemorySaver` | Current session only | Wiped when thread ends |
| LangGraph store | Single process | Lost on restart |
| **Memanto (this example)** | **Global** | **Survives restarts, across processes, across days** |

## 📝 License

MIT — part of the Memanto project's LangGraph integration examples.
