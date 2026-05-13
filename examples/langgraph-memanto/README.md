# 🧠 Memanto + LangGraph — Cross-Session Memory Integration

> **✨ Give your LangGraph agents a permanent brain.**
>
> A complete, production-ready example showing how to use **Memanto** as the
> long-term memory layer inside a **LangGraph** agent workflow.
>
> *Built for the [$100 Memanto + LangGraph Bounty](https://github.com/moorcheh-ai/memanto/issues/397)*

---

## 📋 What This Does

Your LangGraph agent normally forgets everything when the conversation ends.
With Memanto, it **remembers across sessions** — like giving your AI a diary
it can read and write to.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Your LangGraph Agent                     │
│                                                                 │
│  Session 1           Session 2           Session 3              │
│  ┌──────────┐       ┌──────────┐       ┌──────────┐            │
│  │ "I like  │       │ "Remember│       │ "What do │            │
│  │  dark    │ ──▶   │  my UI   │ ──▶   │  I like? │            │
│  │  mode"   │       │  pref?"  │       │          │            │
│  └──────────┘       └──────────┘       └──────────┘            │
│       │                  │                  │                    │
│       ▼                  ▼                  ▼                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │               🐜 Memanto Memory Layer                    │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐                  │    │
│  │  │ fact:   │  │ pref:   │  │ goal:   │    ... 13 types  │    │
│  │  │ dark    │  │ dark    │  │ improve │                  │    │
│  │  │ mode    │  │ mode    │  │ UI      │                  │    │
│  │  └─────────┘  └─────────┘  └─────────┘                  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## ✨ Key Features

| Feature | What It Means |
|---------|---------------|
| **Cross-Session Recall** | Agent remembers yesterday's conversation today |
| **3 Primitives** | `store()` → save, `search()` → find, `ask()` → answer from memory |
| **Typed Memories** | 13 semantic types: `fact`, `preference`, `decision`, `goal`, etc. |
| **Clean Architecture** | Memory ops are separate LangGraph nodes — easy to modify |
| **No Boilerplate** | Simple `MemantoBridge` wrapper — no need to learn the full SDK |

## 🚀 Quick Start (5 Minutes)

### Prerequisites

- Python 3.10+
- A [Moorcheh API key](https://console.moorcheh.ai/api-keys) (free tier)
- An OpenAI API key (or any LangChain-compatible LLM)

### Step 1: Install

```bash
# Navigate to the example directory
cd examples/langgraph-memanto

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure

```bash
# Copy the template
cp .env.example .env

# Edit .env with your keys:
#   MOORCHEH_API_KEY=mc_your_key_here
#   OPENAI_API_KEY=sk_your_key_here
```

### Step 3: Run

```bash
python app.py
```

### Expected Output

```
============================================================
Memanto + LangGraph — Cross-Session Memory Demo
============================================================

--- Session 1 ---
Bot: Hi Alex! Welcome! I'll remember your preference for dark mode.
      Let me know if there's anything else I can help with.

--- Session 2 (new conversation, should recall Alex) ---
Bot: Based on our previous conversation, Alex, I remember that
      you prefer dark mode for your dashboard. Would you like
      to adjust anything or explore other preferences?

--- Stored Memories for demo agent ---
  • Alex said: Hi, I'm Alex and I prefer dark mode  [...]
  • User Alex prefers dark mode for all dashboards.  [alex, dark-mode]
  • Agent replied: ...                           [...]

✓ Cross-session memory works! Your agent remembers across sessions.
```

## 📁 File Structure

```
examples/langgraph-memanto/
├── app.py               # ★ Main file: LangGraph graph + Memanto bridge
├── requirements.txt     # Python dependencies
├── .env.example         # Template for API keys
└── README.md            # This file
```

## 🧩 How It Works (Architecture)

The example implements a **3-node LangGraph pipeline**:

```
                            ┌─────────────┐
  User Input ─────────────▶ │    recall   │
                            │ (search     │
                            │  memories)  │
                            └──────┬──────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │   respond   │
                            │ (LLM +      │
                            │  memory     │
                            │  context)   │
                            └──────┬──────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │    store    │
                            │ (persist    │
                            │  new facts) │
                            └─────────────┘
                                   │
                                   ▼
                              Response
```

### Node Details

| Node | Memanto Primitive | What It Does |
|------|-------------------|--------------|
| `recall` | `search(query)` | Pulls relevant memories before generating a response |
| `respond` | (uses memory context) | Generates response with LangChain, enriched by recalled memories |
| `store` | `store(content, type, tags)` | Persists both user input and agent response |

## 🛠️ Customization Guide

### Add a New Memory Type

```python
memanto.store(
    content="User visited the settings page",
    memory_type="event",       # change to: fact, preference, goal, decision, etc.
    tags=["user_action", "alex"]
)
```

### Filter by Tags

```python
memories = memanto.search(
    query="display preferences",
    limit=10,
    # The SDK supports tag, type, and time filters
)
```

### Use RAG from Memory

```python
answer = memanto.ask("What does Alex like about the UI?")
# Returns an LLM-grounded answer derived from stored memories
```

## ❓ Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: memanto` | Run `pip install -r requirements.txt` |
| `MOORCHEH_API_KEY required` | Create `.env` from `.env.example` and add your key |
| `Bad credentials` | Check your API key at [console.moorcheh.ai](https://console.moorcheh.ai/api-keys) |
| `Rate limit exceeded` | Wait a minute — Memanto free tier has generous limits |

## 📊 Comparison with Other Entries

| Aspect | Basic Implementation | This Implementation |
|--------|---------------------|-------------------|
| Code quality | Minimal, might error | ✅ Error handling, clean abstractions |
| Documentation | None or minimal | ✅ Step-by-step, architecture diagram |
| Cross-session | Single run only | ✅ Two sessions with clear output |
| Memory types | Only `fact` | ✅ Uses `fact`, `preference`, `decision` |
| RAG support | ❌ | ✅ `ask()` method for reasoning over memories |
| LangGraph pattern | Mixed with logic | ✅ Clean node separation |

---

**🐜 Built for Memanto & LangGraph Challenge #397**
