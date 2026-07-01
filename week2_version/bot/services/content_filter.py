from __future__ import annotations


BLOCKED_WORDS = {
    "мат",
    "спам",
    "тест тест",
    "asdf",
    "qwerty",
}


def validate_text(value: str, min_chars: int) -> tuple[bool, str]:
    text = value.strip()
    lowered = text.lower()
    if len(text) < min_chars:
        return False, f"Ответ должен быть не короче {min_chars} символов."
    if any(word in lowered for word in BLOCKED_WORDS):
        return False, "Текст похож на черновик, спам или содержит недопустимые слова. Переформулируйте, пожалуйста."
    unique_chars = set(lowered.replace(" ", ""))
    if len(unique_chars) < 4:
        return False, "Добавьте больше осмысленного текста."
    return True, ""
