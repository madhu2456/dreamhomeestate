import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PROTECTED_PREFIX = '/admin';
/** Must match API SESSION_COOKIE_NAME (prod: dhe_session, default: res_session). */
const SESSION_COOKIE_NAMES = ['dhe_session', 'res_session'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Protect admin routes — require a real session cookie (not CF/analytics cookies)
  if (pathname.startsWith(PROTECTED_PREFIX)) {
    const hasSession = SESSION_COOKIE_NAMES.some((name) => request.cookies.has(name));

    if (!hasSession) {
      const loginUrl = new URL('/login', request.url);
      loginUrl.searchParams.set('redirect', pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // Already signed in? Skip login form
  if (pathname === '/login' || pathname.startsWith('/login/')) {
    const hasSession = SESSION_COOKIE_NAMES.some((name) => request.cookies.has(name));
    if (hasSession && pathname === '/login') {
      const redirect = request.nextUrl.searchParams.get('redirect') || '/admin';
      // Only allow relative redirects
      const target = redirect.startsWith('/') && !redirect.startsWith('//') ? redirect : '/admin';
      return NextResponse.redirect(new URL(target, request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/admin/:path*', '/login', '/login/:path*'],
};
