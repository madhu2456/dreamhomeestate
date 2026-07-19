import type { Listing, ListingMedia } from '@/lib/types';

export function formatPrice(price?: number | null, currency?: string, transactionType?: string): string {
  if (price == null) return 'Price on request';
  const formatted = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency ?? 'USD',
    maximumFractionDigits: 0,
  }).format(price);
  if (transactionType === 'rent') return `${formatted}/mo`;
  return formatted;
}

export function formatLocation(listing: Pick<Listing, 'locality' | 'city' | 'state_region'>): string {
  return [listing.locality, listing.city, listing.state_region].filter(Boolean).join(', ');
}

export function transactionLabel(type: string): string {
  switch (type) {
    case 'sale':
      return 'For Sale';
    case 'rent':
      return 'For Rent';
    case 'lease':
      return 'For Lease';
    default:
      return type.replace(/_/g, ' ');
  }
}

export function propertyLabel(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function mediaUrl(media?: ListingMedia | null, prefer: 'web' | 'thumbnail' | 'instagram' = 'web'): string | null {
  if (!media) return null;
  if (prefer === 'thumbnail') {
    return media.variants?.thumbnail || media.variants?.web || media.url || null;
  }
  if (prefer === 'instagram') {
    return media.variants?.instagram || media.variants?.web || media.url || null;
  }
  return media.variants?.web || media.variants?.thumbnail || media.url || null;
}

export function coverUrl(listing: Listing, prefer: 'web' | 'thumbnail' = 'web'): string | null {
  const cover = listing.media?.find((m) => m.is_cover) ?? listing.media?.[0];
  return mediaUrl(cover, prefer);
}

export function specsLine(listing: Listing): string {
  const parts: string[] = [];
  if (listing.bedrooms != null) parts.push(`${listing.bedrooms} bed`);
  if (listing.bathrooms != null) parts.push(`${listing.bathrooms} bath`);
  if (listing.area != null) parts.push(`${listing.area} ${listing.area_unit}`);
  return parts.join(' · ');
}
