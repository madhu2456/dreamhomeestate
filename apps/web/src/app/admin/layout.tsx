import { redirect } from 'next/navigation';
import Link from 'next/link';
import {
  Building2,
  FileText,
  Home,
  LayoutDashboard,
  Link2,
  LogOut,
  Send,
  Settings,
  Users,
} from 'lucide-react';

import { getCurrentUser } from '@/lib/session';
import { Button } from '@/components/ui/button';
import { Toaster } from '@/components/ui/toaster';

const NAV_ITEMS = [
  { href: '/admin', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { href: '/admin/listings', label: 'Listings', icon: Home },
  { href: '/admin/social-accounts', label: 'Social Accounts', icon: Link2 },
  { href: '/admin/templates', label: 'Content', icon: FileText },
  { href: '/admin/publications', label: 'Publications', icon: Send },
  { href: '/admin/organizations', label: 'Organizations', icon: Building2 },
  { href: '/admin/users', label: 'Users', icon: Users },
  { href: '/admin/settings', label: 'Settings', icon: Settings },
];

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser();

  if (!user) {
    redirect('/login?redirect=/admin');
  }

  return (
    <div className="flex min-h-dvh bg-muted/30">
      <aside className="hidden w-64 shrink-0 border-r border-border/80 bg-primary text-primary-foreground md:flex md:flex-col">
        <div className="flex h-16 items-center gap-2.5 border-b border-white/10 px-5">
          <Link href="/admin" className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-accent-foreground">
              <Building2 className="h-4 w-4" />
            </span>
            <span className="font-display text-lg font-semibold tracking-tight">Dream Home</span>
          </Link>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-primary-foreground/70 transition hover:bg-white/10 hover:text-white"
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="border-t border-white/10 p-3">
          <div className="px-3 py-2">
            <p className="truncate text-sm font-medium">{user.full_name ?? user.email}</p>
            <p className="truncate text-xs text-primary-foreground/50">{user.email}</p>
          </div>
          <div className="mt-1 space-y-1">
            <Button
              variant="ghost"
              className="w-full justify-start gap-3 text-primary-foreground/70 hover:bg-white/10 hover:text-white"
              asChild
            >
              <Link href="/">View public site</Link>
            </Button>
            <form action="/api/v1/auth/logout" method="POST">
              <Button
                variant="ghost"
                className="w-full justify-start gap-3 text-primary-foreground/70 hover:bg-white/10 hover:text-white"
                type="submit"
              >
                <LogOut className="h-4 w-4" />
                Sign out
              </Button>
            </form>
          </div>
        </div>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex h-14 items-center gap-3 border-b border-border bg-background px-4 md:hidden">
          <Link href="/admin" className="flex items-center gap-2 font-display font-semibold">
            <Building2 className="h-5 w-5 text-accent" />
            Dream Home
          </Link>
          <nav className="ml-auto flex items-center gap-1 overflow-x-auto">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
                aria-label={item.label}
              >
                <item.icon className="h-5 w-5" />
              </Link>
            ))}
          </nav>
        </header>
        <main className="flex-1 p-4 md:p-6 lg:p-8">{children}</main>
      </div>
      <Toaster />
    </div>
  );
}
