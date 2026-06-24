from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.console import Group, Console


class StreamRenderer:
    def __init__(self, show_thinking: bool = True):
        self._console = Console()
        self._show_thinking = show_thinking

    def print_thinking(self, text: str):
        if self._show_thinking and text:
            self._console.print(Panel(Text(text[:500], style="blue"), title="Thinking", border_style="blue"))

    def print_tool_call(self, name: str, input_str: str):
        self._console.print(Panel(
            Text(f"{name}\n{input_str[:200]}", style="dim"),
            title="Tool Call", border_style="yellow"
        ))

    def print_tool_result(self, output: str):
        self._console.print(Panel(
            Text(output[:500], style="dim"),
            title="Output", border_style="green"
        ))

    def print_response(self, text: str):
        if text:
            self._console.print(Markdown(text))

    def print_error(self, text: str):
        self._console.print(f"[red]{text}[/red]")

    def print_info(self, text: str):
        self._console.print(f"[dim]{text}[/dim]")

    def render_stream(self, events):
        """Render a stream of astream_events with a Live display.
        Accepts either sync iterator or async iterator."""
        import inspect
        if inspect.isasyncgen(events):
            return self._render_async_stream(events)
        else:
            return self._render_sync_stream(events)

    def _render_sync_stream(self, events):
        thinking_text = ""
        tool_name = ""
        tool_input = ""
        tool_output = ""
        final_text = ""

        def build():
            layout = Layout()
            layout.split_column(
                Layout(name="top", size=3),
                Layout(name="body"),
            )
            top_items = []
            if thinking_text and self._show_thinking:
                top_items.append(Panel(
                    Text(thinking_text[-200:], style="blue"),
                    title="Thinking", border_style="blue", height=3
                ))
            if not top_items:
                top_items.append(Text("", style="dim"))
            layout["top"].update(Group(*top_items))
            body_items = []
            if tool_name:
                body_items.append(Panel(
                    Text(f"{tool_name}\n{tool_input[:200]}", style="dim"),
                    title="Tool", border_style="yellow"
                ))
            if tool_output:
                body_items.append(Panel(
                    Text(tool_output[:300], style="dim"),
                    title="Result", border_style="green"
                ))
            if final_text:
                body_items.append(Markdown(final_text))
            if not body_items:
                body_items.append(Text("...", style="dim italic"))
            layout["body"].update(Group(*body_items))
            return layout

        with Live(build(), refresh_per_second=10, transient=False, console=self._console) as live:
            for event in events:
                kind = event.get("event", "")
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        thinking_text += chunk.content
                elif kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    ti = event.get("data", {}).get("input", {})
                    tool_input = str(ti)
                    tool_output = ""
                elif kind == "on_tool_end":
                    to = event.get("data", {}).get("output", "")
                    tool_output = str(to)[:500]
                elif kind == "on_chat_model_end":
                    out = event.get("data", {}).get("output", {})
                    if hasattr(out, "content") and out.content:
                        final_text = out.content
                live.update(build())
        return final_text

    async def _render_async_stream(self, events):
        thinking_text = ""
        tool_name = ""
        tool_input = ""
        tool_output = ""
        final_text = ""

        def build():
            layout = Layout()
            layout.split_column(
                Layout(name="top", size=3),
                Layout(name="body"),
            )
            top_items = []
            if thinking_text and self._show_thinking:
                top_items.append(Panel(
                    Text(thinking_text[-200:], style="blue"),
                    title="Thinking", border_style="blue", height=3
                ))
            if not top_items:
                top_items.append(Text("", style="dim"))
            layout["top"].update(Group(*top_items))
            body_items = []
            if tool_name:
                body_items.append(Panel(
                    Text(f"{tool_name}\n{tool_input[:200]}", style="dim"),
                    title="Tool", border_style="yellow"
                ))
            if tool_output:
                body_items.append(Panel(
                    Text(tool_output[:300], style="dim"),
                    title="Result", border_style="green"
                ))
            if final_text:
                body_items.append(Markdown(final_text))
            if not body_items:
                body_items.append(Text("...", style="dim italic"))
            layout["body"].update(Group(*body_items))
            return layout

        with Live(build(), refresh_per_second=10, transient=False, console=self._console) as live:
            async for event in events:
                kind = event.get("event", "")
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        thinking_text += chunk.content
                elif kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    ti = event.get("data", {}).get("input", {})
                    tool_input = str(ti)
                    tool_output = ""
                elif kind == "on_tool_end":
                    to = event.get("data", {}).get("output", "")
                    tool_output = str(to)[:500]
                elif kind == "on_chat_model_end":
                    out = event.get("data", {}).get("output", {})
                    if hasattr(out, "content") and out.content:
                        final_text = out.content
                live.update(build())

        return final_text
