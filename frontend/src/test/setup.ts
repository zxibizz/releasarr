import '@testing-library/jest-dom/vitest';

// jsdom does not implement matchMedia, which Mantine uses for responsive styles.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

window.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver;

// jsdom has no layout, so it omits scrollIntoView. Mantine's dropdowns call it
// when highlighting the selected option.
Element.prototype.scrollIntoView = () => {};
