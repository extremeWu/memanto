# Hybrid Timeline Guide: Combining Automatic + Semantic

**For**: AI agents and developers using MEMANTO's timeline features
**Status**: Production Guide

---

## Introduction

MEMANTO's **hybrid timeline model** combines the reliability of automatic server-side timestamps with the richness of semantic timeline memories. This guide shows you how to get the best of both worlds.

---

## The Two Levels

### Level 1: Automatic Timestamps (Always There)
**What**: Server automatically adds `created_at` and `updated_at` to every memory
**Effort**: Zero - happens transparently
**Use For**: Temporal filtering, time-based queries, activity tracking
**Example**:
```bash
# Get memories from last 7 days
curl ".../recall?created_after=2025-12-20T00:00:00Z"
```

### Level 2: Semantic Timeline (Optional)
**What**: Agents explicitly store timeline context (sessions, milestones, phases)
**Effort**: Small - agent chooses when to store
**Use For**: Understanding project history, answering "why" and "what" questions
**Example**:
```bash
# Store milestone
curl -X POST ".../remember?memory_type=event&title=Phase+H+Complete&..."
```

---

## When to Use Each Level

| Scenario | Automatic Timestamps | Semantic Timeline | Both |
|----------|---------------------|-------------------|------|
| **"Show me today's work"** | ✅ Sufficient | ⚠️ Overkill | - |
| **"What did we accomplish this week?"** | ⚠️ Too broad | ✅ Better | ✅ Best |
| **"When did Phase H start?"** | ❌ Can't answer | ✅ Required | - |
| **"Show recent decisions"** | ✅ Filter by time | ⚠️ Good context | ✅ Best |
| **"Track project velocity"** | ⚠️ Basic | ✅ Meaningful | ✅ Best |
| **"Activity heatmap"** | ✅ Sufficient | ❌ Not needed | - |

---

## Pattern 1: Filter First, Contextualize Second

**Use automatic timestamps to narrow down, then semantic timeline to understand.**

### Example: Find Recent Major Decisions

```bash
# Step 1: Use automatic timestamp to filter (fast, broad)
curl "http://localhost:8000/api/v2/agents/{agent_id}/recall?\
query=decision&\
created_after=2025-12-01T00:00:00Z&\
limit=20" \
-H "X-Session-Token: {session_token}"

# Step 2: Look for semantic timeline tags in results
# Filter client-side for memories with tags like:
# - "milestone", "phase-transition", "major-decision"
```

**Python Example**:
```python
import requests
from datetime import datetime, timedelta

session_token = "your_session_token_here" # Replace with your actual session token

# Get last month's decisions
last_month = (datetime.utcnow() - timedelta(days=30)).isoformat() + 'Z'
response = requests.get(f"""
    http://localhost:8000/api/v2/agents/claude_dev/recall?
    query=decision&
    created_after={last_month}&
    limit=50
""", headers={"X-Session-Token": session_token})

memories = response.json()['memories']

# Find major milestones using semantic tags
major_decisions = [
    m for m in memories
    if 'milestone' in m.get('tags', []) or 'major' in m.get('title', '').lower()
]

print(f"Total decisions: {len(memories)}")
print(f"Major decisions: {len(major_decisions)}")
```

---

## Pattern 2: Timeline Anchors with Activity Fill

**Use semantic timeline to mark key moments, automatic timestamps to fill gaps.**

### Example: Project Timeline with Daily Activity

```python
import requests
from datetime import datetime, timedelta

session_token = "your_session_token_here" # Replace with your actual session token

# Get semantic timeline anchors (milestones, phases)
semantic_response = requests.get(f"""
    http://localhost:8000/api/v2/agents/claude_dev/recall?
    query=milestone+phase+session&
    tags=timeline&
    limit=50
""", headers={"X-Session-Token": session_token})

milestones = semantic_response.json()['memories']

# For each period between milestones, get activity via automatic timestamps
for i in range(len(milestones) - 1):
    start = milestones[i]['created_at']
    end = milestones[i+1]['created_at']

    activity = requests.get(f"""
        http://localhost:8000/api/v2/agents/claude_dev/recall?
        query=*&
        created_after={start}&
        created_before={end}&
        limit=1000
    """, headers={"X-Session-Token": session_token})

    print(f"\nBetween {milestones[i]['title']} and {milestones[i+1]['title']}:")
    print(f"  Activity: {len(activity.json()['memories'])} memories")
```

**Visualization**:
```
Project Timeline
─────────────────────────────────────────────────────
Phase A    ●●●●●●●●●●    Phase B    ●●●●    Phase C
Started    (45 memories) Complete   (18)    Started
Dec 1                    Dec 15             Dec 27
```

---

## Pattern 3: Temporal Queries with Semantic Enrichment

**Start with automatic timestamp query, enrich with semantic context.**

### Example: Weekly Status Report

```python
from datetime import datetime, timedelta
from collections import Counter
import requests

def generate_weekly_report(agent_id, session_token):
    # Get last week's data using automatic timestamps
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat() + 'Z'

    response = requests.get(f"""
        http://localhost:8000/api/v2/agents/{agent_id}/recall?
        query=*&
        created_after={week_ago}&
        limit=100
    """, headers={"X-Session-Token": session_token})

    memories = response.json()['memories']

    # Basic stats (from automatic timestamps)
    total = len(memories)
    types = Counter(m.get('type') for m in memories)

    # Semantic enrichment
    milestones = [m for m in memories if 'milestone' in m.get('tags', [])]
    sessions = [m for m in memories if 'session-start' in m.get('tags', [])]
    decisions = [m for m in memories if m.get('type') == 'decision']

    # Generate report
    report = f"""
    Weekly Report for {agent_id}
    ════════════════════════════════════════

    ACTIVITY (Automatic Timestamps)
    • Total Memories: {total}
    • Memory Types: {dict(types)}
    • Time Period: Last 7 days

    HIGHLIGHTS (Semantic Timeline)
    • Milestones Achieved: {len(milestones)}
      {chr(10).join(f'  - {m["title"]}' for m in milestones[:5])}

    • Sessions: {len(sessions)}
    • Major Decisions: {len(decisions)}
      {chr(10).join(f'  - {d["title"]}' for d in decisions[:3])}
    """

    return report

# Example usage:
# session_token = "your_session_token_here"
# print(generate_weekly_report("claude_dev", session_token))
```

---

## Pattern 4: Smart Session Restoration

**Use both levels for optimal context restoration.**

### Bootstrap Script Enhancement

```bash
#!/bin/bash

AGENT_ID="claude_dev"
MEMANTO_URL="http://localhost:8000"
SESSION_TOKEN="your_session_token_here" # Replace with your actual session token

echo "Restoring agent context..."

# 1. Find last session using semantic timeline
LAST_SESSION=$(curl -s "$MEMANTO_URL/api/v2/agents/$AGENT_ID/recall?\
query=session+start&\
tags=timeline,session-start&\
limit=1" -H "X-Session-Token: $SESSION_TOKEN" | python -m json.tool | grep '"created_at"' | head -1)

# 2. Get all activity since last session using automatic timestamps
if [ -n "$LAST_SESSION" ]; then
    LAST_DATE=$(echo $LAST_SESSION | cut -d'"' -f4)

    echo "Last session: $LAST_DATE"
    echo "Retrieving activity since then..."

    curl -s "$MEMANTO_URL/api/v2/agents/$AGENT_ID/recall?\
query=*&\
created_after=$LAST_DATE&\
limit=50" -H "X-Session-Token: $SESSION_TOKEN" | python -m json.tool
else
    echo "No previous session found, getting recent context..."

    curl -s "$MEMANTO_URL/api/v2/agents/$AGENT_ID/recall?\
query=important+context&\
limit=20" -H "X-Session-Token: $SESSION_TOKEN" | python -m json.tool
fi

# 3. Store new session start (semantic timeline)
CURRENT_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
curl -s -X POST "$MEMANTO_URL/api/v2/agents/$AGENT_ID/remember?\
memory_type=fact&\
title=Session+Started+$CURRENT_DATE&\
content=Agent+started+new+work+session&\
tags=timeline,session-start" \
-H "X-Session-Token: $SESSION_TOKEN" > /dev/null

echo "✅ Context restored. Session start recorded."
```

---

## Pattern 5: Progressive Timeline Building

**Start with automatic, add semantic as patterns emerge.**

### Recommended Workflow

**Week 1: Automatic Only**
```bash
# Just use MEMANTO normally - automatic timestamps work
curl -X POST ".../remember?memory_type=fact&title=Bug+Fix&content=..."
# Server adds created_at and updated_at automatically
```

**Week 2: Add Session Markers**
```bash
# Start adding session markers when you notice patterns
# Morning session
curl -X POST ".../remember?memory_type=fact&title=Morning+Session&tags=timeline,session-start&..."

# Evening session
curl -X POST ".../remember?memory_type=fact&title=Evening+Session&tags=timeline,session-start&..."
```

**Week 3: Add Milestones**
```bash
# When something significant happens
curl -X POST ".../remember?memory_type=event&title=Feature+Complete&tags=timeline,milestone&..."
```

**Week 4: Full Hybrid**
```bash
# Now using both:
# - Automatic timestamps (always working)
# - Session markers (track work patterns)
# - Milestones (mark achievements)
# - Phase transitions (track project evolution)
```

---

## Pattern 6: Temporal Analytics

**Combine both for powerful insights.**

### Example: Find Productive Periods

```python
def find_productive_periods(agent_id, tenant_id):
    """
    Use automatic timestamps to find when agent is most productive,
    then use semantic timeline to understand why.
    """

    # Get last month's activity (automatic)
    last_month = (datetime.utcnow() - timedelta(days=30)).isoformat() + 'Z'
    response = requests.get(f"""
        .../recall?
        tenant_id={tenant_id}&
        query=*&
        created_after={last_month}&
        limit=1000
    """)

    memories = response.json()['memories']

    # Group by hour of day
    from collections import defaultdict
    hourly_activity = defaultdict(list)

    for m in memories:
        if 'created_at' in m:
            hour = datetime.fromisoformat(m['created_at'].replace('Z', '')).hour
            hourly_activity[hour].append(m)

    # Find peak hour
    peak_hour = max(hourly_activity.items(), key=lambda x: len(x[1]))[0]

    # Look for semantic context during peak hour
    peak_memories = hourly_activity[peak_hour]
    sessions_during_peak = [
        m for m in peak_memories
        if 'session-start' in m.get('tags', [])
    ]

    print(f"Peak productivity hour: {peak_hour}:00 UTC")
    print(f"Average memories during peak: {len(peak_memories) / 30:.1f} per day")

    if sessions_during_peak:
        print(f"\nSessions typically started at this hour: {len(sessions_during_peak)}")
        print("Semantic context: Morning work sessions")
    else:
        print("\nNo semantic session markers - just observed activity pattern")
```

---

## Best Practices Summary

### ✅ DO

1. **Trust automatic timestamps** - They're always there, always accurate
2. **Add semantic timeline for meaning** - Sessions, milestones, phases
3. **Use temporal filters first** - Narrow down with `created_after`/`created_before`
4. **Tag consistently** - Use `timeline`, `session-start`, `milestone`, `phase`
5. **Combine for insights** - Automatic shows WHEN, semantic shows WHY

### ❌ DON'T

1. **Don't duplicate** - Don't store "created at" in content if automatic timestamp exists
2. **Don't over-tag** - Not every memory needs timeline tags
3. **Don't ignore automatic** - Even without semantic timeline, you have temporal data
4. **Don't stress** - Semantic timeline is RECOMMENDED, not REQUIRED

---

## Quick Reference: API Query Patterns

### Automatic Timestamps Only
```bash
# Last 7 days
?created_after=2025-12-20T00:00:00Z

# Date range
?created_after=2025-12-01T00:00:00Z&created_before=2025-12-31T23:59:59Z

# Last 24 hours
?created_after=$(date -d '24 hours ago' -u +%Y-%m-%dT%H:%M:%SZ)
```

### Semantic Timeline Only
```bash
# Milestones
?query=milestone&tags=timeline,milestone

# Sessions
?query=session&tags=timeline,session-start

# Phases
?query=phase&tags=timeline,phase
```

### Hybrid (Best)
```bash
# Recent milestones
?query=milestone&tags=timeline,milestone&created_after=2025-12-01T00:00:00Z

# This week's sessions
?query=session&tags=timeline,session-start&created_after=$(date -d '7 days ago' -u +%Y-%m-%dT%H:%M:%SZ)
```

---

## Example: Complete Hybrid Workflow

### Agent Daily Routine

**Morning (Session Start)**:
```bash
# Server automatically timestamps this memory
curl -X POST ".../remember?\
memory_type=fact&\
title=Morning+Session+Started&\
content=Starting+work+on+authentication+module&\
tags=timeline,session-start&\
confidence=1.0"

# created_at: 2025-12-27T09:00:00Z (automatic)
# updated_at: 2025-12-27T09:00:00Z (automatic)
# tags: [timeline, session-start] (semantic)
```

**During Work (Regular Memories)**:
```bash
# Just store normally - automatic timestamps handle temporal data
curl -X POST ".../remember?memory_type=decision&title=Use+JWT&content=..."
# created_at: 2025-12-27T11:30:00Z (automatic)

curl -X POST ".../remember?memory_type=fact&title=Bug+Fixed&content=..."
# created_at: 2025-12-27T14:15:00Z (automatic)
```

**Major Achievement (Milestone)**:
```bash
# Add semantic timeline for major events
curl -X POST ".../remember?\
memory_type=event&\
title=Authentication+Module+Complete&\
content=Completed+full+OAuth+2.0+implementation+with+JWT+tokens&\
tags=timeline,milestone,authentication&\
confidence=1.0"

# created_at: 2025-12-27T16:00:00Z (automatic)
# tags: [timeline, milestone, authentication] (semantic)
```

**Query Later**:
```bash
# Use automatic timestamp to filter
curl ".../recall?created_after=2025-12-27T00:00:00Z&limit=50"
# Returns all 4 memories

# Use semantic tags to find milestones
curl ".../recall?query=milestone&tags=timeline,milestone"
# Returns just the achievement

# Hybrid: Recent milestones
curl ".../recall?query=milestone&tags=timeline&created_after=2025-12-20T00:00:00Z"
# Best of both worlds
```

---

## Troubleshooting

### "I don't see timestamps in recall results"

**Cause**: Moorcheh's search API doesn't return metadata by default
**Solution**: Timestamps are in metadata, used for filtering but not always displayed
**Workaround**: Use temporal filters (`created_after`) to verify they work

### "My semantic timeline isn't showing up"

**Check**:
1. Did you add timeline tags? (`tags=timeline,milestone`)
2. Are you querying with correct tags? (`?tags=timeline`)
3. Did you use right memory type? (Use `event` for milestones)

### "Which level should I use?"

**Answer**: BOTH! They complement each other:
- Automatic = Temporal filtering (always works)
- Semantic = Contextual understanding (when valuable)

---

## Resources

- **API Reference**: [AGENT_RUNTIME_GUIDE.md](AGENT_RUNTIME_GUIDE.md)
- **Best Practices**: [AGENT_MEMORY_BEST_PRACTICES.md](AGENT_MEMORY_BEST_PRACTICES.md)
- **Visualization**: [TIMELINE_VISUALIZATION_EXAMPLES.md](TIMELINE_VISUALIZATION_EXAMPLES.md)
- **Temporal Helpers**: [app/utils/temporal_helpers.py](app/utils/temporal_helpers.py)

---

**Remember**: The hybrid timeline model gives you the best of both worlds. Use automatic timestamps for reliability and temporal filtering. Add semantic timeline when you want meaningful context and richer queries. Together, they create a powerful temporal memory system.

---

**Status**: Production Guide
**Last Updated**: December 2025
