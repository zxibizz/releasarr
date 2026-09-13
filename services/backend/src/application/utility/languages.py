"""Translation between the 2- and 3-letter language codes the providers use.

TVDB keys its translations by ISO 639-2 (``rus``), TMDB by ISO 639-1 (``ru``),
and the UI asks in whichever form its locale happens to be. Requests store their
localizations under the 3-letter form so movie and series entries stay
interchangeable, which makes that the canonical form here too.
"""

from __future__ import annotations

# Both the terminological and the bibliographic 3-letter form are accepted, since
# either may appear in configuration.
THREE_TO_TWO_LETTER: dict[str, str] = {
    "ara": "ar",
    "bul": "bg",
    "cat": "ca",
    "ces": "cs",
    "cze": "cs",
    "chi": "zh",
    "dan": "da",
    "deu": "de",
    "dut": "nl",
    "ell": "el",
    "eng": "en",
    "est": "et",
    "fas": "fa",
    "fin": "fi",
    "fra": "fr",
    "fre": "fr",
    "ger": "de",
    "gre": "el",
    "heb": "he",
    "hin": "hi",
    "hrv": "hr",
    "hun": "hu",
    "ind": "id",
    "ita": "it",
    "jpn": "ja",
    "kor": "ko",
    "lav": "lv",
    "lit": "lt",
    "nld": "nl",
    "nor": "no",
    "per": "fa",
    "pol": "pl",
    "por": "pt",
    "ron": "ro",
    "rum": "ro",
    "rus": "ru",
    "slk": "sk",
    "slo": "sk",
    "slv": "sl",
    "spa": "es",
    "srp": "sr",
    "swe": "sv",
    "tha": "th",
    "tur": "tr",
    "ukr": "uk",
    "vie": "vi",
    "zho": "zh",
}

TWO_TO_THREE_LETTER: dict[str, str] = {
    "ar": "ara",
    "bg": "bul",
    "ca": "cat",
    "cs": "ces",
    "da": "dan",
    "de": "deu",
    "el": "ell",
    "en": "eng",
    "es": "spa",
    "et": "est",
    "fa": "fas",
    "fi": "fin",
    "fr": "fra",
    "he": "heb",
    "hi": "hin",
    "hr": "hrv",
    "hu": "hun",
    "id": "ind",
    "it": "ita",
    "ja": "jpn",
    "ko": "kor",
    "lt": "lit",
    "lv": "lav",
    "nl": "nld",
    "no": "nor",
    "pl": "pol",
    "pt": "por",
    "ro": "ron",
    "ru": "rus",
    "sk": "slk",
    "sl": "slv",
    "sr": "srp",
    "sv": "swe",
    "th": "tha",
    "tr": "tur",
    "uk": "ukr",
    "vi": "vie",
    "zh": "zho",
}


def to_two_letter(code: str) -> str | None:
    """Narrow a language code to the 2-letter form, or ``None`` if it cannot be."""

    normalized = code.strip().lower()
    if not normalized:
        return None
    if len(normalized) == 2:
        return normalized
    return THREE_TO_TWO_LETTER.get(normalized)


def to_three_letter(code: str) -> str | None:
    """Widen a language code to the 3-letter form, or ``None`` if it cannot be.

    A locale such as ``pt-BR`` is reduced to its language part: releasarr keys
    translations by language alone, so the region carries no meaning here.
    """

    normalized = code.strip().lower().replace("_", "-").split("-")[0]
    if not normalized:
        return None
    if len(normalized) == 2:
        return TWO_TO_THREE_LETTER.get(normalized)
    return normalized if normalized in THREE_TO_TWO_LETTER else None


__all__ = [
    "THREE_TO_TWO_LETTER",
    "TWO_TO_THREE_LETTER",
    "to_three_letter",
    "to_two_letter",
]
