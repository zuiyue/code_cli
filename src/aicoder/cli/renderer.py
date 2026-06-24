from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text


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
