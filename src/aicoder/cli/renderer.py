from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text


class StreamRenderer:
    def __init__(self, show_thinking: bool = True):
        self._console = Console()
        self._show_thinking = show_thinking

    def print_tool_call(self, name: str, input_str: str):
        self._console.print(Text(f"  [{name}] {input_str[:150]}", style="dim yellow"))

    def print_tool_result(self, output: str):
        lines = output.strip().split("\n")
        preview = "\n".join(lines[:8])
        if len(lines) > 8:
            preview += f"\n  ... ({len(lines)} lines total)"
        for line in preview.split("\n"):
            self._console.print(Text(f"  {line}", style="dim"))

    def print_response(self, text: str):
        if text:
            self._console.print(Markdown(text))

    def print_error(self, text: str):
        self._console.print(f"[red]{text}[/red]")

    def print_info(self, text: str):
        self._console.print(f"[dim]{text}[/dim]")

    def render_stream(self, events):
        """Render streaming events as inline incremental output.
        Deduplicates: shows thinking block, then tool calls, then final response."""
        import inspect

        if inspect.isasyncgen(events):
            return self._render_async_stream(events)
        else:
            return self._render_sync_stream(events)

    def _render_sync_stream(self, events):
        thinking = ""
        final_text = ""
        tool_seen: set[str] = set()

        for event in events:
            kind = event.get("event", "")

            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    thinking += chunk.content

            elif kind == "on_tool_start":
                name = event.get("name", "")
                inp = str(event.get("data", {}).get("input", ""))
                key = f"{name}:{inp}"
                if key not in tool_seen:
                    tool_seen.add(key)
                    self.print_tool_call(name, inp)

            elif kind == "on_tool_end":
                outp = str(event.get("data", {}).get("output", ""))
                if outp:
                    self.print_tool_result(outp)

            elif kind == "on_chat_model_end":
                out = event.get("data", {}).get("output", {})
                if hasattr(out, "content") and out.content:
                    final_text = out.content

        if thinking and self._show_thinking and not final_text:
            self._console.print(Text(thinking[-300:], style="blue dim"))

        if final_text:
            self.print_response(final_text)

        return final_text

    async def _render_async_stream(self, events):
        thinking = ""
        final_text = ""
        tool_seen: set[str] = set()

        async for event in events:
            kind = event.get("event", "")

            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    thinking += chunk.content

            elif kind == "on_tool_start":
                name = event.get("name", "")
                inp = str(event.get("data", {}).get("input", ""))
                key = f"{name}:{inp}"
                if key not in tool_seen:
                    tool_seen.add(key)
                    self.print_tool_call(name, inp)

            elif kind == "on_tool_end":
                outp = str(event.get("data", {}).get("output", ""))
                if outp:
                    self.print_tool_result(outp)

            elif kind == "on_chat_model_end":
                out = event.get("data", {}).get("output", {})
                if hasattr(out, "content") and out.content:
                    final_text = out.content

        if thinking and self._show_thinking and not final_text:
            self._console.print(Text(thinking[-300:], style="blue dim"))

        if final_text:
            self.print_response(final_text)

        return final_text
