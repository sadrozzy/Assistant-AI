from typing import Literal
from app.utils.logger import logger


class TranscriptionService:
    def __init__(self, mode: Literal["local", "api"] = "local"):
        self.mode = mode
        # Здесь можно инициализировать клиента или модель
        self.logger = logger("transcription-service")

    async def transcribe_audio(self, file_path: str) -> str:
        try:
            self.logger.info(f"Transcribing audio file: {file_path}")
            # TODO: Реализовать транскрибацию через Whisper/Ollama или API
            # Вернуть распознанный текст
            pass
        except Exception as e:
            self.logger.exception(f"Transcription failed for {file_path}: {e}")
            raise
