import Link from 'next/link';
import { Search, SlidersHorizontal } from 'lucide-react';
import { Suspense } from 'react';

import { ListingCard } from '@/components/site/listing-card';
import { Button } from '@/components/ui/button';
import { apiGet } from '@/lib/api';
import type { Listing } from '@/lib/types';

export const metadata = {
  title: 'Dream Homes',
  description: 'Browse dream homes for sale and rent from Dream Home Estate.',
};

interface SearchParams {
  city?: string;
  transaction_type?: string;
  property_type?: string;
  min_price?: string;
  max_price?: string;
  q?: string;
  page?: string;
}

interface ListingsContentProps {
  searchParams: SearchParams;
}

async function ListingsContent({ searchParams }: ListingsContentProps) {
  const params = new URLSearchParams();
  params.set('limit', '12');
  if (searchParams.city) params.set('city', searchParams.city);
  if (searchParams.transaction_type) params.set('transaction_type', searchParams.transaction_type);
  if (searchParams.property_type) params.set('property_type', searchParams.property_type);
  if (searchParams.min_price) params.set('min_price', searchParams.min_price);
  if (searchParams.max_price) params.set('max_price', searchParams.max_price);
  if (searchParams.q) params.set('q', searchParams.q);
  if (searchParams.page) params.set('offset', String((Number(searchParams.page) - 1) * 12));

  let listings: Listing[] = [];
  let error: string | null = null;

  try {
    listings = await apiGet<Listing[]>(`/api/v1/public/listings?${params.toString()}`);
  } catch (err) {
    error = err instanceof Error ? err.message : 'Failed to load listings';
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-destructive/30 bg-destructive/5 px-6 py-10 text-center">
        <h2 className="font-display text-xl font-semibold text-destructive">Couldn’t load listings</h2>
        <p className="mt-2 text-sm text-muted-foreground">{error}</p>
        <Button asChild variant="outline" className="mt-5 rounded-full">
          <Link href="/listings">Try again</Link>
        </Button>
      </div>
    );
  }

  if (listings.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-border bg-muted/30 px-6 py-16 text-center">
        <h2 className="font-display text-2xl font-semibold">No matches</h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
          Try a different city, property type, or price range — or clear filters to see everything available.
        </p>
        <Button asChild className="mt-6 rounded-full bg-accent text-accent-foreground hover:bg-accent/90">
          <Link href="/listings">Clear filters</Link>
        </Button>
      </div>
    );
  }

  return (
    <>
      <p className="mb-5 text-sm text-muted-foreground">
        Showing <span className="font-semibold text-foreground">{listings.length}</span> listing
        {listings.length === 1 ? '' : 's'}
      </p>
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {listings.map((listing) => (
          <ListingCard key={listing.id} listing={listing} />
        ))}
      </div>
    </>
  );
}

function FilterField({
  id,
  label,
  children,
  className = '',
}: {
  id: string;
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 block text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </label>
      {children}
    </div>
  );
}

const fieldClass =
  'h-11 w-full rounded-xl border border-input bg-background px-3 text-sm shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

interface ListingsPageProps {
  searchParams: Promise<SearchParams>;
}

export default async function ListingsPage({ searchParams }: ListingsPageProps) {
  const resolved = await searchParams;

  return (
    <main>
      <section className="border-b border-border/70 bg-muted/30">
        <div className="container-wide px-4 py-12 sm:px-6 sm:py-14 lg:px-8">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
            Dream Home Estate
          </p>
          <h1 className="mt-2 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
            Find your dream home
          </h1>
          <p className="mt-3 max-w-2xl text-muted-foreground">
            Explore homes for sale and rent. Filter by city, property type, and budget to match the
            lifestyle you want.
          </p>
        </div>
      </section>

      <section className="container-wide px-4 py-8 sm:px-6 lg:px-8 lg:py-10">
        <form
          method="GET"
          action="/listings"
          className="mb-10 rounded-2xl border border-border/80 bg-card p-4 shadow-card sm:p-5"
        >
          <div className="mb-4 flex items-center gap-2 text-sm font-medium text-foreground">
            <SlidersHorizontal className="h-4 w-4 text-accent" aria-hidden />
            Filters
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
            <FilterField id="q" label="Search" className="xl:col-span-2">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  id="q"
                  name="q"
                  type="text"
                  defaultValue={resolved.q ?? ''}
                  placeholder="Keywords…"
                  className={`${fieldClass} pl-9`}
                />
              </div>
            </FilterField>
            <FilterField id="city" label="City">
              <input
                id="city"
                name="city"
                type="text"
                defaultValue={resolved.city ?? ''}
                placeholder="City"
                className={fieldClass}
              />
            </FilterField>
            <FilterField id="transaction_type" label="Deal type">
              <select
                id="transaction_type"
                name="transaction_type"
                defaultValue={resolved.transaction_type ?? ''}
                className={fieldClass}
              >
                <option value="">All</option>
                <option value="sale">Sale</option>
                <option value="rent">Rent</option>
                <option value="lease">Lease</option>
              </select>
            </FilterField>
            <FilterField id="property_type" label="Property">
              <select
                id="property_type"
                name="property_type"
                defaultValue={resolved.property_type ?? ''}
                className={fieldClass}
              >
                <option value="">All</option>
                <option value="apartment">Apartment</option>
                <option value="house">House</option>
                <option value="villa">Villa</option>
                <option value="plot">Plot</option>
                <option value="commercial">Commercial</option>
                <option value="office">Office</option>
                <option value="shop">Shop</option>
                <option value="warehouse">Warehouse</option>
              </select>
            </FilterField>
            <FilterField id="min_price" label="Min price">
              <input
                id="min_price"
                name="min_price"
                type="number"
                defaultValue={resolved.min_price ?? ''}
                placeholder="0"
                className={fieldClass}
              />
            </FilterField>
            <FilterField id="max_price" label="Max price">
              <input
                id="max_price"
                name="max_price"
                type="number"
                defaultValue={resolved.max_price ?? ''}
                placeholder="Any"
                className={fieldClass}
              />
            </FilterField>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button type="submit" className="rounded-full bg-accent text-accent-foreground hover:bg-accent/90">
              Apply filters
            </Button>
            <Button type="reset" variant="outline" className="rounded-full" asChild>
              <Link href="/listings">Clear</Link>
            </Button>
          </div>
        </form>

        <Suspense
          fallback={
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="h-80 animate-pulse rounded-2xl bg-muted" />
              ))}
            </div>
          }
        >
          <ListingsContent searchParams={resolved} />
        </Suspense>
      </section>
    </main>
  );
}
