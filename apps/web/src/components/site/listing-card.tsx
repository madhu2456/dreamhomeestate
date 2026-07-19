import Link from 'next/link';
import { Bath, BedDouble, MapPin, Ruler } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { coverUrl, formatLocation, formatPrice, propertyLabel, transactionLabel } from '@/lib/format';
import type { Listing } from '@/lib/types';
import { cn } from '@/lib/utils';

interface ListingCardProps {
  listing: Listing;
  className?: string;
  priority?: boolean;
}

export function ListingCard({ listing, className }: ListingCardProps) {
  const image = coverUrl(listing, 'web');
  const href = `/listings/${listing.id}`;

  return (
    <Link
      href={href}
      className={cn(
        'group flex h-full flex-col overflow-hidden rounded-2xl border border-border/80 bg-card shadow-card transition duration-300 hover:-translate-y-0.5 hover:border-accent/30 hover:shadow-lift focus-ring',
        className
      )}
    >
      <div className="relative aspect-[4/3] overflow-hidden bg-muted">
        {image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={image}
            alt={listing.title}
            className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.04]"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-secondary to-muted text-sm text-muted-foreground">
            Photo coming soon
          </div>
        )}
        <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/45 to-transparent" />
        <div className="absolute left-3 top-3 flex flex-wrap gap-2">
          <Badge className="border-0 bg-white/95 text-foreground shadow-sm backdrop-blur">
            {transactionLabel(listing.transaction_type)}
          </Badge>
          <Badge variant="secondary" className="border-0 bg-primary/90 text-primary-foreground">
            {propertyLabel(listing.property_type)}
          </Badge>
        </div>
        <p className="absolute bottom-3 left-3 font-display text-xl font-semibold text-white drop-shadow">
          {formatPrice(listing.price, listing.currency, listing.transaction_type)}
        </p>
      </div>

      <div className="flex flex-1 flex-col gap-3 p-4 sm:p-5">
        <div>
          <h3 className="line-clamp-2 font-display text-lg font-semibold leading-snug tracking-tight text-foreground transition group-hover:text-accent">
            {listing.title}
          </h3>
          <p className="mt-1.5 flex items-start gap-1.5 text-sm text-muted-foreground">
            <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" aria-hidden />
            <span className="line-clamp-1">{formatLocation(listing)}</span>
          </p>
        </div>

        {(listing.bedrooms != null || listing.bathrooms != null || listing.area != null) && (
          <div className="mt-auto flex flex-wrap gap-3 border-t border-border/70 pt-3 text-xs font-medium text-muted-foreground">
            {listing.bedrooms != null && (
              <span className="inline-flex items-center gap-1.5">
                <BedDouble className="h-3.5 w-3.5" aria-hidden />
                {listing.bedrooms} bed
              </span>
            )}
            {listing.bathrooms != null && (
              <span className="inline-flex items-center gap-1.5">
                <Bath className="h-3.5 w-3.5" aria-hidden />
                {listing.bathrooms} bath
              </span>
            )}
            {listing.area != null && (
              <span className="inline-flex items-center gap-1.5">
                <Ruler className="h-3.5 w-3.5" aria-hidden />
                {listing.area} {listing.area_unit}
              </span>
            )}
          </div>
        )}
      </div>
    </Link>
  );
}
