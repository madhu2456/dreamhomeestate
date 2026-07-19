'use client';

import { Suspense, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  Building2,
  CheckCircle2,
  Eye,
  EyeOff,
  Home,
  Instagram,
  Loader2,
  Lock,
  Mail,
  Twitter,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

const loginSchema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});

type LoginForm = z.infer<typeof loginSchema>;

function LoginFormInner() {
  const searchParams = useSearchParams();
  const redirect = searchParams.get('redirect') ?? '/admin';

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  async function onSubmit(data: LoginForm) {
    setError(null);
    setLoading(true);

    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
        credentials: 'include',
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({} as Record<string, unknown>));
        const detail = body.detail;
        let message =
          typeof detail === 'string'
            ? detail
            : Array.isArray(detail)
              ? detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join(', ')
              : typeof body.message === 'string'
                ? body.message
                : '';
        if (!message) {
          message =
            res.status >= 500
              ? 'Sign-in is temporarily unavailable. Please try again in a moment.'
              : 'Invalid email or password';
        }
        throw new Error(message);
      }

      // Full navigation so the session cookie is always sent on the next request.
      // Soft router.push can race with cookie commit / Server Component auth.
      const target =
        redirect.startsWith('/') && !redirect.startsWith('//') ? redirect : '/admin';
      window.location.assign(target);
      return;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed. Please try again.');
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      {/* Brand panel */}
      <aside className="relative hidden overflow-hidden bg-primary text-primary-foreground lg:flex lg:flex-col">
        <div className="pointer-events-none absolute inset-0 surface-grid opacity-20" aria-hidden />
        <div
          className="pointer-events-none absolute -right-20 top-20 h-72 w-72 rounded-full bg-accent/30 blur-3xl"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute -left-16 bottom-10 h-64 w-64 rounded-full bg-white/10 blur-3xl"
          aria-hidden
        />

        <div className="relative flex flex-1 flex-col justify-between p-10 xl:p-14">
          <Link href="/" className="inline-flex items-center gap-3 self-start">
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent text-accent-foreground shadow-sm">
              <Building2 className="h-5 w-5" />
            </span>
            <span>
              <span className="block font-display text-xl font-semibold tracking-tight">
                Dream Home Estate
              </span>
              <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-primary-foreground/60">
                Agent workspace
              </span>
            </span>
          </Link>

          <div className="max-w-md">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
              Welcome back
            </p>
            <h1 className="mt-3 font-display text-4xl font-semibold leading-tight tracking-tight xl:text-5xl">
              Manage dream homes.
              <span className="mt-2 block text-primary-foreground/75">
                Publish them everywhere.
              </span>
            </h1>
            <p className="mt-5 text-base leading-relaxed text-primary-foreground/70">
              Sign in to list properties, connect Instagram and X accounts, and run live
              multi-account campaigns for Dream Home Estate.
            </p>

            <ul className="mt-8 space-y-3">
              {[
                'Create listings once for web and social',
                'Connect multiple live Instagram & X accounts',
                'Approve campaigns with retries and audit trails',
              ].map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm text-primary-foreground/85">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs text-primary-foreground/55">
            <span className="inline-flex items-center gap-1.5">
              <Home className="h-3.5 w-3.5" /> Listings
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Instagram className="h-3.5 w-3.5" /> Instagram
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Twitter className="h-3.5 w-3.5" /> X
            </span>
          </div>
        </div>
      </aside>

      {/* Form panel */}
      <div className="relative flex flex-col bg-background">
        <div className="pointer-events-none absolute inset-0 ink-gradient opacity-80 lg:opacity-100" aria-hidden />
        <div className="relative flex flex-1 flex-col">
          <div className="flex items-center justify-between px-5 py-4 sm:px-8 lg:px-10">
            <Link
              href="/"
              className="inline-flex items-center gap-2 rounded-md text-sm font-medium text-muted-foreground transition hover:text-foreground focus-ring lg:invisible"
            >
              <Building2 className="h-4 w-4 text-accent" />
              Dream Home Estate
            </Link>
            <Link
              href="/listings"
              className="text-sm font-medium text-muted-foreground transition hover:text-accent focus-ring rounded-md"
            >
              Browse homes
            </Link>
          </div>

          <div className="flex flex-1 items-center justify-center px-5 py-8 sm:px-8 lg:px-10">
            <div className="w-full max-w-[420px]">
              <div className="mb-8">
                <h2 className="font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
                  Sign in
                </h2>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  Enter your agent credentials to open the Dream Home Estate workspace.
                </p>
              </div>

              <div className="rounded-2xl border border-border/80 bg-card p-6 shadow-lift sm:p-8">
                <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
                  {error && (
                    <div
                      role="alert"
                      className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
                    >
                      {error}
                    </div>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-foreground">
                      Email
                    </Label>
                    <div className="relative">
                      <Mail
                        className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                        aria-hidden
                      />
                      <Input
                        id="email"
                        type="email"
                        autoComplete="email"
                        placeholder="you@dreamhome.estate"
                        className={cn(
                          'h-12 rounded-xl border-border/80 bg-background pl-10 text-base sm:text-sm',
                          errors.email && 'border-destructive focus-visible:ring-destructive'
                        )}
                        {...register('email')}
                        aria-invalid={!!errors.email}
                        aria-describedby={errors.email ? 'email-error' : undefined}
                      />
                    </div>
                    {errors.email && (
                      <p id="email-error" className="text-sm text-destructive">
                        {errors.email.message}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between gap-3">
                      <Label htmlFor="password" className="text-foreground">
                        Password
                      </Label>
                      <Link
                        href="/login/reset-request"
                        className="text-sm font-medium text-muted-foreground underline-offset-4 transition hover:text-accent hover:underline"
                      >
                        Forgot password?
                      </Link>
                    </div>
                    <div className="relative">
                      <Lock
                        className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                        aria-hidden
                      />
                      <Input
                        id="password"
                        type={showPassword ? 'text' : 'password'}
                        autoComplete="current-password"
                        placeholder="Enter your password"
                        className={cn(
                          'h-12 rounded-xl border-border/80 bg-background pl-10 pr-12 text-base sm:text-sm',
                          errors.password && 'border-destructive focus-visible:ring-destructive'
                        )}
                        {...register('password')}
                        aria-invalid={!!errors.password}
                        aria-describedby={errors.password ? 'password-error' : undefined}
                      />
                      <button
                        type="button"
                        className="absolute right-2 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-lg text-muted-foreground transition hover:bg-muted hover:text-foreground focus-ring"
                        onClick={() => setShowPassword((v) => !v)}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                    {errors.password && (
                      <p id="password-error" className="text-sm text-destructive">
                        {errors.password.message}
                      </p>
                    )}
                  </div>

                  <Button
                    type="submit"
                    className="h-12 w-full rounded-full bg-accent text-base font-medium text-accent-foreground shadow-sm hover:bg-accent/90"
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Signing in…
                      </>
                    ) : (
                      'Sign in to workspace'
                    )}
                  </Button>
                </form>
              </div>

              <p className="mt-6 text-center text-sm text-muted-foreground">
                Looking for a place to live?{' '}
                <Link
                  href="/listings"
                  className="font-medium text-foreground underline-offset-4 transition hover:text-accent hover:underline"
                >
                  Browse dream homes
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function LoginSkeleton() {
  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <div className="hidden bg-primary lg:block" />
      <div className="flex items-center justify-center p-8">
        <div className="w-full max-w-[420px] space-y-4">
          <div className="h-10 w-48 animate-pulse rounded-lg bg-muted" />
          <div className="h-4 w-full animate-pulse rounded bg-muted" />
          <div className="h-64 animate-pulse rounded-2xl bg-muted" />
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginSkeleton />}>
      <LoginFormInner />
    </Suspense>
  );
}
