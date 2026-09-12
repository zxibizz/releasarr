"""Helpers for choosing display values out of a request's localizations."""

from __future__ import annotations

from collections.abc import Sequence

from src.application.interfaces.media_requests import MediaLocalization

# The language Sonarr and Radarr themselves report in, used as the home for
# their values when the metadata provider offered no translation.
DEFAULT_LANGUAGE = "eng"


def merge_default_localization(
    localizations: dict[str, MediaLocalization],
    *,
    title: str | None,
    overview: str | None,
) -> None:
    """Fold the *arr app's own title and overview into the default language."""

    localization = localizations.get(DEFAULT_LANGUAGE)
    if localization is None:
        localizations[DEFAULT_LANGUAGE] = MediaLocalization(title=title, overview=overview)
        return
    if not localization.title:
        localization.title = title
    if not localization.overview:
        localization.overview = overview


class LocalizationPicker:
    """Pick the value to store on a request's own ``title``/``overview``.

    Requests keep every translation, but the columns the list view reads hold a
    single value, so one language has to win. The configured languages are tried
    in order before falling back to any translation at all, and finally to the
    value the *arr app reported.
    """

    def __init__(self, languages: Sequence[str] | None = None) -> None:
        self.languages = tuple(language.lower() for language in languages or ())

    def select(
        self,
        localizations: dict[str, MediaLocalization],
        attribute: str,
        fallback: str | None,
    ) -> str:
        preferred = self._preferred(localizations, attribute)
        if preferred:
            return preferred
        any_value = self._any(localizations, attribute)
        if any_value:
            return any_value
        return fallback or ""

    def _preferred(
        self,
        localizations: dict[str, MediaLocalization],
        attribute: str,
    ) -> str | None:
        for language in self.languages:
            localization = localizations.get(language)
            if not localization:
                continue
            value = getattr(localization, attribute, None)
            if value:
                return value
        return None

    def _any(
        self,
        localizations: dict[str, MediaLocalization],
        attribute: str,
    ) -> str | None:
        for localization in localizations.values():
            value = getattr(localization, attribute, None)
            if value:
                return value
        return None


__all__ = ["DEFAULT_LANGUAGE", "LocalizationPicker", "merge_default_localization"]
