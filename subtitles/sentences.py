"""Restore Uzbek sentence punctuation without changing recognized words or timing."""

from __future__ import annotations

import re
from dataclasses import replace
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable, TypeVar


T = TypeVar("T")
END = ".!?…"
PUNCT = ",;:.!?…"
LITERARY_FORMS = {
    "qivotti": "qilyapti", "qivossan": "qilyapsan", "qivoman": "qilyapman",
    "kevotti": "kelyapti", "kevossan": "kelyapsan", "kevoman": "kelyapman",
    "ketvotti": "ketyapti", "borvotti": "boryapti", "bo'votti": "bo'lyapti",
    "qanaqa": "qanday", "shunaqa": "shunday", "bunaqa": "bunday",
    "manga": "menga", "sanga": "senga", "bilmiyman": "bilmayman",
}


def standardize_literary(words: list[T]) -> list[T]:
    """Normalize common colloquial Uzbek forms without changing word timing or count."""
    result = []
    for word in words:
        match = re.fullmatch(r"([^\wʻʼ‘’']*)([\wʻʼ‘’']+)([^\wʻʼ‘’']*)", word.text)
        if not match:
            result.append(word)
            continue
        leading, source, trailing = match.groups()
        normalized = source.casefold().translate(str.maketrans("ʻʼ‘’", "''''"))
        replacement = LITERARY_FORMS.get(normalized)
        if replacement:
            if source.isupper():
                replacement = replacement.upper()
            elif source[:1].isupper():
                replacement = replacement.capitalize()
            result.append(replace(word, text=leading + replacement + trailing))
        else:
            result.append(word)
    return result


def _lexical(token: str) -> str:
    token = token.replace("’", "'").replace("‘", "'").replace("ʻ", "'").replace("ʼ", "'")
    return re.sub(r"[^\w']", "", token.casefold())


def _tokens(text: str) -> list[str]:
    parts = text.split()
    result: list[str] = []
    for part in parts:
        if part and all(char in PUNCT for char in part) and result:
            result[-1] += part
        else:
            result.append(part)
    return result


def _transfer(words: list[T], prediction: str, final_chunk: bool,
              initial_capital: bool) -> list[T]:
    """Copy only case and punctuation from matching model tokens."""
    predicted = _tokens(prediction)
    source = [_lexical(w.text) for w in words]
    target = [_lexical(token) for token in predicted]
    matcher = SequenceMatcher(None, source, target, autojunk=False)
    matches = [(i + offset, j + offset) for i, j, length in matcher.get_matching_blocks()
               for offset in range(length)]
    if not source or len(matches) / len(source) < .7:
        return words
    result = list(words)
    for i, j in matches:
        original = words[i].text
        candidate = predicted[j]
        if not source[i] or not target[j]:
            continue
        # Never replace the ASR spelling or introduce a different-language word.
        if candidate[:1].isupper() and original[:1].islower() and (i > 0 or initial_capital):
            original = original[:1].upper() + original[1:]
        suffix = re.search(r"[,.!?;:…]+$", candidate)
        if suffix and (final_chunk or i < len(words) - 1):
            existing = re.search(r"[,.!?;:…]+$", original)
            if not existing:
                original += suffix.group()
        result[i] = replace(words[i], text=original)
    return result


def _capitalize_first(word: T) -> T:
    value = word.text
    return replace(word, text=value[:1].upper() + value[1:]) if value[:1].islower() else word


def restore_sentences(words: list[T], correct: Callable[[str], str] | None = None,
                      strong_pause: float = 1.1) -> list[T]:
    """Add model punctuation where safe; fall back to strong pauses and sentence casing."""
    if not words:
        return []
    result: list[T] = []
    chunk: list[T] = []
    for word in words:
        if chunk and (word.start - chunk[-1].end >= strong_pause or len(chunk) >= 30):
            natural_break = word.start - chunk[-1].end >= strong_pause
            begin_sentence = not result or result[-1].text.rstrip().endswith(tuple(END))
            result.extend(_restore_chunk(chunk, correct, natural_break, begin_sentence))
            chunk = []
        chunk.append(word)
    begin_sentence = not result or result[-1].text.rstrip().endswith(tuple(END))
    result.extend(_restore_chunk(chunk, correct, True, begin_sentence))
    for index, word in enumerate(result):
        if index == 0 or result[index - 1].text.rstrip().endswith(tuple(END)):
            result[index] = _capitalize_first(word)
    return result


def _restore_chunk(words: list[T], correct: Callable[[str], str] | None,
                   natural_break: bool, begin_sentence: bool) -> list[T]:
    result = list(words)
    if correct:
        try:
            result = _transfer(words, correct(" ".join(w.text.strip() for w in words)),
                               natural_break, begin_sentence)
        except Exception:
            # A text model failure must not discard an otherwise usable transcript.
            pass
    if natural_break and result and not result[-1].text.rstrip().endswith(tuple(END + ",;:")):
        result[-1] = replace(result[-1], text=result[-1].text.rstrip() + ".")
    return result


def local_corrector(root: Path) -> Callable[[str], str] | None:
    """Load the optional local Uzbek ByT5 model only when fully installed."""
    directory = root / "models" / "rubai-transcript"
    if not (directory / "model.safetensors").is_file():
        return None
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    import torch

    tokenizer = AutoTokenizer.from_pretrained(str(directory), local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(str(directory), local_files_only=True)
    model.eval()

    def correct(text: str) -> str:
        inputs = tokenizer("correct: " + text, return_tensors="pt")
        with torch.inference_mode():
            ids = model.generate(**inputs, max_new_tokens=512, num_beams=1)
        return tokenizer.batch_decode(ids, skip_special_tokens=True)[0]

    return correct
