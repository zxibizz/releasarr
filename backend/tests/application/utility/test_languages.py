"""Tests for normalising language codes between the providers' two forms."""

from __future__ import annotations

import pytest

from src.application.utility.languages import to_three_letter, to_two_letter


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("ru", "rus"),
        ("RU", "rus"),
        (" en ", "eng"),
        # The UI may report a regional locale, which the language part answers for.
        ("pt-BR", "por"),
        ("pt_br", "por"),
        ("rus", "rus"),
        # A bibliographic code stays as given, since TVDB keys translations by it.
        ("ger", "ger"),
        ("klingon", None),
        ("zz", None),
        ("", None),
    ],
)
def test_widening_to_the_three_letter_form(code: str, expected: str | None) -> None:
    assert to_three_letter(code) == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("rus", "ru"),
        ("ger", "de"),
        ("deu", "de"),
        ("ru", "ru"),
        ("klingon", None),
        ("", None),
    ],
)
def test_narrowing_to_the_two_letter_form(code: str, expected: str | None) -> None:
    assert to_two_letter(code) == expected
