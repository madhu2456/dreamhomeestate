import Link from 'next/link';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import {
  ArrowLeft,
  Bath,
  BedDouble,
  Check,
  Mail,
  MapPin,
  MessageCircle,
  Phone,
  Ruler,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiGet } from '@/lib/api';
import {
  formatLocation,
  formatPrice,
  mediaUrl,
  propertyLabel,
  transactionLabel,
} from '@/lib/format';
import type { Listing, ListingMedia } from '@/lib/types';

interface ListingDetailProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: ListingDetailProps): Promise<Metadata> {
  const { id } = await params;
  try {
    const listing = await apiGet<Listing>(`/api/v1/public/listings/${id}`);
    const title = listing.seo_title || listing.title || 'Listing';
    const description = listing.meta_description || listing.summary || undefined;
    return {
      title,
      description,
      openGraph: {
        title: listing.og_title || title,
        description: listing.og_description || description,
        images: listing.og_image_url ? [{ url: listing.og_image_url }] : undefined,
      },
    };
  } catch {
    return { title: 'Listing' };
  }
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  if (value == null || value === '') return null;
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border/60 py-2.5 text-sm last:border-0">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right font-medium capitalize text-foreground">{value}</dd>
    </div>
  );
}

export default async function ListingDetailPage({ params }: ListingDetailProps) {
  const { id } = await params;

  let listing: Listing;
  try {
    listing = await apiGet<Listing>(`/api/v1/public/listings/${id}`);
  } catch {
    notFound();
  }

  const media = [...(listing.media ?? [])].sort((a, b) => {
    if (a.is_cover && !b.is_cover) return -1;
    if (!a.is_cover && b.is_cover) return 1;
    return (a.order_index ?? 0) - (b.order_index ?? 0);
  });
  const hero = media[0];
  const gallery = media.slice(1);

  return (
    <main>
      <div className="border-b border-border/70 bg-muted/20">
        <div className="container-wide px-4 py-4 sm:px-6 lg:px-8">
          <Link
            href="/listings"
            className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground transition hover:text-foreground focus-ring rounded-md"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to listings
          </Link>
        </div>
      </div>

      <div className="container-wide px-4 py-8 sm:px-6 lg:px-8 lg:py-10">
        {/* Hero media */}
        <div className="overflow-hidden rounded-2xl border border-border/80 bg-muted shadow-card">
          {hero && mediaUrl(hero) ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={mediaUrl(hero)!}
              alt={listing.title}
              className="max-h-[480px] w-full object-cover"
            />
          ) : (
            <div className="flex h-64 items-center justify-center text-muted-foreground sm:h-80">
              No photos available
            </div>
          )}
        </div>

        {gallery.length > 0 && (
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {gallery.slice(0, 4).map((m: ListingMedia) => {
              const src = mediaUrl(m, 'thumbnail');
              if (!src) return null;
              return (
                <a
                  key={m.id}
                  href={mediaUrl(m) ?? src}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="overflow-hidden rounded-xl border border-border/70 focus-ring"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={src}
                    alt={m.caption ?? listing.title}
                    className="aspect-[4/3] w-full object-cover transition hover:opacity-90"
                  />
                </a>
              );
            })}
          </div>
        )}

        <div className="mt-8 grid gap-8 lg:grid-cols-12 lg:gap-10">
          <div className="space-y-8 lg:col-span-7 xl:col-span-8">
            <header>
              <div className="flex flex-wrap gap-2">
                <Badge className="border-0 bg-accent/15 text-accent hover:bg-accent/20">
                  {transactionLabel(listing.transaction_type)}
                </Badge>
                <Badge variant="secondary">{propertyLabel(listing.property_type)}</Badge>
              </div>
              <h1 className="mt-3 font-display text-3xl font-semibold tracking-tight sm:text-4xl lg:text-5xl">
                {listing.title}
              </h1>
              <p className="mt-3 flex items-start gap-2 text-muted-foreground">
                <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden />
                {formatLocation(listing)}
                {listing.country ? `, ${listing.country}` : ''}
              </p>
              <p className="mt-4 font-display text-3xl font-semibold text-foreground sm:text-4xl">
                {formatPrice(listing.price, listing.currency, listing.transaction_type)}
                {listing.negotiable && (
                  <span className="ml-3 text-base font-sans font-medium text-muted-foreground">
                    Negotiable
                  </span>
                )}
              </p>

              <div className="mt-6 flex flex-wrap gap-4 rounded-2xl border border-border/80 bg-card p-4 text-sm font-medium shadow-sm">
                {listing.bedrooms != null && (
                  <span className="inline-flex items-center gap-2">
                    <BedDouble className="h-4 w-4 text-accent" />
                    {listing.bedrooms} bedrooms
                  </span>
                )}
                {listing.bathrooms != null && (
                  <span className="inline-flex items-center gap-2">
                    <Bath className="h-4 w-4 text-accent" />
                    {listing.bathrooms} bathrooms
                  </span>
                )}
                {listing.area != null && (
                  <span className="inline-flex items-center gap-2">
                    <Ruler className="h-4 w-4 text-accent" />
                    {listing.area} {listing.area_unit}
                  </span>
                )}
              </div>
            </header>

            {listing.summary && (
              <section>
                <h2 className="font-display text-2xl font-semibold tracking-tight">Overview</h2>
                <p className="mt-3 text-muted-foreground leading-relaxed">{listing.summary}</p>
              </section>
            )}

            {listing.description && (
              <section>
                <h2 className="font-display text-2xl font-semibold tracking-tight">Description</h2>
                <p className="mt-3 whitespace-pre-wrap text-muted-foreground leading-relaxed">
                  {listing.description}
                </p>
              </section>
            )}

            {listing.key_selling_points && listing.key_selling_points.length > 0 && (
              <section>
                <h2 className="font-display text-2xl font-semibold tracking-tight">Highlights</h2>
                <ul className="mt-4 grid gap-2 sm:grid-cols-2">
                  {listing.key_selling_points.map((point, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2.5 rounded-xl border border-border/70 bg-card px-3.5 py-3 text-sm"
                    >
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden />
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {listing.nearby_landmarks && listing.nearby_landmarks.length > 0 && (
              <section>
                <h2 className="font-display text-2xl font-semibold tracking-tight">Nearby</h2>
                <ul className="mt-3 list-inside list-disc space-y-1.5 text-muted-foreground">
                  {listing.nearby_landmarks.map((lm, i) => (
                    <li key={i}>{lm}</li>
                  ))}
                </ul>
              </section>
            )}
          </div>

          <aside className="space-y-4 lg:col-span-5 xl:col-span-4">
            <div className="sticky top-24 space-y-4">
              <div className="rounded-2xl border border-border/80 bg-card p-5 shadow-card">
                <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Property details
                </h3>
                <dl className="mt-3">
                  <DetailRow label="Type" value={propertyLabel(listing.property_type)} />
                  <DetailRow label="Transaction" value={transactionLabel(listing.transaction_type)} />
                  <DetailRow
                    label="Furnishing"
                    value={listing.furnishing_status?.replace(/_/g, ' ')}
                  />
                  <DetailRow
                    label="Construction"
                    value={listing.construction_status?.replace(/_/g, ' ')}
                  />
                  <DetailRow
                    label="Ownership"
                    value={listing.ownership_type?.replace(/_/g, ' ')}
                  />
                  <DetailRow
                    label="Floor"
                    value={
                      listing.floor_number != null
                        ? `${listing.floor_number}${listing.total_floors ? ` of ${listing.total_floors}` : ''}`
                        : null
                    }
                  />
                  <DetailRow
                    label="Parking"
                    value={listing.parking_spaces != null ? String(listing.parking_spaces) : null}
                  />
                </dl>
              </div>

              {(listing.address_line || listing.city) && (
                <div className="rounded-2xl border border-border/80 bg-card p-5 shadow-card">
                  <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                    Address
                  </h3>
                  <p className="mt-3 text-sm leading-relaxed">
                    {listing.address_line && (
                      <>
                        {listing.address_line}
                        <br />
                      </>
                    )}
                    {formatLocation(listing)}
                    {listing.postal_code ? ` ${listing.postal_code}` : ''}
                    <br />
                    {listing.country}
                  </p>
                </div>
              )}

              {(listing.contact_name || listing.contact_phone || listing.contact_email) && (
                <div className="rounded-2xl border border-border/80 bg-primary p-5 text-primary-foreground shadow-card">
                  <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-primary-foreground/60">
                    Contact agent
                  </h3>
                  {listing.contact_name && (
                    <p className="mt-3 font-display text-xl font-semibold">{listing.contact_name}</p>
                  )}
                  <div className="mt-4 space-y-2">
                    {listing.contact_phone && (
                      <a
                        href={`tel:${listing.contact_phone}`}
                        className="flex items-center gap-2 rounded-xl bg-white/10 px-3 py-2.5 text-sm transition hover:bg-white/15"
                      >
                        <Phone className="h-4 w-4" />
                        {listing.contact_phone}
                      </a>
                    )}
                    {listing.contact_email && (
                      <a
                        href={`mailto:${listing.contact_email}`}
                        className="flex items-center gap-2 rounded-xl bg-white/10 px-3 py-2.5 text-sm transition hover:bg-white/15"
                      >
                        <Mail className="h-4 w-4" />
                        {listing.contact_email}
                      </a>
                    )}
                    {listing.whatsapp_contact && (
                      <a
                        href={`https://wa.me/${listing.whatsapp_contact.replace(/\D/g, '')}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 rounded-xl bg-accent px-3 py-2.5 text-sm font-medium text-accent-foreground transition hover:bg-accent/90"
                      >
                        <MessageCircle className="h-4 w-4" />
                        WhatsApp
                      </a>
                    )}
                  </div>
                </div>
              )}

              <Button asChild variant="outline" className="w-full rounded-full">
                <Link href="/listings">Browse more listings</Link>
              </Button>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}
