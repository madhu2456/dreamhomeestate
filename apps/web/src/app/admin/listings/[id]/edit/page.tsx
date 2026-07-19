'use client';

import { Suspense, useCallback, useEffect, useState } from 'react';
import { useRouter, useSearchParams, useParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import Link from 'next/link';
import { Trash2, Star } from 'lucide-react';

import { apiGet, apiPatch, apiPost, apiDelete } from '@/lib/api';
import { useToast } from '@/components/ui/use-toast';
import type { Listing, ListingMedia } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface FormValues {
  title: string;
  transaction_type: string;
  property_type: string;
  price: string;
  currency: string;
  area: string;
  area_unit: string;
  bedrooms: string;
  bathrooms: string;
  city: string;
  country: string;
  summary: string;
  description: string;
  address_line: string;
  locality: string;
  state_region: string;
  postal_code: string;
  negotiable: boolean;
  furnishing_status: string;
  construction_status: string;
  ownership_type: string;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  whatsapp_contact: string;
  listing_status: string;
}

function mediaSrc(media: ListingMedia): string {
  if (media.variants?.thumbnail) return media.variants.thumbnail;
  if (media.variants?.web) return media.variants.web;
  return media.url ?? '';
}

function EditListingFormInner() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const { toast } = useToast();

  const listingId = params.id as string;
  const orgId = searchParams.get('org_id') ?? '';

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [media, setMedia] = useState<ListingMedia[]>([]);
  const [uploading, setUploading] = useState(false);
  const [listing, setListing] = useState<Listing | null>(null);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>();

  const fetchListing = useCallback(async () => {
    if (!orgId || !listingId) return;
    setFetching(true);
    try {
      const data = await apiGet<Listing>(
        `/api/v1/organizations/${orgId}/listings/${listingId}`
      );
      setListing(data);
      setMedia(data.media ?? []);
      reset({
        title: data.title ?? '',
        transaction_type: data.transaction_type ?? 'sale',
        property_type: data.property_type ?? 'apartment',
        price: data.price?.toString() ?? '',
        currency: data.currency ?? 'INR',
        area: data.area?.toString() ?? '',
        area_unit: data.area_unit ?? 'sqft',
        bedrooms: data.bedrooms?.toString() ?? '',
        bathrooms: data.bathrooms?.toString() ?? '',
        city: data.city ?? '',
        country: data.country ?? 'India',
        summary: data.summary ?? '',
        description: data.description ?? '',
        address_line: data.address_line ?? '',
        locality: data.locality ?? '',
        state_region: data.state_region ?? '',
        postal_code: data.postal_code ?? '',
        negotiable: data.negotiable ?? false,
        furnishing_status: data.furnishing_status ?? '',
        construction_status: data.construction_status ?? '',
        ownership_type: data.ownership_type ?? '',
        contact_name: data.contact_name ?? '',
        contact_phone: data.contact_phone ?? '',
        contact_email: data.contact_email ?? '',
        whatsapp_contact: data.whatsapp_contact ?? '',
        listing_status: data.listing_status ?? 'draft',
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load listing');
    } finally {
      setFetching(false);
    }
  }, [orgId, listingId, reset]);

  useEffect(() => {
    fetchListing();
  }, [fetchListing]);

  async function onSubmit(data: FormValues) {
    if (!orgId || !listingId) return;

    setError(null);
    setLoading(true);

    const body: Record<string, unknown> = {
      title: data.title,
      transaction_type: data.transaction_type || 'sale',
      property_type: data.property_type || 'apartment',
      currency: data.currency || 'INR',
      negotiable: data.negotiable,
      area_unit: data.area_unit || 'sqft',
      city: data.city,
      country: data.country || 'India',
      listing_status: data.listing_status || 'draft',
    };

    if (data.price) body.price = Number(data.price);
    if (data.area) body.area = Number(data.area);
    if (data.bedrooms) body.bedrooms = Number(data.bedrooms);
    if (data.bathrooms) body.bathrooms = Number(data.bathrooms);
    if (data.summary) body.summary = data.summary;
    if (data.description) body.description = data.description;
    if (data.address_line) body.address_line = data.address_line;
    if (data.locality) body.locality = data.locality;
    if (data.state_region) body.state_region = data.state_region;
    if (data.postal_code) body.postal_code = data.postal_code;
    if (data.furnishing_status) body.furnishing_status = data.furnishing_status;
    if (data.construction_status) body.construction_status = data.construction_status;
    if (data.ownership_type) body.ownership_type = data.ownership_type;
    if (data.contact_name) body.contact_name = data.contact_name;
    if (data.contact_phone) body.contact_phone = data.contact_phone;
    if (data.contact_email) body.contact_email = data.contact_email;
    if (data.whatsapp_contact) body.whatsapp_contact = data.whatsapp_contact;

    try {
      await apiPatch(`/api/v1/organizations/${orgId}/listings/${listingId}`, body);
      toast({ title: 'Saved', description: 'Listing updated successfully.' });
      router.refresh();
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to update listing',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleMediaUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !orgId || !listingId) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      await apiPost(
        `/api/v1/organizations/${orgId}/listings/${listingId}/media`,
        formData
      );
      toast({ title: 'Uploaded', description: 'Media uploaded successfully.' });
      await fetchListing();
    } catch (err) {
      toast({
        title: 'Upload failed',
        description: err instanceof Error ? err.message : 'Failed to upload media',
        variant: 'destructive',
      });
    } finally {
      setUploading(false);
      // Reset input
      e.target.value = '';
    }
  }

  async function handleSetCover(mediaId: string) {
    if (!orgId || !listingId) return;
    try {
      await apiPatch(
        `/api/v1/organizations/${orgId}/listings/${listingId}/media/${mediaId}/cover`
      );
      toast({ title: 'Cover updated' });
      await fetchListing();
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to set cover',
        variant: 'destructive',
      });
    }
  }

  async function handleDeleteMedia(mediaId: string) {
    if (!orgId || !listingId) return;
    if (!confirm('Delete this media?')) return;

    try {
      await apiDelete(
        `/api/v1/organizations/${orgId}/listings/${listingId}/media/${mediaId}`
      );
      toast({ title: 'Deleted', description: 'Media deleted.' });
      await fetchListing();
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to delete media',
        variant: 'destructive',
      });
    }
  }

  if (fetching) {
    return <p className="text-muted-foreground">Loading listing…</p>;
  }

  if (!listing && !fetching) {
    return (
      <Alert variant="destructive">
        <AlertDescription>Listing not found.</AlertDescription>
      </Alert>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-8">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Media Section */}
      <Card>
        <CardHeader>
          <CardTitle>Media</CardTitle>
          <CardDescription>Upload images and set a cover photo.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="media-upload">Upload Image</Label>
            <Input
              id="media-upload"
              type="file"
              accept="image/*"
              disabled={uploading}
              onChange={handleMediaUpload}
              className="mt-1 cursor-pointer"
            />
            {uploading && <p className="mt-1 text-sm text-muted-foreground">Uploading…</p>}
          </div>

          {media.length === 0 ? (
            <p className="text-sm text-muted-foreground">No media uploaded yet.</p>
          ) : (
            <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 lg:grid-cols-6">
              {media.map((m) => (
                <div key={m.id} className="group relative">
                  <img
                    src={mediaSrc(m)}
                    alt={m.caption ?? m.original_file_name ?? ''}
                    className="aspect-square w-full rounded-md border object-cover"
                  />
                  <div className="absolute inset-0 flex items-center justify-center gap-1 rounded-md bg-black/40 opacity-0 transition-opacity group-hover:opacity-100">
                    {!m.is_cover && (
                      <button
                        type="button"
                        onClick={() => handleSetCover(m.id)}
                        className="rounded bg-white px-2 py-1 text-xs font-medium text-black hover:bg-gray-200"
                        title="Set as cover"
                      >
                        <Star className="h-3 w-3" />
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => handleDeleteMedia(m.id)}
                      className="rounded bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-700"
                      title="Delete"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                  {m.is_cover && (
                    <span className="absolute left-1 top-1 rounded bg-primary px-1.5 py-0.5 text-[10px] font-semibold text-primary-foreground">
                      Cover
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Basic Info */}
      <Card>
        <CardHeader>
          <CardTitle>Basic Information</CardTitle>
          <CardDescription>Core listing details.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title">Title *</Label>
            <Input id="title" {...register('title', { required: 'Title is required' })} />
            {errors.title && <p className="text-sm text-destructive">{errors.title.message}</p>}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="transaction_type">Transaction Type</Label>
              <select
                id="transaction_type"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                {...register('transaction_type')}
              >
                <option value="sale">Sale</option>
                <option value="rent">Rent</option>
                <option value="lease">Lease</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="property_type">Property Type</Label>
              <select
                id="property_type"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                {...register('property_type')}
              >
                <option value="apartment">Apartment</option>
                <option value="house">House</option>
                <option value="villa">Villa</option>
                <option value="plot">Plot</option>
                <option value="commercial">Commercial</option>
                <option value="office">Office</option>
                <option value="shop">Shop</option>
                <option value="warehouse">Warehouse</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="price">Price</Label>
              <Input id="price" type="number" {...register('price')} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="currency">Currency</Label>
              <Input id="currency" {...register('currency')} />
            </div>
            <div className="flex items-end pb-2">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" {...register('negotiable')} className="h-4 w-4" />
                Negotiable
              </label>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="area">Area</Label>
              <Input id="area" type="number" {...register('area')} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="area_unit">Area Unit</Label>
              <select
                id="area_unit"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                {...register('area_unit')}
              >
                <option value="sqft">sqft</option>
                <option value="sqm">sqm</option>
                <option value="sqyrd">sqyrd</option>
                <option value="acre">acre</option>
                <option value="hectare">hectare</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="listing_status">Status</Label>
              <select
                id="listing_status"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                {...register('listing_status')}
              >
                <option value="draft">Draft</option>
                <option value="ready_for_review">Ready for Review</option>
                <option value="published">Published</option>
                <option value="paused">Paused</option>
                <option value="sold">Sold</option>
                <option value="rented">Rented</option>
                <option value="expired">Expired</option>
                <option value="archived">Archived</option>
              </select>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="bedrooms">Bedrooms</Label>
              <Input id="bedrooms" type="number" min="0" {...register('bedrooms')} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="bathrooms">Bathrooms</Label>
              <Input id="bathrooms" type="number" min="0" {...register('bathrooms')} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="furnishing_status">Furnishing</Label>
              <select
                id="furnishing_status"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                {...register('furnishing_status')}
              >
                <option value="">—</option>
                <option value="unfurnished">Unfurnished</option>
                <option value="semi_furnished">Semi Furnished</option>
                <option value="furnished">Furnished</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Location */}
      <Card>
        <CardHeader>
          <CardTitle>Location</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="address_line">Address</Label>
              <Input id="address_line" {...register('address_line')} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="locality">Locality</Label>
              <Input id="locality" {...register('locality')} />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="city">City *</Label>
              <Input id="city" {...register('city', { required: 'City is required' })} />
              {errors.city && <p className="text-sm text-destructive">{errors.city.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="state_region">State / Region</Label>
              <Input id="state_region" {...register('state_region')} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="postal_code">Postal Code</Label>
              <Input id="postal_code" {...register('postal_code')} />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="country">Country</Label>
            <Input id="country" {...register('country')} />
          </div>
        </CardContent>
      </Card>

      {/* Description */}
      <Card>
        <CardHeader>
          <CardTitle>Description</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="summary">Summary</Label>
            <Textarea id="summary" rows={2} {...register('summary')} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Full Description</Label>
            <Textarea id="description" rows={4} {...register('description')} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="construction_status">Construction Status</Label>
              <select
                id="construction_status"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                {...register('construction_status')}
              >
                <option value="">—</option>
                <option value="ready_to_move">Ready to Move</option>
                <option value="under_construction">Under Construction</option>
                <option value="new_launch">New Launch</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="ownership_type">Ownership Type</Label>
              <select
                id="ownership_type"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                {...register('ownership_type')}
              >
                <option value="">—</option>
                <option value="freehold">Freehold</option>
                <option value="leasehold">Leasehold</option>
                <option value="power_of_attorney">Power of Attorney</option>
                <option value="cooperative">Cooperative</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Contact */}
      <Card>
        <CardHeader>
          <CardTitle>Contact Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="contact_name">Contact Name</Label>
              <Input id="contact_name" {...register('contact_name')} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="contact_phone">Contact Phone</Label>
              <Input id="contact_phone" {...register('contact_phone')} />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="contact_email">Contact Email</Label>
              <Input id="contact_email" type="email" {...register('contact_email')} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="whatsapp_contact">WhatsApp</Label>
              <Input id="whatsapp_contact" {...register('whatsapp_contact')} />
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center gap-4">
        <Button type="submit" disabled={loading}>
          {loading ? 'Saving…' : 'Save Listing'}
        </Button>
        <Button variant="outline" asChild>
          <Link href={`/admin/listings?org_id=${orgId}`}>Back to Listings</Link>
        </Button>
      </div>
    </form>
  );
}

export default function EditListingPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Edit Listing</h1>
        <p className="mt-1 text-muted-foreground">Update property details and manage media.</p>
      </div>
      <Suspense fallback={<p className="text-muted-foreground">Loading…</p>}>
        <EditListingFormInner />
      </Suspense>
    </div>
  );
}
