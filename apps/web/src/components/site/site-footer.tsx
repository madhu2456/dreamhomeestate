import Link from 'next/link';
import { Building2 } from 'lucide-react';

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-primary text-primary-foreground">
      <div className="container-wide px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid gap-10 md:grid-cols-4">
          <div className="md:col-span-2">
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                <Building2 className="h-4 w-4" aria-hidden />
              </span>
              <span className="font-display text-xl font-semibold">Dream Home Estate</span>
            </div>
            <p className="mt-4 max-w-md text-sm leading-relaxed text-primary-foreground/70">
              Discover homes you will love — and for agents, list once then publish live to your
              website, Instagram, and X accounts without the copy-paste chaos.
            </p>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-primary-foreground/50">
              Explore
            </h3>
            <ul className="mt-4 space-y-2.5 text-sm">
              <li>
                <Link href="/listings" className="text-primary-foreground/80 transition hover:text-white">
                  Browse homes
                </Link>
              </li>
              <li>
                <Link href="/#how-it-works" className="text-primary-foreground/80 transition hover:text-white">
                  How it works
                </Link>
              </li>
              <li>
                <Link href="/#for-agents" className="text-primary-foreground/80 transition hover:text-white">
                  For agents
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-primary-foreground/50">
              Workspace
            </h3>
            <ul className="mt-4 space-y-2.5 text-sm">
              <li>
                <Link href="/login" className="text-primary-foreground/80 transition hover:text-white">
                  Sign in
                </Link>
              </li>
              <li>
                <Link href="/admin" className="text-primary-foreground/80 transition hover:text-white">
                  Admin console
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-10 flex flex-col gap-3 border-t border-white/10 pt-6 text-xs text-primary-foreground/50 sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} Dream Home Estate. All rights reserved.</p>
          <p className="font-medium tracking-wide">Your dream home starts here</p>
        </div>
      </div>
    </footer>
  );
}
