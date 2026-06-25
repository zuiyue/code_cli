from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text


class StreamRenderer:
    def __init__(self, show_thinking: bool = True):
        self._console = Console()
        self._show_thinking = show_thinking

    def print_tool_call(self, name: str, input_str: str):
        self._console.print(Panel(
            Text(f"{input_str[:200]}", style="dim"),
            title=f"[bold yellow]{name}[/bold yellow]",
            border_style="yellow",
            padding=(0, 1),
        ))

    def print_tool_result(self, output: str):
        lines = output.strip().split("\n")
        preview = "\n".join(lines[:10])
        if len(lines) > 10:
            preview += f"\n[dim]... ({len(lines)} lines total)[/dim]"
        self._console.print(Panel(
            Text(preview, style="dim green"),
            title="[green]result[/green]",
            border_style="green",
            padding=(0, 1),
        ))

    def print_thinking(self, text: str):
        if self._show_thinking and text.strip():
            self._console.print(Panel(
                Text(text.strip()[-400:], style="blue"),
                title="[blue]thinking[/blue]",
                border_style="blue",
                padding=(0, 1),
            ))

    def print_response(self, text: str):
        if text:
            self._console.print()
            self._console.print(Markdown(text))

    def print_error(self, text: str):
        self._console.print(f"\n[red]{text}[/red]")

    def print_info(self, text: str):
        self._console.print(f"[dim]{text}[/dim]")

    def render_stream(self, events):
        """Render streaming events inline with panels."""
        import inspect
        # Print empty line for visual separation from prompt
        self._console.print()
        if inspect.isasyncgen(events):
            return self._render_async_stream(events)
        else:
            return self._render_sync_stream(events)

    def _render_sync_stream(self, events):
        thinking = ""
        final_text = ""

        for event in events:
            kind = event.get("event", "")
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    thinking += chunk.content
            elif kind == "on_tool_start":
                name = event.get("name", "")
                inp = str(event.get("data", {}).get("input", ""))
                self.print_tool_call(name, inp)
            elif kind == "on_tool_end":
                outp = str(event.get("data", {}).get("output", ""))
                if outp:
                    self.print_tool_result(outp)
            elif kind == "on_chat_model_end":
                out = event.get("data", {}).get("output", {})
                if hasattr(out, "content") and out.content:
                    final_text = out.content

        if thinking and not final_text:
            self.print_thinking(thinking)
        if final_text:
            self.print_response(final_text)
        return final_text

    async def _render_async_stream(self, events):
        thinking = ""
        final_text = ""
        started = False

        async for event in events:
            kind = event.get("event", "")
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    if not started:
                        self._console.print("  [dim]Thinking...[/dim]")
                        started = True
                    thinking += chunk.content
            elif kind == "on_tool_start":
                name = event.get("name", "")
                inp = str(event.get("data", {}).get("input", ""))
                self.print_tool_call(name, inp)
            elif kind == "on_tool_end":
                outp = str(event.get("data", {}).get("output", ""))
                if outp:
                    self.print_tool_result(outp)
            elif kind == "on_chat_model_end":
                out = event.get("data", {}).get("output", {})
                if hasattr(out, "content") and out.content:
                    final_text = out.content

        if thinking and not final_text:
            self.print_thinking(thinking)
        if final_text:
            self.print_response(final_text)
        return final_text
