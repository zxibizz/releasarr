import { describe, expect, it } from 'vitest';

import type { ReleaseFile } from '@/types';
import { splitVideoFiles } from '@/utils/files';

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
