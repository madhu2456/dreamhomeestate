import type { ApiError } from '@/lib/types';

const API_BASE = '';

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  cookies?: string;
}

/**
 * Returns a Cookie header string from the current request context.
 * Use in Server Components only.
 */
export async function getServerCookieHeader(): Promise<string> {
  const { cookies } = await import('next/headers');
  const cookieStore = cookies();
  return cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join('; ');
}

class ApiRequestError extends Error {
  status: number;
  code?: string;
  details?: Record<string, unknown>;

  constructor(message: string, status: number, code?: string, details?: Record<string, unknown>) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function buildUrl(path: string): string {
  return `${API_BASE}${path}`;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as unknown as T;
  }

  const contentType = response.headers.get('content-type') ?? '';

  if (!response.ok) {
    let error: ApiError = { message: 'An unexpected error occurred' };
    if (contentType.includes('application/json')) {
      try {
        const body = await response.json();
        error = {
          message: body.detail ?? body.message ?? 'Request failed',
          code: body.code,
          details: body.details,
        };
      } catch {
        // use default error
      }
    }
    throw new ApiRequestError(error.message, response.status, error.code, error.details);
  }

  if (contentType.includes('application/json')) {
    return response.json() as Promise<T>;
  }

  return response.text() as unknown as T;
}

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { body, cookies, ...fetchOptions } = options;

  const headers: HeadersInit = {
    Accept: 'application/json',
    ...(body && !(body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
    ...(fetchOptions.headers as Record<string, string>),
  };

  if (cookies) {
    (headers as Record<string, string>)['Cookie'] = cookies;
  }

  const init: RequestInit = {
    ...fetchOptions,
    headers,
    credentials: 'include',
    ...(body !== undefined ? { body: body instanceof FormData ? body : JSON.stringify(body) } : {}),
  };

  const url = buildUrl(path);
  const response = await fetch(url, init);

  return handleResponse<T>(response);
}

// Convenience wrappers
export function apiGet<T = unknown>(path: string, options?: RequestOptions): Promise<T> {
  return apiFetch<T>(path, { ...options, method: 'GET' });
}

export function apiPost<T = unknown>(
  path: string,
  body?: unknown,
  options?: RequestOptions
): Promise<T> {
  return apiFetch<T>(path, { ...options, method: 'POST', body });
}

export function apiPut<T = unknown>(
  path: string,
  body?: unknown,
  options?: RequestOptions
): Promise<T> {
  return apiFetch<T>(path, { ...options, method: 'PUT', body });
}

export function apiPatch<T = unknown>(
  path: string,
  body?: unknown,
  options?: RequestOptions
): Promise<T> {
  return apiFetch<T>(path, { ...options, method: 'PATCH', body });
}

export function apiDelete<T = unknown>(path: string, options?: RequestOptions): Promise<T> {
  return apiFetch<T>(path, { ...options, method: 'DELETE' });
}

export { ApiRequestError };
