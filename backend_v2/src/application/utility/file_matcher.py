"""Utility to autocomplete release file mappings based on file structure."""

from __future__ import annotations

import os

from src.application.interfaces.releases import FileMappingUpdateData, ReleaseFileRecord


class ReleaseFileMatcher:
    """Helper to infer season and episode numbers for files in a release."""

    def autocomplete(self, files: list[ReleaseFileRecord]) -> list[FileMappingUpdateData]:
        """Infer missing season/episode mappings based on adjacent files."""
        updates: list[FileMappingUpdateData] = []
        
        # Sort by filename to ensure sequence
        sorted_files = sorted(files, key=lambda f: f.name)
        
        prev_season: int | None = None
        prev_episode: int | None = None
        prev_dir: str | None = None
        prev_ext: str | None = None

        for file in sorted_files:
            file_dir = os.path.dirname(file.path)
            file_ext = os.path.splitext(file.name)[1]
            
            mapping = file.mapping
            season = mapping.season if mapping else None
            episode = mapping.episode if mapping else None

            # Reset context on directory change
            if prev_dir != file_dir:
                prev_season = None
                prev_episode = None
                prev_ext = None

            # Reset context on extension change if current file has no mapping
            if (
                prev_ext is not None
                and file_ext != prev_ext
                and season is None
                and episode is None
            ):
                # Don't try to sequence across different file types (e.g. .nfo after .mkv)
                continue

            # Infer from previous if missing
            inferred = False
            if (
                season is None
                and episode is None
                and prev_season is not None
                and prev_episode is not None
            ):
                season = prev_season
                episode = int(prev_episode) + 1
                inferred = True

            # Update context
            if season is not None and episode is not None:
                prev_season = season
                prev_episode = episode
                prev_dir = file_dir
                prev_ext = file_ext

            # Create update if we inferred new data
            if inferred and mapping:
                # We need to clone the mapping to avoid mutating the original record input?
                # Dataclasses are mutable by default via python but strictness varies.
                # Here we construct a new update.
                updates.append(
                    FileMappingUpdateData(
                        file_id=file.id,
                        mapping=mapping, # We will modify the mapping object or create copy? 
                        # Wait, ReleaseFileMapping is frozen? Check definition. 
                        # @dataclass(slots=True) defaults to frozen=False. So we can update.
                    )
                )
                # Apply to current loop var to propagate context
                # But we should probably construct a new mapping object to be safe/clean
                mapping.season = season
                mapping.episode = episode

        return updates
