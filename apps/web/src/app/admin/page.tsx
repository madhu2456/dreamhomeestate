import Link from 'next/link';
import {
  ArrowRight,
  Building2,
  FileText,
  Home,
  Link2,
  Send,
  Settings,
  Users,
} from 'lucide-react';

import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const SECTIONS = [
  {
    href: '/admin/listings',
    title: 'Listings',
    description: 'Create inventory, upload media, and publish to the public site.',
    icon: Home,
  },
  {
    href: '/admin/social-accounts',
    title: 'Social accounts',
    description: 'Connect live Instagram and X accounts for multi-profile distribution.',
    icon: Link2,
  },
  {
    href: '/admin/templates',
    title: 'Content templates',
    description: 'Write platform-aware captions with Jinja variables from each listing.',
    icon: FileText,
  },
  {
    href: '/admin/publications',
    title: 'Publications',
    description: 'Approve campaigns, track jobs, retry failures, and review outcomes.',
    icon: Send,
  },
  {
    href: '/admin/organizations',
    title: 'Organizations',
    description: 'Manage workspaces, membership, and multi-tenant boundaries.',
    icon: Building2,
  },
  {
    href: '/admin/users',
    title: 'Users',
    description: 'Invite teammates and control owner, admin, editor, and viewer roles.',
    icon: Users,
  },
  {
    href: '/admin/settings',
    title: 'Settings',
    description: 'Organization defaults, branding, and integration preferences.',
    icon: Settings,
  },
];

export default function AdminDashboardPage() {
  return (
    <div className="space-y-8">
      <div className="rounded-2xl border border-border/80 bg-card p-6 shadow-card sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">
          Dream Home Estate
        </p>
        <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
          Agent workspace
        </h1>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          Manage dream-home listings, connect live Instagram and X accounts, and publish campaigns
          across every profile.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            href="/admin/listings/new"
            className="inline-flex h-10 items-center rounded-full bg-accent px-5 text-sm font-medium text-accent-foreground transition hover:bg-accent/90"
          >
            New listing
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
          <Link
            href="/admin/social-accounts"
            className="inline-flex h-10 items-center rounded-full border border-border bg-background px-5 text-sm font-medium transition hover:bg-muted"
          >
            Connect accounts
          </Link>
          <Link
            href="/"
            className="inline-flex h-10 items-center rounded-full px-5 text-sm font-medium text-muted-foreground transition hover:text-foreground"
          >
            View public site
          </Link>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {SECTIONS.map((section) => (
          <Link key={section.href} href={section.href} className="group">
            <Card className="h-full border-border/80 shadow-card transition duration-300 group-hover:-translate-y-0.5 group-hover:border-accent/30 group-hover:shadow-soft">
              <CardHeader className="space-y-3">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                  <section.icon className="h-5 w-5" />
                </span>
                <div>
                  <CardTitle className="font-display text-xl tracking-tight group-hover:text-accent">
                    {section.title}
                  </CardTitle>
                  <CardDescription className="mt-1.5 leading-relaxed">
                    {section.description}
                  </CardDescription>
                </div>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
