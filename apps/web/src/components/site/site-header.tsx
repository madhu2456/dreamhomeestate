'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { Building2, Menu, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const NAV = [
  { href: '/listings', label: 'Homes' },
  { href: '/#how-it-works', label: 'How it works' },
  { href: '/#for-agents', label: 'For agents' },
];

export function SiteHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-border/70 bg-background/85 backdrop-blur-md">
      <div className="container-wide flex h-16 items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Link href="/" className="group flex items-center gap-2.5 focus-ring rounded-md">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm transition-transform group-hover:scale-[1.03]">
            <Building2 className="h-4 w-4" aria-hidden />
          </span>
          <span className="flex flex-col leading-none">
            <span className="font-display text-lg font-semibold tracking-tight">Dream Home Estate</span>
            <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Find your dream home
            </span>
          </span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
          {NAV.map((item) => {
            const active = item.href.startsWith('/#')
              ? false
              : pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'rounded-full px-3.5 py-2 text-sm font-medium transition-colors focus-ring',
                  active
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          <Button variant="ghost" asChild className="text-muted-foreground">
            <Link href="/login">Sign in</Link>
          </Button>
          <Button asChild className="bg-accent text-accent-foreground hover:bg-accent/90 shadow-sm">
            <Link href="/listings">Find a dream home</Link>
          </Button>
        </div>

        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-border md:hidden focus-ring"
          aria-expanded={open}
          aria-controls="mobile-nav"
          aria-label={open ? 'Close menu' : 'Open menu'}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open && (
        <div id="mobile-nav" className="border-t border-border bg-background px-4 py-4 md:hidden">
          <nav className="flex flex-col gap-1" aria-label="Mobile">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-lg px-3 py-3 text-sm font-medium text-foreground hover:bg-muted"
                onClick={() => setOpen(false)}
              >
                {item.label}
              </Link>
            ))}
            <Link
              href="/login"
              className="rounded-lg px-3 py-3 text-sm font-medium text-muted-foreground hover:bg-muted"
              onClick={() => setOpen(false)}
            >
              Sign in
            </Link>
            <Button asChild className="mt-2 bg-accent text-accent-foreground hover:bg-accent/90">
              <Link href="/listings" onClick={() => setOpen(false)}>
                Find a dream home
              </Link>
            </Button>
          </nav>
        </div>
      )}
    </header>
  );
}
