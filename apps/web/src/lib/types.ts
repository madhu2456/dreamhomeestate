export type MembershipRole = 'owner' | 'administrator' | 'editor' | 'viewer';

export interface Organization {
  id: string;
  name: string;
  slug: string;
}

export interface Membership {
  organization: Organization;
  role: MembershipRole;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  memberships: Membership[];
}

export interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, unknown>;
}

// --- Listing types ---

export type ListingStatus =
  | 'draft'
  | 'ready_for_review'
  | 'approved'
  | 'published'
  | 'paused'
  | 'sold'
  | 'rented'
  | 'expired'
  | 'archived';

export type TransactionType = 'sale' | 'rent' | 'lease' | 'other';

export type PropertyType =
  | 'apartment'
  | 'house'
  | 'villa'
  | 'plot'
  | 'commercial'
  | 'office'
  | 'shop'
  | 'warehouse'
  | 'other';

export type FurnishingStatus = 'unfurnished' | 'semi_furnished' | 'furnished';

export type ConstructionStatus = 'ready_to_move' | 'under_construction' | 'new_launch';

export type OwnershipType = 'freehold' | 'leasehold' | 'power_of_attorney' | 'cooperative';

export interface ListingMedia {
  id: string;
  listing_id: string;
  kind: 'image' | 'video';
  url?: string;
  variants?: Record<string, string>;
  width?: number;
  height?: number;
  order_index: number;
  is_cover: boolean;
  processing_status: string;
  caption?: string;
  original_file_name?: string;
}

export interface Listing {
  id: string;
  org_id: string;
  slug: string;
  listing_status: ListingStatus;
  title: string;
  transaction_type: TransactionType;
  property_type: PropertyType;
  price?: number;
  currency: string;
  negotiable: boolean;
  deposit?: number;
  maintenance_charges?: number;
  area?: number;
  area_unit: string;
  bedrooms?: number;
  bathrooms?: number;
  balconies?: number;
  parking_spaces?: number;
  furnishing_status?: FurnishingStatus;
  construction_status?: ConstructionStatus;
  ownership_type?: OwnershipType;
  floor_number?: number;
  total_floors?: number;
  address_line?: string;
  locality?: string;
  landmark?: string;
  city: string;
  state_region?: string;
  postal_code?: string;
  country: string;
  latitude?: number;
  longitude?: number;
  summary?: string;
  description?: string;
  key_selling_points?: string[];
  nearby_landmarks?: string[];
  contact_name?: string;
  contact_phone?: string;
  contact_email?: string;
  whatsapp_contact?: string;
  seo_title?: string;
  meta_description?: string;
  og_title?: string;
  og_description?: string;
  og_image_url?: string;
  auto_distribute: boolean;
  version: number;
  published_at?: string;
  expires_at?: string;
  created_at: string;
  updated_at: string;
  media: ListingMedia[];
}

// --- Social Account types ---

export type Provider = 'instagram' | 'x' | 'mock';
export type ConnectionStatus = 'active' | 'revoked' | 'expired' | 'error';
export type AccountType = 'personal' | 'business' | 'creator' | 'page';

export interface SocialAccount {
  id: string;
  organization_id: string;
  provider: Provider;
  provider_account_id: string;
  display_name?: string;
  username?: string;
  profile_image_url?: string;
  account_type?: AccountType;
  connection_status: ConnectionStatus;
  granted_scopes?: string[];
  is_default_destination: boolean;
  created_at: string;
  updated_at: string;
  revoked_at?: string;
}

// --- Content template types ---

export interface ContentTemplate {
  id: string;
  organization_id: string;
  name: string;
  scope?: string | null;
  platform: Provider;
  language: string;
  campaign_tag?: string | null;
  title_template?: string | null;
  body_template: string;
  variables: string[];
  is_default: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface PreviewResponse {
  title?: string | null;
  body: string;
  platform: Provider;
  warnings: string[];
  errors: string[];
  length: number;
  max_length?: number | null;
  length_exceeded: boolean;
}

// --- Publication types ---

export type JobStatus =
  | 'pending_approval'
  | 'approved'
  | 'rejected'
  | 'queued'
  | 'publishing'
  | 'published'
  | 'failed'
  | 'cancelled';

export interface PublicationJob {
  id: string;
  campaign_id: string;
  social_account_id: string;
  template_id: string | null;
  idempotency_key: string;
  status: JobStatus;
  rendered_title: string | null;
  rendered_body: string | null;
  media_urls: string[] | null;
  scheduled_at: string | null;
  approved_at: string | null;
  approved_by: string | null;
  published_at: string | null;
  provider_job_id: string | null;
  error_code: string | null;
  error_message: string | null;
  retry_count: number;
  max_retries: number;
  created_at: string;
  updated_at: string;
}

export interface PublicationCampaign {
  id: string;
  organization_id: string;
  listing_id: string | null;
  listing_version_id: string | null;
  campaign_kind?: string;
  title?: string | null;
  body?: string | null;
  media_urls?: string[] | null;
  created_by: string | null;
  status: JobStatus;
  auto_distribute: boolean;
  created_at: string;
  updated_at: string;
  jobs: PublicationJob[];
}

export interface CreateCampaignRequest {
  listing_id: string;
  auto_distribute?: boolean;
  scheduled_at?: string | null;
  social_account_ids?: string[];
}

export interface CreateQuickPostRequest {
  body: string;
  title?: string;
  media_urls: string[];
  social_account_ids: string[];
  auto_distribute?: boolean;
}

export interface JobActionResponse {
  id: string;
  status: JobStatus;
  message: string;
}
