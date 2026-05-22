from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional


class VoiceSpeaker:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._engine = None

    def _ensure_engine(self) -> None:
        if self._engine is not None:
            return
        import pyttsx3

        self._engine = pyttsx3.init()

    def _speak_blocking(self, text: str) -> None:
        self._ensure_engine()
        self._engine.say(text)
        self._engine.runAndWait()

    async def speak(self, text: str) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._speak_blocking, text)


def try_create_speaker() -> Optional[VoiceSpeaker]:
    try:
        import pyttsx3  # noqa: F401
    except Exception:
        return None
    return VoiceSpeaker()
