/**
 * The URL base the app is served under, e.g. `/releasarr`, or `''` at the root.
 * nginx writes it into index.html's `<base href>`; with no such tag (tests) the
 * app is at the root.
 */
export function getBasePath(): string {
  if (!document.querySelector('base[href]')) {
    return '';
  }
  return new URL(document.baseURI).pathname.replace(/\/+$/, '');
}
