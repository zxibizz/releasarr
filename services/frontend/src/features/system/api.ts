import { apiRequest } from '@/lib/api/client';
import type { SystemInfo } from '@/types';

export const systemApi = {
  info: (signal?: AbortSignal) => apiRequest<SystemInfo>('/system', { signal }),
};
