import { describe, expect, it } from 'vitest';

import type { ReleaseFile } from '@/types';
import { commonRootFolder, splitVideoFiles, withoutRootFolder } from '@/utils/files';

describe('splitVideoFiles', () => {
  const file = (name: string): ReleaseFile => ({ id: name, name, size: 1, path: name });

  it('separates videos from everything else and sorts both by name', () => {
    const { video, other } = splitVideoFiles([
      file('Show.S01E10.mkv'),
      file('readme.txt'),
      file('Show.S01E09.mkv'),
      file('Show.S01E09.srt'),
      file('Show.S01E01.mp4'),
    ]);

    expect(video.map((entry) => entry.name)).toEqual([
      'Show.S01E01.mp4',
      'Show.S01E09.mkv',
      'Show.S01E10.mkv',
    ]);
    expect(other.map((entry) => entry.name)).toEqual(['readme.txt', 'Show.S01E09.srt']);
  });
});

describe('commonRootFolder', () => {
  const file = (name: string): ReleaseFile => ({ id: name, name, size: 1, path: name });

  it('is the folder every file of a pack sits in', () => {
    expect(
      commonRootFolder([
        file('Show.S02.1080p/Season 1/Show.S01E01.mkv'),
        file('Show.S02.1080p/Season 1/Show.S01E02.mkv'),
      ]),
    ).toBe('Show.S02.1080p');
  });

  it('is nothing when the files sit at the top of the torrent', () => {
    expect(commonRootFolder([file('Show.S02E01.mkv'), file('Show.S02E02.mkv')])).toBeNull();
  });

  it('is nothing when one file is outside the folder the rest share', () => {
    expect(
      commonRootFolder([file('Show.S02.1080p/Show.S02E01.mkv'), file('readme.txt')]),
    ).toBeNull();
  });

  it('is nothing for a release with no files', () => {
    expect(commonRootFolder([])).toBeNull();
  });
});

describe('withoutRootFolder', () => {
  it('drops the folder and the separator in front of the rest of the path', () => {
    expect(withoutRootFolder('Show.S02.1080p/Season 1/Show.S01E01.mkv', 'Show.S02.1080p')).toBe(
      'Season 1/Show.S01E01.mkv',
    );
  });

  it('leaves a name that is not inside that folder alone', () => {
    expect(withoutRootFolder('readme.txt', 'Show.S02.1080p')).toBe('readme.txt');
    expect(withoutRootFolder('Show.S02.1080p.mkv', 'Show.S02.1080p')).toBe('Show.S02.1080p.mkv');
  });

  it('leaves every name alone when the release has no shared folder', () => {
    expect(withoutRootFolder('Show.S02.1080p/Show.S02E01.mkv', null)).toBe(
      'Show.S02.1080p/Show.S02E01.mkv',
    );
  });
});
