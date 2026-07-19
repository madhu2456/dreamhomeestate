'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import Link from 'next/link';
import { ArrowLeft, Building2, CheckCircle2, Loader2, Mail } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

const schema = z.object({
  email: z.string().email('Enter a valid email address'),
});

type FormData = z.infer<typeof schema>;

export default function ResetRequestPage() {
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  async function onSubmit(data: FormData) {
    setError(null);
    setLoading(true);
    try {
      const res = await fetch('/api/v1/auth/password-reset-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      // API intentionally returns success even for unknown emails
      if (!res.ok && res.status >= 500) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
          typeof body.detail === 'string'
            ? body.detail
            : 'Could not process request. Try again later.'
        );
      }
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-dvh flex-col bg-background">
      <div className="pointer-events-none absolute inset-0 ink-gradient" aria-hidden />
      <header className="relative flex items-center justify-between px-5 py-4 sm:px-8">
        <Link href="/" className="inline-flex items-center gap-2 focus-ring rounded-md">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Building2 className="h-4 w-4" />
          </span>
          <span className="font-display text-lg font-semibold">Dream Home Estate</span>
        </Link>
        <Link
          href="/login"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to sign in
        </Link>
      </header>

      <main className="relative flex flex-1 items-center justify-center px-5 py-10">
        <div className="w-full max-w-[420px]">
          <h1 className="font-display text-3xl font-semibold tracking-tight">Reset password</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Enter the email for your Dream Home Estate agent account. If it exists, we will send reset
            instructions.
          </p>

          <div className="mt-8 rounded-2xl border border-border/80 bg-card p-6 shadow-lift sm:p-8">
            {success ? (
              <div className="text-center">
                <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-accent/15 text-accent">
                  <CheckCircle2 className="h-6 w-6" />
                </span>
                <h2 className="mt-4 font-display text-xl font-semibold">Check your email</h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  If an account matches that address, reset instructions are on the way. Also check
                  spam, and contact your workspace owner if you need help.
                </p>
                <Button asChild className="mt-6 w-full rounded-full bg-accent text-accent-foreground hover:bg-accent/90">
                  <Link href="/login">Return to sign in</Link>
                </Button>
              </div>
            ) : (
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
                  <Label htmlFor="email">Email</Label>
                  <div className="relative">
                    <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id="email"
                      type="email"
                      autoComplete="email"
                      placeholder="you@dreamhome.estate"
                      className={cn(
                        'h-12 rounded-xl pl-10',
                        errors.email && 'border-destructive focus-visible:ring-destructive'
                      )}
                      {...register('email')}
                    />
                  </div>
                  {errors.email && (
                    <p className="text-sm text-destructive">{errors.email.message}</p>
                  )}
                </div>
                <Button
                  type="submit"
                  disabled={loading}
                  className="h-12 w-full rounded-full bg-accent text-accent-foreground hover:bg-accent/90"
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Sending…
                    </>
                  ) : (
                    'Send reset link'
                  )}
                </Button>
              </form>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
