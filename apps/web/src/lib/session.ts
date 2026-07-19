import { cookies } from 'next/headers';
import { apiGet } from '@/lib/api';
import type { User } from '@/lib/types';

/**
 * Reads the current authenticated user by forwarding the session cookie to the API.
 * Returns null if the user is not authenticated.
 * Use in Server Components only.
 */
export async function getCurrentUser(): Promise<User | null> {
  try {
    const cookieStore = cookies();
    const cookieHeader = cookieStore
      .getAll()
      .map((c) => `${c.name}=${c.value}`)
      .join('; ');

    if (!cookieHeader) {
      return null;
    }

    const user = await apiGet<User>('/api/v1/auth/me', {
      cookies: cookieHeader,
    });

    return user;
  } catch {
    return null;
  }
}

/**
 * Checks if the request includes a session cookie.
 * Fast check suitable for middleware; does not validate the session.
 */
export function hasSessionCookie(): boolean {
  try {
    const cookieStore = cookies();
    return cookieStore.getAll().length > 0;
  } catch {
    return false;
  }
}
