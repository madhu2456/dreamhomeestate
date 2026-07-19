import Link from 'next/link';
import { redirect } from 'next/navigation';
import { Plus } from 'lucide-react';

import { getCurrentUser } from '@/lib/session';
import { getServerCookieHeader, apiGet } from '@/lib/api';
import type { Listing, Organization } from '@/lib/types';
import { AdminPageHeader } from '@/components/admin/page-header';
import { OrgSelect } from '@/components/admin/org-select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface AdminListingsPageProps {
  searchParams: Promise<{ org_id?: string }>;
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'secondary',
  ready_for_review: 'outline',
  approved: 'default',
  published: 'default',
  paused: 'secondary',
  sold: 'destructive',
  rented: 'outline',
  expired: 'destructive',
  archived: 'secondary',
};

function formatPrice(price?: number, currency?: string): string {
  if (price == null) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency ?? 'INR',
    maximumFractionDigits: 0,
  }).format(price);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function coverUrl(media: Listing['media']): string | null {
  const cover = media.find((m) => m.is_cover);
  if (cover?.variants?.thumbnail) return cover.variants.thumbnail;
  if (cover?.variants?.web) return cover.variants.web;
  if (cover?.url) return cover.url;
  const first = media[0];
  if (first?.variants?.thumbnail) return first.variants.thumbnail;
  if (first?.variants?.web) return first.variants.web;
  return first?.url ?? null;
}

export default async function AdminListingsPage({ searchParams }: AdminListingsPageProps) {
  const user = await getCurrentUser();
  if (!user) redirect('/login?redirect=/admin/listings');

  const cookieHeader = await getServerCookieHeader();
  const params = await searchParams;

  let organizations: Organization[] = [];
  try {
    organizations = await apiGet<Organization[]>('/api/v1/organizations', {
      cookies: cookieHeader,
    });
  } catch {
    // empty
  }

  const selectedOrgId = params.org_id ?? organizations[0]?.id ?? '';

  let listings: Listing[] = [];
  if (selectedOrgId) {
    try {
      listings = await apiGet<Listing[]>(
        `/api/v1/organizations/${selectedOrgId}/listings`,
        { cookies: cookieHeader }
      );
    } catch {
      // empty
    }
  }

  return (
    <div className="space-y-6">
      <AdminPageHeader
        title="Listings"
        description="Create and manage Dream Home Estate inventory for the public site and social campaigns."
        actions={
          selectedOrgId ? (
            <Button asChild className="rounded-full bg-accent text-accent-foreground hover:bg-accent/90">
              <Link href={`/admin/listings/new?org_id=${selectedOrgId}`}>
                <Plus className="mr-2 h-4 w-4" />
                New listing
              </Link>
            </Button>
          ) : undefined
        }
      />

      <OrgSelect
        organizations={organizations}
        selectedOrgId={selectedOrgId}
        basePath="/admin/listings"
      />

      {!selectedOrgId && organizations.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No organizations found</CardTitle>
            <CardDescription>
              You need to be a member of an organization to manage listings.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : listings.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No listings yet</CardTitle>
            <CardDescription>
              Create your first dream home listing to get started.
            </CardDescription>
          </CardHeader>
          {selectedOrgId && (
            <CardContent>
              <Button asChild className="rounded-full bg-accent text-accent-foreground hover:bg-accent/90">
                <Link href={`/admin/listings/new?org_id=${selectedOrgId}`}>
                  <Plus className="mr-2 h-4 w-4" />
                  New listing
                </Link>
              </Button>
            </CardContent>
          )}
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {listings.map((listing) => (
            <Link
              key={listing.id}
              href={`/admin/listings/${listing.id}/edit?org_id=${selectedOrgId}`}
              className="group"
            >
              <Card className="h-full overflow-hidden transition duration-300 group-hover:-translate-y-0.5 group-hover:border-accent/30 group-hover:shadow-soft">
                <div className="aspect-video bg-muted">
                  {coverUrl(listing.media) ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={coverUrl(listing.media)!}
                      alt={listing.title}
                      className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center text-muted-foreground">
                      No image
                    </div>
                  )}
                </div>
                <CardHeader>
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="line-clamp-1 text-lg">{listing.title}</CardTitle>
                    <Badge variant={(STATUS_COLORS[listing.listing_status] as 'default' | 'secondary' | 'outline' | 'destructive') ?? 'secondary'}>
                      {listing.listing_status.replace(/_/g, ' ')}
                    </Badge>
                  </div>
                  <CardDescription>
                    <span className="block font-medium text-foreground">
                      {formatPrice(listing.price, listing.currency)}
                      {listing.transaction_type === 'rent' ? '/mo' : ''}
                    </span>
                    <span className="block">
                      {listing.city}{listing.state_region ? `, ${listing.state_region}` : ''}
                    </span>
                    <span className="block text-xs">Updated {formatDate(listing.updated_at)}</span>
                  </CardDescription>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
