'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import Link from 'next/link';

import { apiPost } from '@/lib/api';
import type { Listing } from '@/lib/types';
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

function NewListingFormInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const orgId = searchParams.get('org_id') ?? '';

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    defaultValues: {
      transaction_type: 'sale',
      property_type: 'apartment',
      currency: 'INR',
      area_unit: 'sqft',
      country: 'India',
      listing_status: 'draft',
      negotiable: false,
    },
  });

  async function onSubmit(data: FormValues) {
    if (!orgId) {
      setError('No organization selected. Please go back and select an organization.');
      return;
    }

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
      const listing = await apiPost<Listing>(
        `/api/v1/organizations/${orgId}/listings`,
        body
      );
      router.push(`/admin/listings/${listing.id}/edit?org_id=${orgId}`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create listing');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-8">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

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
              <Input id="currency" {...register('currency')} placeholder="INR" />
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
          {loading ? 'Creating…' : 'Create Listing'}
        </Button>
        <Button variant="outline" asChild>
          <Link href="/admin/listings">Cancel</Link>
        </Button>
      </div>
    </form>
  );
}

export default function NewListingPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">New Listing</h1>
        <p className="mt-1 text-muted-foreground">Create a new property listing.</p>
      </div>
      <Suspense fallback={<p className="text-muted-foreground">Loading…</p>}>
        <NewListingFormInner />
      </Suspense>
    </div>
  );
}
