# MEMANTO CLI Installation & Usage Guide

**Status**: Production Ready
**Last Updated**: March 2025

---

## Table of Contents

1. [Installation](#installation)
2. [First-Time Setup](#first-time-setup)
3. [Server Management](#server-management)
4. [Basic Usage](#basic-usage)
5. [Architecture](#architecture)
6. [Troubleshooting](#troubleshooting)

---

## Installation

### Option 1: Install from PyPI (Future - After Publishing)

```bash
pip install memanto
```

### Option 2: Install from Source (Current)

```bash
# Clone the repository
git clone https://github.com/your-org/memanto.git
cd memanto

# Install in development mode
pip install -e .

# Verify installation
memanto --help
```

**What gets installed:**
- `memanto` command-line tool
- MEMANTO API server (`app/` package)
- CLI interface (`cli/` package)
- All dependencies (typer, rich, httpx, cryptography, fastapi, moorcheh-sdk, etc.)

---

## First-Time Setup

### Quick Start (Recommended - 2 Steps!)

#### Step 1: Get Moorcheh API Key

1. Go to [Moorcheh Dashboard](https://moorcheh.ai)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key

#### Step 2: Initialize & Start

```bash
# Initialize MEMANTO
memanto init
# Enter your API key when prompted

# Start MEMANTO (single command - server + CLI!)
memanto serve
```

**That's it!** The server is now running. Open a new terminal for CLI commands.

### Alternative: Manual Server Management

If you prefer to manage the server separately:

```bash
# Terminal 1: Start the server manually
python -m app.main

# Terminal 2: Initialize CLI
memanto

# Terminal 2: Use CLI commands
memanto agent create my-agent
```

**Output:**
```
+----------------------------------------+
| MEMANTO CLI Initialization               |
| Setting up your MEMANTO configuration... |
+----------------------------------------+

Enter your Moorcheh API key: ********

Testing connection to MEMANTO server...
OK Connection successful!
Server version: 1.0.0

Configuration saved to: ~/.memanto/config.yaml

Next steps:
  1. Start MEMANTO: memanto serve
  2. In another terminal, create an agent: memanto agent create my-agent

Or use the quick workflow:
  memanto serve (starts server)
```

**What happens:**
- API key is encrypted with Fernet and saved to `~/.memanto/config.yaml`
- Connection to server is tested
- CLI is ready to use!

---

## Server Management

### Recommended: Embedded Server Mode (`memanto serve`)

**Terminal 1 - Start Server:**
```bash
memanto serve
```

**Output:**
```
+--------------------------+
| MEMANTO Server Starting... |
| Host: 0.0.0.0:8000       |
+--------------------------+

Starting MEMANTO server...
Server URL: http://localhost:8000
API Docs: http://localhost:8000/docs
Health Check: http://localhost:8000/health

Server is running. Press CTRL+C to stop.
```

**Terminal 2 - Use CLI:**
```bash
memanto agent create my-agent
memanto agent activate my-agent
memanto remember "First memory"
```

**Pros:**
- ✅ Single command to start everything
- ✅ Beautiful terminal UI
- ✅ Built-in port conflict detection
- ✅ Clean shutdown with CTRL+C

**Options:**
```bash
memanto serve --port 8080        # Use different port
memanto serve --reload           # Auto-reload for development
memanto serve --host 127.0.0.1   # Localhost only
```

### Alternative: Manual Server Management

If you prefer to manage the server separately:

**Terminal 1 - Server:**
```bash
python -m app.main
```

**Terminal 2 - CLI:**
```bash
memanto agent create my-agent
memanto agent activate my-agent
memanto remember "First memory"
```

**Use when:**
- You want direct control over uvicorn parameters
- You're debugging server issues
- You're running in production with supervisord/systemd

---

## Basic Usage

### Complete Workflow Example

```bash
# 1. Create an agent (one-time)
memanto agent create my-assistant --pattern tool --description "My AI assistant"

# Output:
# OK Agent 'my-assistant' created successfully!
# Pattern: tool
# Description: My AI assistant

# 2. Activate the agent (starts a session)
memanto agent activate my-assistant --duration-hours 4

# Output:
# OK Agent 'my-assistant' activated!
# Session duration: 4 hours
# Session expires: 2025-12-28T10:30:00

# 3. Store memories
memanto remember "User prefers dark mode" --type preference --tags "ui,settings"
memanto remember "Implemented login feature" --type decision --tags "auth,feature"

# Output for each:
# OK Memory stored successfully!
# Memory ID: abc-123-def-456
# Type: preference | Confidence: 0.8

# 4. Search memories
memanto recall "dark mode" --limit 5

# Output:
# Found 1 memories:
#
# +--------------------------------- Memory 1 ----------------------------------+
# | User prefers dark mode                                                      |
# |                                                                             |
# | User prefers dark mode                                                      |
# |                                                                             |
# | Type: preference | Confidence: 0.80 | Score: 0.923                          |
# +-----------------------------------------------------------------------------+

# 5. Ask questions (RAG)
memanto answer "What UI preferences does the user have?"

# Output:
# +------------------------------- RAG Response --------------------------------+
# | Question: What UI preferences does the user have?                           |
# |                                                                             |
# | Answer:                                                                     |
# | Based on stored memories:                                                   |
# | - User prefers dark mode                                                    |
# +-----------------------------------------------------------------------------+

# 6. Check session status
memanto session info

# Output:
# Active Session
# +-----------------------------------------+
# | Agent ID      | my-assistant            |
# | Session Token | eyJhbGciOiJIUzI1NiI...  |
# +-----------------------------------------+

# 7. When done
memanto agent deactivate

# Output:
# OK Agent 'my-assistant' deactivated
```

### All Available Commands

```bash
# Initialization
memanto init                              # Setup CLI with API key

# Agent Management
memanto agent create AGENT_ID             # Create new agent
memanto agent list                        # List all agents
memanto agent activate AGENT_ID           # Start session
memanto agent deactivate                  # End session
memanto agent delete AGENT_ID            # Delete agent (prompts to keep/purge cloud memories)

# Memory Operations
memanto remember "content"                # Store memory (fact)
memanto remember "content" --type TYPE    # Store with type
memanto remember "content" --tags "a,b"   # Store with tags
memanto recall "query"                    # Search memories
memanto answer "question"                    # RAG question answering

# Session Management
memanto session info                      # Show session details
memanto session extend --hours 2          # Extend session

# Configuration
memanto config show                       # Display config

# Help
memanto --help                            # Show all commands
memanto COMMAND --help                    # Show command help
```

---

## Architecture

### How It Works

```
┌─────────────────┐
│   User Types    │
│  memanto init     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  CLI (cli/main.py)                  │
│  - Typer framework                  │
│  - Rich terminal UI                 │
│  - Config management                │
│  - API client wrapper               │
└────────┬────────────────────────────┘
         │ HTTP Requests
         │ (Authorization: Bearer API_KEY)
         │ (X-Session-Token: JWT)
         ▼
┌─────────────────────────────────────┐
│  MEMANTO Server (app/main.py)         │
│  - FastAPI application              │
│  - Session-based API                │
│  - JWT token management             │
│  - Agent & memory services          │
└────────┬────────────────────────────┘
         │ moorcheh-sdk
         │ (Semantic operations)
         ▼
┌─────────────────────────────────────┐
│  Moorcheh Cloud                     │
│  - No-indexing semantic database    │
│  - Instant write-to-search          │
│  - Namespace: memanto_agent_{id}      │
└─────────────────────────────────────┘
```

### File Structure

```
memanto/
├── pyproject.toml          # Package definition, entry point
├── app/                    # MEMANTO Server
│   ├── main.py            # FastAPI app
│   ├── routes/            # API endpoints
│   └── services/          # Business logic
├── cli/                    # CLI Package
│   ├── main.py            # CLI entry point (Typer app)
│   ├── client/            # API client wrapper
│   │   └── api_client.py
│   └── config/            # Config management
│       ├── models.py      # Pydantic models
│       └── manager.py     # Encryption, persistence
└── ~/.memanto/               # User config (created at runtime)
    ├── config.yaml        # User configuration
    └── .key               # Encryption key (0600 permissions)
```

### Entry Point

**[pyproject.toml:25](pyproject.toml#L25)**
```toml
[project.scripts]
memanto = "cli.main:app"
```

This creates the `memanto` command that runs the Typer app in `cli/main.py`.

### Configuration File

**Location:** `~/.memanto/config.yaml` (Linux/Mac) or `C:\Users\<user>\.memanto\config.yaml` (Windows)

**Contents:**
```yaml
version: "2.0"

server:
  url: "localhost"
  port: 8000
  auto_start: false

moorcheh:
  api_key_encrypted: "gAAAAABf..."  # Fernet encrypted

session:
  default_duration_hours: 4
  auto_extend: true

cli:
  interactive_mode: true
  smart_parse: true
  color_output: true

# AI / Answer & Recall configuration (all optional — defaults shown)
ai:
  model: "anthropic.claude-sonnet-4-20250514-v1:0"  # LLM used for answer
  temperature: 0.7        # LLM temperature (0.0–1.0)
  answer_limit: 5         # context memories passed to LLM for `answer`
  threshold: 0.25         # confidence threshold for memory relevance
  recall_limit: 10        # top-N results returned by `recall`

active_agent_id: "my-assistant"
active_session_token: "eyJhbGciOiJIUzI1NiI..."
```

**Security:**
- API key encrypted with Fernet (symmetric encryption)
- Encryption key in `~/.memanto/.key` with 0600 permissions
- Never commit config files to version control

---

## Troubleshooting

### "memanto: command not found"

**Cause:** Package not installed or not in PATH

**Solution:**
```bash
# If installed with pip:
pip install memanto

# If installed from source:
cd memanto
pip install -e .

# Verify:
which memanto  # Should show path to command
memanto --help # Should work
```

### "Connection failed" Error

**Cause:** MEMANTO server not running

**Check:**
```bash
# Is server running?
curl http://localhost:8000/health

# Should return:
# {"status":"healthy","service":"MEMANTO","version":"1.0.0"}
```

**Solution:**
```bash
# Start server in a separate terminal
cd memanto
python -m app.main
```

### "No active agent" Error

**Cause:** Trying to use memory commands without an active session

**Solution:**
```bash
# List available agents
memanto agent list

# Activate one
memanto agent activate AGENT_ID
```

### "MEMANTO not initialized" Error

**Cause:** CLI not configured

**Solution:**
```bash
memanto
# Follow the prompts
```

### Session Expired

**Cause:** JWT token expired (default: 4 hours)

**Solution:**
```bash
# Option 1: Reactivate
memanto agent activate AGENT_ID

# Option 2: Extend (if still valid)
memanto session extend --hours 4
```

### Windows Unicode Errors

All Unicode symbols (✓ ✗ ⚠ 🟢) replaced with ASCII equivalents (OK, ERROR, Warning, [Active]).

If you still see encoding errors, ensure your terminal uses UTF-8:
```bash
# PowerShell
chcp 65001

# CMD
chcp 65001
```

---

## Next Steps

1. **Try the Quick Start workflow** (5 minutes)
2. **Read the [CLI User Guide](CLI_USER_GUIDE.md)** for detailed examples
3. **Explore memory types** - fact, decision, instruction, etc.
4. **Set up automation** - Use CLI in scripts

---

## Support

- **Documentation:** [CLI_USER_GUIDE.md](CLI_USER_GUIDE.md)
- **API Reference:** [V2_QUICK_START.md](V2_QUICK_START.md)
- **Issues:** GitHub Issues
- **Moorcheh:** [moorcheh.ai/docs](https://moorcheh.ai/docs)

---

**License**: MIT
**Last Updated**: December 2025

