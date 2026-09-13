import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ManualReleaseForm } from '@/features/releases/components/ManualReleaseForm';
import { apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const MAGNET = 'magnet:?xt=urn:btih:abc123&dn=Show.S01';
const TORRENT_BYTES = 'd4:spami42ee';
const TORRENT_BASE64 = 'ZDQ6c3BhbWk0MmVl';

const SUBMIT = 'Add release';
const MAGNET_FIELD = 'Magnet link';

/**
 * Mantine's `FileInput` labels the button that opens the picker, so the input
 * the upload has to go through is only reachable through the DOM.
 */
const fileInputOf = (container: HTMLElement): HTMLInputElement => {
  const input = container.querySelector<HTMLInputElement>('input[type="file"]');
  if (!input) {
    throw new Error('no file input rendered');
  }
  return input;
};

const torrentFile = () =>
  new File([TORRENT_BYTES], 'Show.S01.1080p.torrent', { type: 'application/x-bittorrent' });

function renderForm() {
  const onDownloadQueued = vi.fn();
  const rendered = renderWithProviders(
    <ManualReleaseForm requestId="req-1" onDownloadQueued={onDownloadQueued} />,
  );
  return { ...rendered, onDownloadQueued };
}

describe('ManualReleaseForm', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
    vi.mocked(apiRequest).mockResolvedValue({ operation: 'queue_download', status: 'queued' });
  });

  it('has nothing to submit until a file or magnet is supplied', () => {
    renderForm();

    expect(screen.getByRole('button', { name: SUBMIT })).toBeDisabled();
  });

  it('sends a picked torrent file as base64', async () => {
    const { container, onDownloadQueued } = renderForm();

    await userEvent.upload(fileInputOf(container), torrentFile());
    await userEvent.click(screen.getByRole('button', { name: SUBMIT }));

    expect(apiRequest).toHaveBeenCalledWith(
      '/requests/req-1/releases/manual',
      expect.objectContaining({
        method: 'POST',
        body: { torrent_file_base64: TORRENT_BASE64 },
      }),
    );
    expect(onDownloadQueued).toHaveBeenCalled();
  });

  it('sends a pasted magnet link', async () => {
    const { onDownloadQueued } = renderForm();

    await userEvent.type(screen.getByLabelText(MAGNET_FIELD), MAGNET);
    await userEvent.click(screen.getByRole('button', { name: SUBMIT }));

    expect(apiRequest).toHaveBeenCalledWith(
      '/requests/req-1/releases/manual',
      expect.objectContaining({ method: 'POST', body: { magnet_link: MAGNET } }),
    );
    expect(onDownloadQueued).toHaveBeenCalled();
  });

  it('refuses a link that is not a magnet', async () => {
    renderForm();

    await userEvent.type(screen.getByLabelText(MAGNET_FIELD), 'https://example.test/file.torrent');

    expect(screen.getByText('A magnet link must start with "magnet:".')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: SUBMIT })).toBeDisabled();
    expect(apiRequest).not.toHaveBeenCalled();
  });

  it('drops a typed magnet once a file is picked, so only one is sent', async () => {
    const { container } = renderForm();

    await userEvent.type(screen.getByLabelText(MAGNET_FIELD), MAGNET);
    await userEvent.upload(fileInputOf(container), torrentFile());
    await userEvent.click(screen.getByRole('button', { name: SUBMIT }));

    expect(screen.getByLabelText(MAGNET_FIELD)).toHaveValue('');
    expect(apiRequest).toHaveBeenCalledWith(
      '/requests/req-1/releases/manual',
      expect.objectContaining({ body: { torrent_file_base64: TORRENT_BASE64 } }),
    );
  });

  it('keeps the input around when the server rejects the grab', async () => {
    vi.mocked(apiRequest).mockRejectedValue(new Error('Release already registered'));
    const { onDownloadQueued } = renderForm();

    await userEvent.type(screen.getByLabelText(MAGNET_FIELD), MAGNET);
    await userEvent.click(screen.getByRole('button', { name: SUBMIT }));

    expect(await screen.findByText('Release already registered')).toBeInTheDocument();
    expect(screen.getByLabelText(MAGNET_FIELD)).toHaveValue(MAGNET);
    expect(onDownloadQueued).not.toHaveBeenCalled();
  });
});
