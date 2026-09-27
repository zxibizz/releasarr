import { afterEach, describe, expect, it } from 'vitest';

import { getBasePath } from '@/lib/basePath';

describe('getBasePath', () => {
  afterEach(() => {
    document.querySelectorAll('base').forEach((base) => base.remove());
  });

  it('is the root when index.html carries no base tag', () => {
    expect(getBasePath()).toBe('');
  });

  it('is the root for the unrewritten tag', () => {
    document.head.insertAdjacentHTML('afterbegin', '<base href="/" />');
    expect(getBasePath()).toBe('');
  });

  it('is the path nginx wrote into the tag, without its trailing slash', () => {
    document.head.insertAdjacentHTML('afterbegin', '<base href="/media/releasarr/" />');
    expect(getBasePath()).toBe('/media/releasarr');
  });
});
