import asyncio
from concurrent.futures import CancelledError
from typing import AsyncGenerator, List, Optional, Union
from pydantic import BaseModel
from loguru import logger

from pipecat.frames.frames import (
    Frame,
    TTSAudioRawFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
    StartInterruptionFrame,
    CancelFrame,
    StartFrame,
    EndFrame,
    ErrorFrame,
    BotStoppedSpeakingFrame,
    LLMFullResponseEndFrame,
    TTSSpeakFrame,
)
from pipecat.services.ai_services import WordTTSService
from pipecat.processors.frame_processor import FrameDirection
from pipecat.transcriptions.language import Language
from kokoro import KPipeline


class KokoroTTSService(WordTTSService):
    """TTS service implementation using the Kokoro model with interruption and word-level timing support."""

    class InputParams(BaseModel):
        language: Optional[Language] = Language.EN
        voice: str = "af_heart"
        speed: Optional[Union[str, float]] = 1.0
        split_pattern: str = r"\n+"
        emotion: Optional[List[str]] = []  # For future emotion support

    def __init__(
        self,
        *,
        sample_rate: int = 24000,
        params: InputParams = InputParams(),
        **kwargs,
    ):
        # Enable sentence aggregation for better audio quality
        # Disable automatic text frame pushing - we'll handle it with word timestamps
        super().__init__(
            aggregate_sentences=True,
            push_text_frames=False,
            sample_rate=sample_rate,
            **kwargs,
        )
        self._params = params
        self._pipeline = None
        self._lang_code = self._get_lang_code(params.language)
        self._current_generation_task = None
        self._interrupt_event = asyncio.Event()
        self._is_speaking = False
        self._context_id = None

    def can_generate_metrics(self) -> bool:
        return True

    def _get_lang_code(self, language: Language) -> str:
        """Map PipeCat language to Kokoro language code."""
        LANG_MAP = {
            Language.EN: "a",  # American English
            Language.EN_GB: "b",  # British English
            Language.ES: "e",  # Spanish
            Language.FR: "f",  # French
            Language.HI: "h",  # Hindi
            Language.IT: "i",  # Italian
            Language.JA: "j",  # Japanese
            Language.PT: "p",  # Brazilian Portuguese
            Language.ZH: "z",  # Mandarin Chinese
        }
        return LANG_MAP.get(language, "a")

    async def start(self, frame: StartFrame):
        """Initialize the Kokoro pipeline and reset state."""
        await super().start(frame)
        if not self._pipeline:
            self._pipeline = KPipeline(lang_code=self._lang_code)
        self._interrupt_event.clear()
        self._is_speaking = False
        self._context_id = None

    async def stop(self, frame: EndFrame):
        """Clean up resources and stop any ongoing generation."""
        await self._handle_interruption(None, None)
        await super().stop(frame)
        self._pipeline = None

    async def cancel(self, frame: CancelFrame):
        """Handle cancellation request."""
        await self._handle_interruption(None, None)
        await super().cancel(frame)

    async def flush_audio(self):
        """Ensure any buffered audio is processed."""
        if self._is_speaking:
            await self._handle_interruption()
            self._context_id = None

    async def _handle_interruption(
        self, frame: StartInterruptionFrame = None, direction: FrameDirection = None
    ):
        """Handle interruption request by stopping current generation."""
        logger.debug("Handling interruption in Kokoro TTS")
        self._interrupt_event.set()

        if self._current_generation_task and not self._current_generation_task.done():
            try:
                self._current_generation_task.cancel()
                await self._current_generation_task
            except (asyncio.CancelledError, CancelledError):
                pass
            finally:
                self._current_generation_task = None

        self._is_speaking = False
        await self.stop_all_metrics()

        if frame:
            await super()._handle_interruption(frame, direction)

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process incoming frames and manage frame processing state."""
        await super().process_frame(frame, direction)

        # Pause processing when speaking and resume when done
        if isinstance(frame, TTSSpeakFrame):
            await self.pause_processing_frames()
        elif isinstance(frame, LLMFullResponseEndFrame) and self._context_id:
            await self.pause_processing_frames()
        elif isinstance(frame, BotStoppedSpeakingFrame):
            await self.resume_processing_frames()

    async def run_tts(self, text: str) -> AsyncGenerator[Frame, None]:
        """Generate audio from text using Kokoro with interruption support and metrics."""
        if not text or not text.strip():
            return

        try:
            logger.debug(f"Generating TTS with Kokoro: [{text}]")
            self._interrupt_event.clear()
            self._is_speaking = True
            self._context_id = str(uuid.uuid4())

            await self.start_ttfb_metrics()
            yield TTSStartedFrame()

            # Create and store the generation task
            async def generate_audio():
                generator = self._pipeline(
                    text,
                    voice=self._params.voice,
                    speed=float(self._params.speed) if self._params.speed else 1.0,
                    split_pattern=self._params.split_pattern,
                )

                word_start_time = 0
                for word, duration, audio in generator:
                    # Check for interruption before processing each chunk
                    if self._interrupt_event.is_set():
                        raise asyncio.CancelledError("TTS generation interrupted")

                    # Convert numpy array to bytes if needed
                    if not isinstance(audio, bytes):
                        audio = audio.tobytes()

                    # Add word timestamp for alignment
                    if word:
                        await self.add_word_timestamps([(word, word_start_time)])
                        word_start_time += duration

                    yield TTSAudioRawFrame(
                        audio=audio,
                        sample_rate=self.sample_rate,
                        num_channels=1,
                    )

            self._current_generation_task = asyncio.create_task(generate_audio())

            try:
                async for frame in self._current_generation_task:
                    await self.stop_ttfb_metrics()
                    yield frame
                    await asyncio.sleep(0)  # Allow interruption processing

                # Add final timestamps and metrics
                await self.add_word_timestamps(
                    [
                        ("TTSStoppedFrame", 0),
                        ("LLMFullResponseEndFrame", 0),
                        ("Reset", 0),
                    ]
                )
                await self.start_tts_usage_metrics(text)

                yield TTSStoppedFrame()

            except asyncio.CancelledError:
                logger.debug("TTS generation cancelled")
                yield TTSStoppedFrame()
                raise

            finally:
                self._is_speaking = False
                self._current_generation_task = None
                self._context_id = None

        except Exception as e:
            if not isinstance(e, asyncio.CancelledError):
                logger.error(f"Kokoro TTS error: {e}")
                await self.push_error(ErrorFrame(f"Kokoro TTS error: {str(e)}"))
            yield TTSStoppedFrame()
            self._is_speaking = False
            await self.stop_all_metrics()

    async def set_model(self, model: str):
        """Update the model/voice."""
        self._model_name = model
        await super().set_model(model)
        logger.info(f"Switching TTS model to: [{model}]")

    async def update_setting(self, key: str, value: any):
        """Update service settings."""
        if key == "voice":
            self._params.voice = value
        elif key == "speed":
            self._params.speed = float(value)
        elif key == "language":
            self._lang_code = self._get_lang_code(value)
            # Recreate pipeline with new language
            if self._pipeline:
                await self._handle_interruption()
                self._pipeline = KPipeline(lang_code=self._lang_code)
        else:
            logger.warning(f"Unknown setting for Kokoro TTS service: {key}")
