"""Token usage tracking across a session."""


class TokenTracker:
    def __init__(self):
        self._rounds: list[dict] = []
        self._by_model: dict[str, dict] = {}

    def record(self, token_usage: dict | None, model_name: str = ""):
        if not token_usage:
            return
        prompt = token_usage.get("prompt_tokens", 0) or token_usage.get("input_tokens", 0)
        completion = token_usage.get("completion_tokens", 0) or token_usage.get("output_tokens", 0)
        total = token_usage.get("total_tokens", prompt + completion)
        entry = {
            "model": model_name,
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
        }
        self._rounds.append(entry)
        if model_name not in self._by_model:
            self._by_model[model_name] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "count": 0}
        m = self._by_model[model_name]
        m["prompt_tokens"] += prompt
        m["completion_tokens"] += completion
        m["total_tokens"] += total
        m["count"] += 1

    @property
    def total_tokens(self):
        return sum(r["total_tokens"] for r in self._rounds)

    @property
    def total_prompt(self):
        return sum(r["prompt_tokens"] for r in self._rounds)

    @property
    def total_completion(self):
        return sum(r["completion_tokens"] for r in self._rounds)

    @property
    def round_count(self):
        return len(self._rounds)

    def summary(self) -> str:
        if not self._rounds:
            return "No usage data yet."
        lines = [
            f"  Rounds: {self.round_count}",
            f"  Total tokens: {self.total_tokens:,}",
            f"  Prompt tokens: {self.total_prompt:,}",
            f"  Completion tokens: {self.total_completion:,}",
        ]
        if self._by_model:
            lines.append("  By model:")
            for name, m in self._by_model.items():
                lines.append(f"    {name}: {m['total_tokens']:,}t ×{m['count']}")
        return "\n".join(lines)
