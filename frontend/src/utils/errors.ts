import { ApiError } from '@/lib/api/client';

export interface ErrorInfo {
  title: string;
  description: string;
}

export const getErrorMessage = (error: unknown, fallback: string): string => {
  if (error instanceof ApiError) {
    return error.message || fallback;
  }
  if (error instanceof Error) {
    return error.message || fallback;
  }
  if (typeof error === 'string' && error.trim()) {
    return error;
  }
  return fallback;
};

export const getErrorInfo = (error: unknown, fallback: ErrorInfo): ErrorInfo => ({
  title: fallback.title,
  description: getErrorMessage(error, fallback.description),
});
