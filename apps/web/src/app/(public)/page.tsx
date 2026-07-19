import Link from 'next/link';
import {
  ArrowRight,
  Building2,
  CheckCircle2,
  Heart,
  Home,
  Instagram,
  Megaphone,
  Share2,
  Sparkles,
  Twitter,
} from 'lucide-react';

import { ListingCard } from '@/components/site/listing-card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiGet } from '@/lib/api';
import type { Listing } from '@/lib/types';

export const metadata = {
  title: 'Dream Home Estate — Find the home you have been dreaming of',
  description:
    'Browse beautiful homes for sale and rent with Dream Home Estate. Agents list once and publish live to Instagram and X.',
};

async function getFeaturedListings(): Promise<Listing[]> {
  try {
    const listings = await apiGet<Listing[]>('/api/v1/public/listings?limit=6');
    return listings ?? [];
  } catch {
    return [];
  }
}

const STEPS = [
  {
    title: 'Discover dream homes',
    body: 'Browse curated listings with photos, pricing, and neighborhood details — ready when you are.',
    icon: Home,
  },
  {
    title: 'Connect with agents',
    body: 'Reach listing contacts by phone, email, or WhatsApp and take the next step with confidence.',
    icon: Heart,
  },
  {
    title: 'Agents publish everywhere',
    body: 'Dream Home Estate teams list once, then share live to the website plus Instagram and X accounts.',
    icon: Megaphone,
  },
];

const FEATURES = [
  {
    title: 'Homes that feel personal',
    body: 'Every listing highlights the details that matter — beds, baths, location, and the story of the space.',
    icon: Home,
  },
  {
    title: 'Share across every feed',
    body: 'Agents distribute the same home to multiple Instagram and X accounts from one campaign.',
    icon: Share2,
  },
  {
    title: 'Captions that fit each platform',
    body: 'Templates adapt copy for Instagram captions and X posts so every channel stays on brand.',
    icon: Sparkles,
  },
  {
    title: 'Trusted live publishing',
    body: 'Official Instagram and X APIs only — with approvals, retries, and a clear status for every post.',
    icon: CheckCircle2,
  },
];

export default async function HomePage() {
  const featured = await getFeaturedListings();

  return (
    <main>
      {/* Hero */}
      <section className="relative overflow-hidden ink-gradient">
        <div className="pointer-events-none absolute inset-0 surface-grid opacity-40" aria-hidden />
        <div className="container-wide relative grid items-center gap-12 px-4 pb-16 pt-14 sm:px-6 sm:pb-20 sm:pt-20 lg:grid-cols-12 lg:gap-10 lg:px-8 lg:pb-28 lg:pt-24">
          <div className="lg:col-span-6">
            <Badge className="mb-5 border-0 bg-accent/15 text-accent hover:bg-accent/20">
              Dream Home Estate
            </Badge>
            <h1 className="font-display text-4xl font-semibold leading-[1.08] tracking-tight text-foreground sm:text-5xl lg:text-[3.4rem]">
              Find the home
              <span className="mt-2 block text-accent">you have been dreaming of.</span>
            </h1>
            <p className="mt-6 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg">
              Welcome to Dream Home Estate — a modern marketplace for beautiful homes, and a
              workspace for agents who list once and publish live to their website, Instagram, and
              X accounts.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Button
                asChild
                size="lg"
                className="h-12 rounded-full bg-accent px-7 text-base text-accent-foreground hover:bg-accent/90 shadow-soft"
              >
                <Link href="/listings">
                  Explore dream homes
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="h-12 rounded-full border-border bg-white/60 px-7 text-base backdrop-blur"
              >
                <Link href="/login">Agent workspace</Link>
              </Button>
            </div>
            <div className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-3 text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-2">
                <Home className="h-4 w-4 text-accent" aria-hidden />
                Homes for sale &amp; rent
              </span>
              <span className="inline-flex items-center gap-2">
                <Instagram className="h-4 w-4 text-accent" aria-hidden />
                Instagram
              </span>
              <span className="inline-flex items-center gap-2">
                <Twitter className="h-4 w-4 text-accent" aria-hidden />
                X / Twitter
              </span>
            </div>
          </div>

          <div className="relative lg:col-span-6">
            <div
              className="absolute -inset-6 rounded-[2rem] bg-gradient-to-br from-accent/20 via-transparent to-primary/10 blur-2xl"
              aria-hidden
            />
            <div className="relative overflow-hidden rounded-[1.75rem] border border-border/70 bg-card shadow-lift">
              <div className="flex items-center justify-between border-b border-border/70 bg-muted/50 px-5 py-3">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-accent" />
                  <span className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                    Dream Home campaign
                  </span>
                </div>
                <span className="text-xs font-medium text-emerald-700">3 accounts ready</span>
              </div>
              <div className="space-y-4 p-5 sm:p-6">
                <div className="rounded-xl border border-border bg-background p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                    Featured home
                  </p>
                  <p className="mt-1 font-display text-xl font-semibold">Willow Creek Villa · 4 bed</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Austin, TX · $875,000 · For Sale
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
                  {[
                    { platform: 'Instagram', handle: '@dreamhome.estate', status: 'Queued' },
                    { platform: 'Instagram', handle: '@dreamhome.rentals', status: 'Queued' },
                    { platform: 'X', handle: '@DreamHomeEstate', status: 'Queued' },
                  ].map((row) => (
                    <div
                      key={row.handle}
                      className="rounded-xl border border-border/80 bg-white p-3 shadow-sm"
                    >
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                        {row.platform}
                      </p>
                      <p className="mt-1 truncate text-sm font-medium">{row.handle}</p>
                      <p className="mt-2 text-xs font-medium text-accent">{row.status}</p>
                    </div>
                  ))}
                </div>
                <div className="rounded-xl bg-primary px-4 py-3 text-sm text-primary-foreground">
                  <span className="font-medium">One listing.</span>
                  <span className="text-primary-foreground/70">
                    {' '}
                    Shared to every Dream Home Estate channel — website, Instagram, and X.
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Featured listings */}
      <section className="section-pad border-t border-border/70 bg-background">
        <div className="container-wide">
          <div className="mb-10 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
                Featured homes
              </p>
              <h2 className="mt-2 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
                Places you will love coming home to
              </h2>
              <p className="mt-2 max-w-xl text-muted-foreground">
                Explore the latest Dream Home Estate listings — carefully presented for buyers, and
                ready for agents to share across social.
              </p>
            </div>
            <Button asChild variant="outline" className="rounded-full">
              <Link href="/listings">
                View all homes
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>

          {featured.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border bg-muted/40 px-6 py-16 text-center">
              <Building2 className="mx-auto h-10 w-10 text-muted-foreground/60" />
              <h3 className="mt-4 font-display text-xl font-semibold">New dream homes are on the way</h3>
              <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
                When Dream Home Estate agents publish inventory, it will appear here for buyers —
                and can be shared live to Instagram and X.
              </p>
              <Button
                asChild
                className="mt-6 rounded-full bg-accent text-accent-foreground hover:bg-accent/90"
              >
                <Link href="/login">Agent sign in</Link>
              </Button>
            </div>
          ) : (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {featured.map((listing) => (
                <ListingCard key={listing.id} listing={listing} />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="section-pad border-t border-border/70 bg-muted/40">
        <div className="container-wide">
          <div className="mx-auto max-w-2xl text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
              How Dream Home Estate works
            </p>
            <h2 className="mt-2 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
              From first look to every feed
            </h2>
            <p className="mt-3 text-muted-foreground">
              Buyers discover the right home. Agents keep one listing and publish it everywhere it
              needs to be seen.
            </p>
          </div>
          <ol className="mt-12 grid gap-6 md:grid-cols-3">
            {STEPS.map((step, index) => (
              <li
                key={step.title}
                className="relative rounded-2xl border border-border/80 bg-card p-6 shadow-card"
              >
                <div className="mb-5 flex items-center justify-between">
                  <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                    <step.icon className="h-5 w-5" aria-hidden />
                  </span>
                  <span className="font-display text-3xl font-semibold text-border">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                </div>
                <h3 className="font-display text-xl font-semibold tracking-tight">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* For agents */}
      <section id="for-agents" className="section-pad border-t border-border/70">
        <div className="container-wide grid items-center gap-12 lg:grid-cols-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
              For Dream Home agents
            </p>
            <h2 className="mt-2 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
              List once. Share the dream everywhere.
            </h2>
            <p className="mt-4 text-muted-foreground leading-relaxed">
              Dream Home Estate gives brokerages a public showcase for buyers and a live publishing
              engine for Instagram and X. Connect multiple accounts, approve a campaign, and let
              every destination post independently.
            </p>
            <ul className="mt-8 space-y-3">
              {[
                'Multiple Instagram + X accounts per organization',
                'Home-first listing pages with photos and contact CTAs',
                'Approval, retry, and cancel controls for every post',
                'Encrypted OAuth credentials and full audit history',
              ].map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            <Button asChild className="mt-8 rounded-full bg-primary px-6">
              <Link href="/login">
                Open agent workspace
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {FEATURES.map((feature) => (
              <div
                key={feature.title}
                className="rounded-2xl border border-border/80 bg-card p-5 shadow-card transition hover:border-accent/25 hover:shadow-soft"
              >
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/12 text-accent">
                  <feature.icon className="h-5 w-5" aria-hidden />
                </span>
                <h3 className="mt-4 font-display text-lg font-semibold tracking-tight">
                  {feature.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{feature.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA band */}
      <section className="border-t border-border/70 bg-primary text-primary-foreground">
        <div className="container-wide flex flex-col items-start justify-between gap-6 px-4 py-14 sm:px-6 sm:py-16 lg:flex-row lg:items-center lg:px-8">
          <div className="max-w-2xl">
            <h2 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">
              Your dream home is closer than you think
            </h2>
            <p className="mt-3 text-primary-foreground/70">
              Browse Dream Home Estate listings today — or sign in as an agent to list once and
              publish everywhere.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button
              asChild
              size="lg"
              className="h-12 rounded-full bg-accent px-7 text-accent-foreground hover:bg-accent/90"
            >
              <Link href="/listings">Browse homes</Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="h-12 rounded-full border-white/20 bg-transparent px-7 text-primary-foreground hover:bg-white/10 hover:text-white"
            >
              <Link href="/login">Agent sign in</Link>
            </Button>
          </div>
        </div>
      </section>
    </main>
  );
}
