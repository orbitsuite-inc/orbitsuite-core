# Shim for backward compatibility: EngineerAgent -> EngineerCore
from .engineer_core import EngineerCore
import inspect
import asyncio
from typing import Any


class EngineerAgent(EngineerCore):
    """Backward-compatible alias for legacy import paths.
    Provides the same interface while exposing core functionality while
    converting the async core run() into a synchronous call expected by dispatch.
    """

    def __init__(self, output_dir: str | None = None):
        super().__init__(output_dir)
        self.name = "engineer"  # legacy display

    def run(self, input_data: Any):  # type: ignore[override]
        # Normalize legacy string invocation to structured dict expected by core
        if isinstance(input_data, str):
            input_data = {"command": "analyze", "description": input_data}
        result = EngineerCore.run(self, input_data)  # async def -> coroutine
        if inspect.iscoroutine(result):
            try:
                return asyncio.run(result)
            except RuntimeError:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(result)
        return result
