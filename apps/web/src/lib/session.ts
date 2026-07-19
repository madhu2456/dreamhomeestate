import { cookies } from 'next/headers';
import { apiGet } from '@/lib/api';
import type { Membership, MembershipRole, User } from '@/lib/types';

/** Cookie names used by the API (prod default + settings default). */
export const SESSION_COOKIE_NAMES = ['dhe_session', 'res_session'] as const;

interface MeResponse {
  user: {
    id: string;
    email: string;
    full_name: string;
    is_active: boolean;
  };
  memberships: Array<{
    id: string;
    email: string;
    full_name: string;
    role: MembershipRole;
    is_active: boolean;
    joined_at?: string;
  }>;
}

/**
 * Reads the current authenticated user by forwarding the session cookie to the API.
 * Returns null if the user is not authenticated.
 * Use in Server Components only.
 */
export async function getCurrentUser(): Promise<User | null> {
  try {
    const cookieStore = cookies();
    const sessionCookie = SESSION_COOKIE_NAMES.map((name) => cookieStore.get(name)).find(Boolean);

    // Prefer the real session cookie; fall back to forwarding all cookies
    // so Cloudflare / other cookies don't block when session name differs.
    const cookieHeader = sessionCookie
      ? `${sessionCookie.name}=${sessionCookie.value}`
      : cookieStore
          .getAll()
          .map((c) => `${c.name}=${c.value}`)
          .join('; ');

    if (!cookieHeader) {
      return null;
    }

    // API returns MeResponse { user, memberships }, not a flat User
    const me = await apiGet<MeResponse>('/api/v1/auth/me', {
      cookies: cookieHeader,
      cache: 'no-store',
    });

    if (!me?.user?.id) {
      return null;
    }

    const memberships: Membership[] = (me.memberships ?? []).map((m) => ({
      organization: {
        id: m.id,
        name: m.full_name || m.email || 'Organization',
        slug: m.id,
      },
      role: m.role,
    }));

    return {
      id: me.user.id,
      email: me.user.email,
      full_name: me.user.full_name,
      is_active: me.user.is_active,
      memberships,
    };
  } catch {
    return null;
  }
}

/**
 * Checks if the request includes a known session cookie.
 * Fast check suitable for middleware; does not validate the session.
 */
export function hasSessionCookie(): boolean {
  try {
    const cookieStore = cookies();
    return SESSION_COOKIE_NAMES.some((name) => Boolean(cookieStore.get(name)));
  } catch {
    return false;
  }
}
