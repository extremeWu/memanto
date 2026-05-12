"""
Research Assistant — LangGraph agent with Memanto persistent memory.

Demonstrates cross-session memory: a research agent that stores findings
in Memanto, then recalls them in a later session.

Usage:
    python research_assistant.py          # Run research
    python research_assistant.py --recall # Recall previous findings
"""

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

from memanto_memory import MemantoMemory

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("research-agent")


def simulate_research(memory: MemantoMemory, topic: str) -> None:
    """Simulate a research agent gathering and storing findings."""
    print(f"\n{'='*60}")
    print(f"🔬 Research Agent — Topic: {topic}")
    print(f"{'='*60}\n")

    # --- Step 1: Define research goals ---
    print("📋 Setting research goals...")
    memory.remember(
        f"Research goal: Investigate latest trends in {topic}",
        memory_type="goal",
    )
    memory.remember(
        f"Focus area: Identify key players, market size, and emerging technologies in {topic}",
        memory_type="goal",
    )

    # --- Step 2: Simulated research findings ---
    findings = {
        "fact": [
            f"The global {topic} market is projected to reach $42.3B by 2030, growing at 32.5% CAGR.",
            f"Major players in {topic} include OpenAI, Google DeepMind, and Anthropic.",
            f"R1, DeepSeek-R1, and Qwen2.5 are the top open-weight models for {topic} applications as of Q2 2026.",
        ],
        "preference": [
            f"Developers in the {topic} space prefer Python-first frameworks with comprehensive documentation.",
            f"The community favors Apache 2.0 and MIT licenses for open-source {topic} projects.",
        ],
        "observation": [
            f"Smaller specialized models (7B-32B params) are outperforming generalist 70B+ models on domain-specific {topic} benchmarks.",
            f"Agentic frameworks like LangGraph and CrewAI are the primary orchestration tools used in production {topic} deployments.",
        ],
    }

    for mem_type, contents in findings.items():
        for content in contents:
            print(f"  💾 [{mem_type}] {content[:80]}...")
            memory.remember(content, memory_type=mem_type)

    # --- Step 3: Store a decision ---
    memory.remember(
        f"Decision: Recommend Python + LangGraph + Memanto as the tech stack for building production {topic} agents.",
        memory_type="decision",
    )

    print(f"\n✅ Research complete. {sum(len(v) for v in findings.values())} findings stored.")
    print("   Memories are persisted in Memanto — accessible from any future session.\n")


def recall_findings(memory: MemantoMemory) -> None:
    """Recall previously stored findings, proving cross-session persistence."""
    print(f"\n{'='*60}")
    print("🔄 Cross-Session Recall — Retrieving Past Research")
    print(f"{'='*60}\n")

    queries = [
        ("market", "Market intelligence"),
        ("preference", "Developer preferences"),
        ("decision", "Previous decisions"),
        ("goal", "Research goals"),
    ]

    for query, label in queries:
        print(f"🔍 {label}: searching \"{query}\"...")
        results = memory.recall(query, limit=3)
        if results:
            for r in results:
                content = r.get("content", "")
                mtype = r.get("type", "?")
                score = r.get("confidence", r.get("score", "N/A"))
                print(f"  ├ [{mtype}] (score: {score})")
                print(f"  └ {content[:120]}")
        else:
            print(f"  └ No memories found for \"{query}\"")
        print()

    # Also try the grounded answer endpoint
    print("🧠 Grounded Answer from Memanto:")
    answer = memory.answer(
        "Based on previously stored research, what tech stack is recommended "
        "for building production AI agents and why?"
    )
    if answer:
        print(f"   {answer}")
    else:
        print("   (No answer — Memanto server may not be running locally)")


def main():
    parser = argparse.ArgumentParser(
        description="LangGraph Research Assistant with Memanto Memory"
    )
    parser.add_argument(
        "--topic",
        default="AI agent frameworks",
        help="Research topic to investigate",
    )
    parser.add_argument(
        "--recall",
        action="store_true",
        help="Recall past research instead of running new research",
    )
    args = parser.parse_args()

    with MemantoMemory(agent_name="research-assistant") as memory:
        if args.recall:
            recall_findings(memory)
        else:
            simulate_research(memory, args.topic)

    print("Session closed. Memories persist in Memanto.\n")


if __name__ == "__main__":
    main()
