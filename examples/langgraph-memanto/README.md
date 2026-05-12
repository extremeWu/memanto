# Memanto + LangGraph Integration

A clean example showing how to use **Memanto** as the long-term memory layer inside a **LangGraph** agent.

## What It Does

This example builds a support agent that:
1. **Remembers** user facts across conversations (cross-session memory)
2. **Recalls** relevant past memories before each response
3. **Stores** every interaction for future reference

## How It Works

```
User Input → [Recall Memories from Memanto] → [Generate Response with LangChain] → [Store New Memories] → Response
```

Memanto handles all the persistent storage — your LangGraph state stays clean and stateless.

## Requirements

- Python 3.10+
- A [Moorcheh API key](https://console.moorcheh.ai/api-keys) (free tier available)

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your API keys
cp .env.example .env
# Edit .env with your MOORCHEH_API_KEY and OPENAI_API_KEY

# 3. Run the demo
python app.py
```

The demo runs two "sessions" — the second one automatically recalls what was stored in the first.

## File Structure

```
langgraph-memanto/
├── app.py              # Main example: LangGraph graph + Memanto bridge
├── requirements.txt    # Python dependencies
├── .env.example        # Template for API keys
└── README.md           # This file
```

## Key Concepts Shown

| Concept | Implementation |
|---------|---------------|
| Cross-session recall | `memanto.search(query)` before generating responses |
| Persistent memory | `memanto.store(content, type, tags)` on every interaction |
| RAG from memory | `memanto.ask(question)` for LLM-grounded answers |
| Typed memories | Using Memanto's 13 memory types (fact, preference, decision, etc.) |
| LangGraph nodes | Memory operations are separate graph nodes for clean architecture |

## Going Further

- Add more memory types: `goal`, `commitment`, `relationship`, `error`
- Filter by time: `memanto.search(..., created_after="2026-01-01")`
- Batch upload documents with `memanto.upload_file()`
- Add conflict detection when two memories contradict each other

---

Built for the [Memanto + LangGraph Bounty](https://github.com/moorcheh-ai/memanto/issues/397) ($100).
