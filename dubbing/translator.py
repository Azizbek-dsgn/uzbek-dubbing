"""Natural Uzbek translation for timestamped dubbing segments."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Iterable

from .transcriber import TranscriptSegment


@dataclass
class TranslationSegment:
    """A transcript segment paired with its Uzbek dubbing text."""

    index: int
    start_time: float
    end_time: float
    source_text: str
    translated_text: str
    language: str | None = None

    @property
    def duration(self) -> float:
        """Return the available duration for the dubbed speech."""

        return max(0.0, self.end_time - self.start_time)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return {
            "index": self.index,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "source_text": self.source_text,
            "translated_text": self.translated_text,
            "language": self.language,
        }


SYSTEM_PROMPT = """Siz professional dublyaj rejissyorisiz.
Berilgan ingliz yoki rus tilidagi matnni o‘zbek tiliga tabiiy, ravon va so‘zlashuv/podkast uslubida tarjima qiling.
Ma’noni, ohangni, hazil va iboralarni saqlang. So‘zma-so‘z yoki kitobiy tarjimadan qoching.
Natijada faqat tarjima matnini qaytaring: izoh, qo‘shtirnoq, markdown va sarlavha yozmang.
"""


def _response_text(response: Any) -> str:
    """Extract response text across compatible google-genai response shapes."""

    text = getattr(response, "text", None)
    if text:
        return str(text).strip()
    return str(response).strip()


class GeminiTranslator:
    """Small Gemini client wrapper with retry handling."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", retries: int = 3):
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError(
                "google-genai o‘rnatilmagan. `pip install -r dubbing/requirements.txt` ni bajaring."
            ) from exc
        self._client = genai.Client(api_key=api_key)
        self.model = model
        self.retries = max(1, retries)

    def translate_one(self, text: str, source_language: str | None, duration: float) -> str:
        """Translate one speech segment, retrying transient API failures."""

        prompt = (
            f"{SYSTEM_PROMPT}\n"
            f"Manba tili: {source_language or 'ingliz yoki rus'}\n"
            f"Original audio vaqti: {duration:.2f} soniya. Tarjima shu vaqtga sig‘adigan darajada ixcham bo‘lsin.\n"
            f"Matn:\n{text}"
        )
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )
                translated = _response_text(response)
                if not translated:
                    raise RuntimeError("Gemini bo‘sh tarjima qaytardi.")
                return translated
            except Exception as exc:  # API libraries expose several exception types.
                last_error = exc
                if attempt + 1 < self.retries:
                    time.sleep(2**attempt)
        raise RuntimeError(f"Gemini tarjimasida xato: {last_error}") from last_error

    def translate_segments(
        self,
        segments: Iterable[TranscriptSegment],
        cached: dict[int, str] | None = None,
    ) -> list[TranslationSegment]:
        """Translate segments and reuse already completed translations."""

        cache = cached or {}
        result: list[TranslationSegment] = []
        for segment in segments:
            translated = cache.get(segment.index)
            if not translated:
                translated = self.translate_one(
                    segment.text,
                    segment.language,
                    segment.duration,
                )
            result.append(
                TranslationSegment(
                    index=segment.index,
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    source_text=segment.text,
                    translated_text=translated,
                    language=segment.language,
                )
            )
        return result
