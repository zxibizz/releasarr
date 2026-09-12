import { describe, expect, it } from 'vitest';

import { parseEpisodeFromFile, parseEpisodeFromFilename } from '@/utils/files';

describe('parseEpisodeFromFilename', () => {
  it.each([
    ['Avatar.The.Last.Airbender.S01E01.1080p.BluRay.x264.mkv', 1, 1],
    ['Avatar - s02 e07 - The Blind Bandit.mkv', 2, 7],
    ['Show.Season 2.Episode 5.mkv', 2, 5],
    ['Show.2x05.HDTV.mkv', 2, 5],
    ['Avatar.S03E20.mkv', 3, 20],
  ])('reads %s as S%iE%i', (filename, season, episode) => {
    expect(parseEpisodeFromFilename(filename)).toEqual({ season, episode });
  });

  it('ignores resolutions, codecs and years', () => {
    expect(
      parseEpisodeFromFilename('Avatar.The.Last.Airbender.2005.1080p.1920x1080.x264.DD5.1.mkv'),
    ).toEqual({ season: undefined, episode: undefined });
  });
});

describe('parseEpisodeFromFile', () => {
  it('takes the season from the enclosing folder', () => {
    expect(
      parseEpisodeFromFile({
        name: '05 - The Swamp.mkv',
        path: 'Avatar/Season 2/05 - The Swamp.mkv',
      }),
    ).toEqual({ season: 2, episode: 5 });
  });

  it('prefers the file name over the folder', () => {
    expect(
      parseEpisodeFromFile({ name: 'Avatar.S02E04.mkv', path: 'Avatar/Season 1/Avatar.S02E04.mkv' }),
    ).toEqual({ season: 2, episode: 4 });
  });

  it('handles torrent listings whose name is a relative path with bracketed numbering', () => {
    const location = 'Seihantai na Kimi to Boku S2/Seihantai na Kimi to Boku S2 [07].avi';

    expect(parseEpisodeFromFile({ name: location, path: location })).toEqual({
      season: 2,
      episode: 7,
    });
  });

  it('reports the season alone for a season pack folder', () => {
    expect(
      parseEpisodeFromFile({ name: 'Avatar.1080p.mkv', path: 'Avatar.S02.1080p/Avatar.1080p.mkv' }),
    ).toEqual({ season: 2, episode: undefined });
  });
});
