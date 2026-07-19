# Data model

Entity relationship summary for the MVP. All non-public tables are scoped to an `organizations` row via `organization_id`. Multi-tenancy is enforced in code and by database foreign keys.

## Core entities

```text
organizations
  ├── users (via organization_memberships)
  ├── listings
  ├── listing_media
  ├── contacts
  ├── social_accounts
  ├── distribution_profiles
  ├── content_templates
  ├── campaigns
  ├── publication_jobs
  ├── platform_posts
  ├── outbox_events
  ├── scheduled_jobs
  ├── inquiries
  └── audit_events
```

## Table descriptions

### users

System identity. A user can belong to multiple organizations with different roles.

- `id` UUID primary key
- `email` unique, verified
- `full_name`
- `password_hash` bcrypt
- `mfa_secret` encrypted, nullable
- `is_active`
- `created_at`, `updated_at`

### organizations

Workspace that owns listings, accounts, templates, jobs, and audit records.

- `id` UUID
- `name`
- `slug` unique
- `logo_url`
- `contact fields`, `default_currency`, `timezone`, `language`, `website_domain`
- `legal_disclaimer`
- `default_social_rules`
- `created_at`, `updated_at`

### organization_memberships

Many-to-many between users and organizations with role.

- `id`
- `organization_id` FK
- `user_id` FK
- `role` enum: owner, administrator, editor, viewer
- `joined_at`, `updated_at`
- Unique `(organization_id, user_id)`

### roles

Hard-coded in application; table documents permissions for reference.

- owner: full control, credentials, users, organization settings
- administrator: listings, accounts, publishing, templates, cannot manage billing/owner-only settings
- editor: create/edit listings, prepare social content, cannot manage secrets/users/destructive settings
- viewer: read-only access

### listings

Real estate listing with lifecycle state machine.

- `id` UUID
- `organization_id` FK
- `public_reference_number` unique scoped to organization
- `title`, `slug`
- `listing_status` enum: draft, ready_for_review, approved, published, paused, sold, rented, expired, archived
- `transaction_type` enum: sale, rent, lease, other
- `price`, `currency`, `price_display_option`, `negotiable`, `deposit`, `maintenance_charges`, `price_per_area_unit`
- `property_type`, `property_subtype`, `bedrooms`, `bathrooms`, `balconies`, `parking_spaces`, `furnishing_status`, `construction_status`, `property_age`, `floor_number`, `total_floors`, `facing`, `availability_date`, `ownership_type`
- `area`, `area_unit`, `carpet_area`, `built_up_area`, `plot_area`
- `address_line`, `locality`, `landmark`, `city`, `state_region`, `postal_code`, `country`, `latitude`, `longitude`, `map_display_preference`, `approximate_location`
- `summary`, `description`, `key_selling_points` JSON, `nearby_landmarks` JSON, `transportation_info`, `legal_notes`, `contact_cta`, `internal_notes`
- `contact_name`, `contact_phone`, `contact_email`, `whatsapp_contact`
- `external_source`
- `seo_title`, `meta_description`, `canonical_url`, `og_title`, `og_description`, `og_image_url`
- `indexing_preference`, `social_sharing_title`, `social_sharing_description`
- `auto_distribute`, `distribution_profile_id` nullable, `scheduled_distribution_at`
- `version` optimistic lock
- `published_at`, `expires_at`, `created_at`, `updated_at`
- Unique `(organization_id, slug)`

### listing_versions

Immutable snapshot of listing at time of publication. Social posts always reference a version.

- `id` UUID
- `listing_id` FK
- `version_number`
- `data` JSONB full snapshot
- `created_at`

### listing_media

Images and videos attached to a listing.

- `id` UUID
- `listing_id` FK
- `organization_id` FK
- `kind` enum: image, video
- `original_object_key`
- `original_file_name`, `mime_type`, `size_bytes`, `checksum_sha256`
- `width`, `height`, `duration_seconds`
- `caption`, `description`, `attribution`
- `order_index`
- `is_cover`
- `processing_status` enum: pending, processing, ready, failed
- `variants` JSONB map of object keys by variant name
- `created_at`, `updated_at`

### amenities + listing_amenities

Normalized amenities.

- amenities: `id`, `name`, `category`, `icon`
- listing_amenities: `listing_id`, `amenity_id`

### contacts

Reusable contact records; can be linked to listings or used as organization defaults.

- `id`, `organization_id`, `name`, `phone`, `email`, `whatsapp`, `role`

### social_accounts

Connected social platform account.

- `id` UUID
- `organization_id` FK
- `provider` enum: instagram, x/twitter, mock (future: facebook, linkedin, threads, ...)
- `provider_account_id` immutable platform identifier
- `display_name`, `username`, `profile_image_url`
- `account_type` enum: personal, business, creator, page
- `connection_status` enum: active, revoked, expired, error
- `granted_scopes` text[]
- `token_expires_at`, `last_validated_at`, `last_successful_publication_at`, `last_error`
- `provider_metadata` JSONB
- `capabilities_snapshot` JSONB
- `is_default_destination`
- `created_by` FK users
- `revoked_at`
- `created_at`, `updated_at`
- Unique `(organization_id, provider, provider_account_id)`

### encrypted_oauth_credentials

Encrypted tokens. Foreign keys reference `social_accounts`. Encryption key stored in `OAUTH_ENCRYPTION_KEY`.

- `id`
- `social_account_id` FK
- `encrypted_access_token`
- `encrypted_refresh_token`
- `token_type`, `scope`, `expires_at`
- `created_at`, `updated_at`

### distribution_profiles

Reusable publishing configuration.

- `id`, `organization_id`, `name`, `description`
- `selected_account_ids` JSONB array
- `platforms` JSONB
- `immediate` boolean, `spacing_minutes`
- `instagram_post_type`, `x_thread_preference`
- `media_selection_strategy`, `template_id`, `hashtag_set`, `utm_campaign`
- `ai_assistance`, `requires_approval`, `retry_policy` JSONB
- `notification_recipients` JSONB

### content_templates

Platform/scope templates stored as body + title + variable list.

- `id`, `organization_id`, `name`, `scope`
- `platform`, `language`, `campaign_tag`
- `title_template`, `body_template`
- `variables` JSONB allow-list
- `is_default`
- `version` integer
- `created_at`, `updated_at`

### template_versions

Immutable prior versions.

- `id`, `template_id`, `version`, `title_template`, `body_template`, `created_at`

### campaigns

A publication campaign for one listing version.

- `id`, `organization_id`, `listing_id`, `listing_version_id`
- `status` enum: pending, processing, partial, completed, failed, cancelled
- `distribution_profile_id` nullable
- `utm_campaign`, `utm_source`, `utm_medium`
- `created_at`, `updated_at`

### campaign_destinations

Per-destination selection and override.

- `id`, `campaign_id`, `organization_id`, `social_account_id`
- `platform`, `status`
- `override_title`, `override_body`, `override_media_ids` JSONB
- `sequence_number`

### rendered_social_content

Final content used for each publication attempt; never mutated after creation.

- `id`, `publication_job_id`, `campaign_destination_id`
- `platform`, `title`, `body`, `media_object_keys` JSONB
- `hashtags`, `link_url`, `alt_text`
- `created_at`

### publication_jobs

State machine per destination.

- `id`, `organization_id`, `campaign_id`, `campaign_destination_id`, `social_account_id`, `provider`
- `state` enum: created, queued, validating, preparing_media, waiting_for_provider, ready_to_publish, publishing, published, partially_published, retry_scheduled, rate_limited, auth_required, validation_failed, permanently_failed, cancelled
- `previous_state`
- `attempt_number`, `max_attempts`
- `idempotency_key`
- `scheduled_at`, `next_retry_at`
- `provider_request_id`, `provider_post_id`, `provider_post_url`
- `normalized_error_code`, `safe_error_message`, `diagnostic_details`
- `correlation_id`, `worker_id`
- `created_at`, `updated_at`

### publication_attempts

Immutable record of every attempt.

- `id`, `publication_job_id`, `attempt_number`
- `started_at`, `finished_at`
- `state_before`, `state_after`
- `provider_request_id`, `provider_response_metadata` JSONB (safe subset)
- `error_code`, `error_message`

### platform_posts

Successful provider posts.

- `id`, `organization_id`, `publication_job_id`, `social_account_id`, `provider`
- `provider_post_id`, `provider_post_url`
- `idempotency_key` unique
- `sequence_number`
- `posted_at`

### outbox_events

Transactional outbox for async handlers.

- `id`, `organization_id`, `topic`, `payload` JSONB
- `status` enum: pending, processing, completed, failed
- `processed_at`, `attempts`, `error`
- `created_at`

### scheduled_jobs

Jobs scheduled for future execution.

- `id`, `organization_id`, `campaign_id`, `execute_at`, `timezone`, `status`

### notifications

User-visible notifications.

- `id`, `user_id`, `organization_id`, `kind`, `title`, `body`, `read_at`, `created_at`

### inquiries

Public lead form submissions.

- `id`, `organization_id`, `listing_id` nullable
- `name`, `email`, `phone`, `preferred_contact`, `message`, `consent_given`
- `source_page`, `source_ip` (privacy-aware), `created_at`

### audit_events

Immutable audit log.

- `id`, `organization_id`, `user_id` nullable
- `action`, `resource_type`, `resource_id`
- `metadata` JSONB
- `ip_address`, `user_agent`
- `created_at`

## Important constraints

- All FKs use `ON DELETE` behavior appropriate to historical integrity (e.g., listings keep versions; social accounts jobs kept after revoke).
- Unique constraints as listed above.
- Soft deletion: listings use status `archived`; users use `is_active`; social accounts use `revoked_at`.
- Indexes on `(organization_id, status)`, `(organization_id, created_at)`, `(next_retry_at, state)`, `(outbox_events.status, created_at)`, `(social_accounts.organization_id, provider, connection_status)`.
