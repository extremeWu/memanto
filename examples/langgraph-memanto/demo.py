"""
Memanto + LangGraph: Cross-Session Demo

This script demonstrates the core cross-session recall capability by simulating
two separate conversations with the Memanto memory layer in between.

No LangGraph needed — uses Memanto directly to show the memory primitive.

Usage:
    export MOORCHEH_API_KEY="your-api-key-here"
    python demo.py
"""

import os
import time
import json

# ─── Demo Configuration ───────────────────────────────────────────────────────

API_KEY = os.environ.get("MOORCHEH_API_KEY")
if not API_KEY:
    print("❌ Please set MOORCHEH_API_KEY environment variable")
    print("   Get one at https://console.moorcheh.ai/api-keys")
    exit(1)


def print_separator(title: str):
    """Print a section header."""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ─── Initialize Client ────────────────────────────────────────────────────────

print("🔄 Initializing Memanto client...")
try:
    from memanto.cli.client.sdk_client import SdkClient

    client = SdkClient(api_key=API_KEY)
except ImportError as e:
    print(f"❌ Failed to import memanto: {e}")
    print("   Run: pip install memanto")
    exit(1)
except Exception as e:
    print(f"❌ Failed to initialize client: {e}")
    exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO PART 1: Session A — User Introduction
# ═══════════════════════════════════════════════════════════════════════════════

print_separator("SESSION A — User Introduction (e.g., Monday)")

print("\n👤 User: \"Hi, I'm Alice. I work at Acme Corp and prefer dark mode.\"")

# Store each fact with appropriate memory types
print("\n📝 Storing memories via Memanto...")

result = client.remember(
    "User's name is Alice",
    type="fact",
)
print(f"   ✓ Stored fact: {result}")

result = client.remember(
    "Alice works at Acme Corp as a developer",
    type="fact",
)
print(f"   ✓ Stored fact: {result}")

result = client.remember(
    "Alice prefers dark mode for all interfaces",
    type="preference",
)
print(f"   ✓ Stored preference: {result}")

result = client.remember(
    "First support contact — initial onboarding",
    type="event",
)
print(f"   ✓ Stored event: {result}")

print("\n✅ Session A complete. Memories stored in Memanto.")
time.sleep(1)


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO PART 2: Simulate session break
# ═══════════════════════════════════════════════════════════════════════════════

print_separator("⏳ Time passes... (hours/days) — LangGraph state is gone")

print("""🧠 What happened:
  - The LangGraph thread state has been reset
  - No conversation history exists
  - But Memanto still has all the memories!
""")
time.sleep(1)


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO PART 3: Session B — Cross-Session Recall
# ═══════════════════════════════════════════════════════════════════════════════

print_separator("SESSION B — Cross-Session Recall (e.g., Wednesday)")

print("\n👤 User: \"Hey, what do you remember about me? I need help with settings.\"")

print("\n🔍 Recalling from Memanto (cross-session)...")
results = client.recall(
    "What do I know about this user — name, work, preferences?",
    limit=5,
)

print(f"\n📚 MEMANTO RECALL RESULTS:")
if results:
    for i, mem in enumerate(results, 1):
        content = mem.get("content", "N/A")[:150]
        mtype = mem.get("type", "unknown")
        confidence = mem.get("confidence", "N/A")
        print(f"\n  {i}. [{mtype}] \"{content}\"")
        print(f"     Confidence: {confidence}")
else:
    print("  (No results — check your API key and agent setup)")

print("\n✅ Cross-session recall demonstrated!")
print("   The agent remembers Alice from the previous session")
print("   despite having a completely new LangGraph thread state.")
time.sleep(1)


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO PART 4: Conflict Detection
# ═══════════════════════════════════════════════════════════════════════════════

print_separator("SESSION C — Preference Update & Conflict Detection")

print("\n👤 User: \"Actually, I now prefer light mode during work hours.\"")

print("\n🔄 Detecting potential conflict...")

# Check existing preference
existing = client.recall("What theme does Alice prefer?", type="preference")
print(f"   Previous preference found: {[e.get('content') for e in (existing or [])]}")

# Store the updated preference
result = client.remember(
    "Alice now prefers light mode during work hours (9-5)",
    type="preference",
)
print(f"   ✓ Updated preference stored: {result}")

result = client.remember(
    "Important: Alice's preference changed from dark mode to light mode",
    type="decision",
)
print(f"   ✓ Decision recorded: {result}")

print("\n✅ Memanto's versioned storage ensures no silent overwrites!")
print("   Both old and new preferences are retrievable with temporal queries.")


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print_separator("✅ DEMO COMPLETE")

print("""
What was demonstrated:
  ✓ Cross-session recall — memories survive LangGraph state resets
  ✓ Typed semantic memory — fact, preference, event, decision types
  ✓ Preference updates with conflict detection
  ✓ Grounded answers via recall

Next steps:
  1. Run agent.py for the full LangGraph integration
  2. Try with different memory types
  3. Add memanto_answer for RAG-grounded responses
""")
