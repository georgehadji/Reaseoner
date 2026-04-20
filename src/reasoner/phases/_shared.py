from __future__ import annotations
import re
from reasoner.models import PipelineState, PerspectiveType
from reasoner.core.constants import JSON_ONLY_FOOTER, TRUNCATION, DEFAULT_SEARCH_RESULTS


def detect_language(text: str) -> str:
    """Simple language detection based on character patterns."""
    text = text.lower()
    sample = text[:TRUNCATION.PROBLEM]

    # Greek (full Greek and Coptic block for better coverage)
    if re.search(r'[\u0370-\u03FF]', sample):
        return "Greek"
    
    # Russian/Cyrillic
    if any(c in text for c in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'):
        return "Russian"
    
    # Arabic
    if any(c in text for c in 'ابتثجحخدذرزسشصضطظعغفقكلمنهوي'):
        return "Arabic"
    
    # Chinese
    if any('\u4e00' <= c <= '\u9fff' for c in text):
        return "Chinese"
    
    # Japanese (Hiragana/Katakana)
    if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in text):
        return "Japanese"
    
    # Korean (Hangul)
    if any('\uac00' <= c <= '\ud7af' for c in text):
        return "Korean"
    
    # Turkish (distinctive characters: ı, ğ, ç, ş — checked first because ü/ö can overlap with German)
    turkish_exclusive = 'ığıçış'
    if any(c in text for c in turkish_exclusive):
        return "Turkish"
    
    # German (exclusive characters: ä, ö, ß; ü is shared with Spanish)
    german_exclusive = 'äöß'
    if any(c in text for c in german_exclusive):
        return "German"
    
    # Spanish (common Spanish-specific characters)
    spanish_chars = 'áéíóúüñ¿¡'
    if any(c in text for c in spanish_chars):
        return "Spanish"
    
    return "English"


def get_language_instruction(state: PipelineState) -> str:
    """Returns the 'Respond in X' instruction line."""
    lang_map = {
        "Greek": "Απάντησε στα Ελληνικά.",
        "Russian": "Ответьте на русском языке.",
        "Arabic": "أجب بالعربية.",
        "Chinese": "用中文回答。",
        "Japanese": "日本語で回答してください。",
        "Korean": "한국어로 답변해 주세요.",
        "Spanish": "Responde en español.",
        "German": "Antworte auf Deutsch.",
        "Turkish": "Türkçe cevap ver.",
    }
    return lang_map.get(state.language, "Respond in English.")


def _followup_context(state: PipelineState) -> str:
    """Build a compact follow-up context block for injection into prompts."""
    if not state.conversation_history:
        return ""
    history_text = ""
    for turn in state.conversation_history[-6:]:
        role = turn.get("role", "user").capitalize()
        content = turn.get("content", "")
        history_text += f"{role}: {_wrap_user_input(content)}\n"
    ctx = f"\n---\nCONVERSATION HISTORY (Turn {state.turn_number}):\n{history_text}"
    if state.previous_synthesis:
        ctx += f"PREVIOUS SYNTHESIS:\n{state.previous_synthesis[:TRUNCATION.LARGE_CONTENT]}\n"
    ctx += "---\n"
    return ctx


def _wrap_user_input(text: str) -> str:
    """Wrap user-controlled text in explicit delimiters."""
    return f"<<<USER_INPUT>>>\n{text}\n<<<END_USER_INPUT>>>"


def _wrap_external_content(text: str) -> str:
    """Wrap external/untrusted content in explicit delimiters."""
    return f"<<<EXTERNAL_CONTENT>>>\n{text}\n<<<END_EXTERNAL_CONTENT>>>"
