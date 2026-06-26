"""Context compaction — summarize conversation history to stay within token limits."""


def build_compaction_prompt(agent, config) -> str:
    """Read current state and build a compaction prompt."""
    try:
        state = agent.get_state(config)
        msgs = state.values.get("messages", []) if state else []
    except Exception:
        return "Summarize the conversation so far."

    if len(msgs) < 4:
        return ""

    # Keep last 2 exchanges (4 messages), summarize the rest
    keep = min(4, len(msgs))
    return (
        "Compaction task: Summarize the conversation above into a single paragraph. "
        "Include key decisions, files modified, and current progress. "
        "Be concise — the summary replaces the full conversation history."
    )
