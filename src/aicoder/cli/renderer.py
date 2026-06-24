from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.console import Group


class StreamRenderer:
    def __init__(self, show_thinking: bool = True):
        self._show_thinking = show_thinking
        self._thinking = ""
        self._tool_name = ""
        self._tool_input = ""
        self._tool_output = ""
        self._final_text = ""

    def _build_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="thinking", size=8),
            Layout(name="body"),
        )
        elements = []
        if self._tool_name:
            elements.append(
                Panel(
                    Text(f"{self._tool_name}\n{self._tool_input[:200]}",
                         style="dim"),
                    title="Tool Call",
                    border_style="yellow",
                )
            )
        if self._tool_output:
            elements.append(
                Panel(
                    Text(self._tool_output[:500], style="dim"),
                    title="Output",
                    border_style="green",
                )
            )
        if self._final_text:
            elements.append(Markdown(self._final_text))
        if not elements:
            elements.append(Text("Thinking...", style="dim italic"))

        layout["thinking"].update(
            Panel(
                Text(self._thinking[-500:] if self._thinking else "Waiting...", style="blue"),
                title="Thinking" if self._show_thinking else "",
                border_style="blue",
                height=8,
            )
        )
        layout["body"].update(Group(*elements))
        return layout

    def render(self, events, show_thinking: bool = True):
        self._show_thinking = show_thinking
        with Live(self._build_layout(), refresh_per_second=10, transient=False) as live:
            for event in events:
                kind = event.get("event", "")
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content"):
                        self._thinking += chunk.content
                elif kind == "on_tool_start":
                    self._tool_name = event.get("name", "")
                    self._tool_input = str(event.get("data", {}).get("input", ""))
                    self._tool_output = ""
                elif kind == "on_tool_end":
                    self._tool_output = str(event.get("data", {}).get("output", ""))[:500]
                elif kind == "on_chat_model_end":
                    output = event.get("data", {}).get("output", "")
                    if hasattr(output, "content"):
                        self._final_text = output.content
                live.update(self._build_layout())
        return self._final_text or "(no response)"
