# Shim for backward compatibility: TaskLinguistAgent -> TaskLinguistCore
from .task_linguist_core import TaskLinguistCore
import inspect
import asyncio


class TaskLinguistAgent(TaskLinguistCore):
    """Backward-compatible alias class so existing imports keep working.
    Wraps the async core implementation with a synchronous run() so the legacy
    BaseAgent.dispatch (which is sync) continues to function correctly.
    """

    def __init__(self):
        super().__init__()
        # Maintain legacy name for display/logging consistency
        self.name = "task_linguist"

    def run(self, input_data: str | dict[str, str]) -> any:  # type: ignore[override]
        # Allow legacy usage where a plain string prompt is passed
        if isinstance(input_data, str):
            input_data = {"command": "parse", "text": input_data}
        else:
            # ensure command defaults to parse so .get chain works
            input_data.setdefault("command", "parse")
            if "text" not in input_data and "prompt" in input_data:
                input_data["text"] = input_data.get("prompt", "")
        result = TaskLinguistCore.run(self, input_data)  # returns coroutine (async def)
        if inspect.iscoroutine(result):
            try:
                return asyncio.run(result)
            except RuntimeError:
                # If already in an event loop (unlikely in packaged exe), fallback
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(result)
        return result
