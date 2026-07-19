import type { ApiError } from '@/lib/types';

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  cookies?: string;
}

const CSRF_COOKIE_NAMES = ['dhe_csrf', 'res_csrf'] as const;
const MUTATING = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

/**
 * Browser: same-origin (nginx proxies /api → FastAPI).
 * Server Components: call the API container directly (relative /api URLs
 * break inside Docker because Next cannot resolve them to the api service).
 */
function getApiBase(): string {
  if (typeof window !== 'undefined') {
    return '';
  }
  const internal =
    process.env.API_INTERNAL_URL?.replace(/\/$/, '') ||
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ||
    'http://api:8000';
  return internal;
}

function readCookieFromDocument(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function extractCookie(cookieHeader: string, name: string): string | null {
  const match = cookieHeader.match(new RegExp(`(?:^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

/** Read the double-submit CSRF token from document cookies (browser only). */
export function getCsrfToken(): string | null {
  for (const name of CSRF_COOKIE_NAMES) {
    const value = readCookieFromDocument(name);
    if (value) return value;
  }
  return null;
}

function resolveCsrfToken(cookieHeader?: string): string | null {
  if (typeof window !== 'undefined') {
    return getCsrfToken();
  }
  if (cookieHeader) {
    for (const name of CSRF_COOKIE_NAMES) {
      const value = extractCookie(cookieHeader, name);
      if (value) return value;
    }
  }
  return null;
}

/**
 * Ensure a CSRF cookie exists (browser). Safe to call before any mutation.
 * No-ops on the server.
 */
export async function ensureCsrfToken(): Promise<string | null> {
  if (typeof window === 'undefined') {
    return null;
  }
  const existing = getCsrfToken();
  if (existing) return existing;

  try {
    const res = await fetch(buildUrl('/api/v1/auth/csrf'), {
      method: 'GET',
      credentials: 'include',
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    });
    if (!res.ok) return null;
    const data = (await res.json()) as { csrf_token?: string };
    return data.csrf_token ?? getCsrfToken();
  } catch {
    return null;
  }
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
  const base = getApiBase();
  if (!base) {
    return path;
  }
  return `${base}${path.startsWith('/') ? path : `/${path}`}`;
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
  const method = (fetchOptions.method ?? 'GET').toUpperCase();

  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(body && !(body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
    ...(fetchOptions.headers as Record<string, string>),
  };

  if (cookies) {
    headers['Cookie'] = cookies;
  }

  if (MUTATING.has(method) && !headers['X-CSRF-Token']) {
    // Prefer existing cookie; on the browser, refresh if missing
    let csrf = resolveCsrfToken(cookies);
    if (!csrf && typeof window !== 'undefined') {
      csrf = await ensureCsrfToken();
    }
    if (csrf) {
      headers['X-CSRF-Token'] = csrf;
    }
  }

  const init: RequestInit = {
    ...fetchOptions,
    method,
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
