import { render, screen, waitFor } from '@testing-library/react';
import { PublicationsClient } from '@/components/publications-client';
import type { Organization, PublicationCampaign } from '@/lib/types';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

jest.mock('@/lib/api', () => ({
  apiGet: jest.fn(),
  apiPost: jest.fn(),
}));

jest.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn(),
    dismiss: jest.fn(),
    toasts: [],
  }),
}));

import { apiGet } from '@/lib/api';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockOrganizations: Organization[] = [
  { id: 'org-1', name: 'Test Org', slug: 'test-org' },
  { id: 'org-2', name: 'Second Org', slug: 'second-org' },
];

function buildCampaign(
  overrides: Partial<PublicationCampaign> = {},
): PublicationCampaign {
  return {
    id: 'campaign-1',
    organization_id: 'org-1',
    listing_id: 'listing-abc-12345',
    listing_version_id: null,
    created_by: 'user-1',
    status: 'published',
    auto_distribute: false,
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-01-15T12:00:00Z',
    jobs: [
      {
        id: 'job-1',
        campaign_id: 'campaign-1',
        social_account_id: 'social-abc-123',
        template_id: null,
        idempotency_key: 'ik-1',
        status: 'published',
        rendered_title: null,
        rendered_body: 'Stylish 2BHK in downtown.',
        media_urls: [],
        scheduled_at: null,
        approved_at: '2025-01-15T11:00:00Z',
        approved_by: 'admin-1',
        published_at: '2025-01-15T11:30:00Z',
        provider_job_id: 'ext-123',
        error_code: null,
        error_message: null,
        retry_count: 0,
        max_retries: 3,
        created_at: '2025-01-15T10:00:00Z',
        updated_at: '2025-01-15T11:30:00Z',
      },
    ],
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('PublicationsClient', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders a loading indicator while campaigns are being fetched', () => {
    // Never-resolving promise so we stay in loading state forever
    (apiGet as jest.Mock).mockReturnValue(new Promise(() => {}));

    render(<PublicationsClient organizations={mockOrganizations} />);

    expect(screen.getByText('0 campaigns')).toBeInTheDocument();
    // The Refresh button icon spins during loading
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders campaign cards when API returns data', async () => {
    (apiGet as jest.Mock).mockResolvedValue([buildCampaign()]);

    render(<PublicationsClient organizations={mockOrganizations} />);

    await waitFor(() => {
      expect(screen.getByText('1 campaign')).toBeInTheDocument();
    });

    expect(screen.getByText('Campaign')).toBeInTheDocument();
    expect(screen.getByText('Published')).toBeInTheDocument();
    expect(screen.getByText('1 job')).toBeInTheDocument();
    // rendered_body inside the job row
    expect(screen.getByText('Stylish 2BHK in downtown.')).toBeInTheDocument();
  });

  it('shows an error card when the API call fails', async () => {
    (apiGet as jest.Mock).mockRejectedValue(new Error('Network error'));

    render(<PublicationsClient organizations={mockOrganizations} />);

    await waitFor(() => {
      expect(
        screen.getByText('Error loading campaigns'),
      ).toBeInTheDocument();
    });

    expect(screen.getByText('Network error')).toBeInTheDocument();
  });

  it('shows an empty-state card when the org has zero campaigns', async () => {
    (apiGet as jest.Mock).mockResolvedValue([]);

    render(<PublicationsClient organizations={mockOrganizations} />);

    await waitFor(() => {
      expect(screen.getByText('No campaigns yet')).toBeInTheDocument();
    });
  });

  it('renders an org selector when multiple organizations are provided', () => {
    (apiGet as jest.Mock).mockResolvedValue([]);

    render(<PublicationsClient organizations={mockOrganizations} />);

    expect(screen.getByLabelText('Organization:')).toBeInTheDocument();
    expect(screen.getByText('Test Org')).toBeInTheDocument();
    expect(screen.getByText('Second Org')).toBeInTheDocument();
  });

  it('hides the org selector when only one organization exists', () => {
    (apiGet as jest.Mock).mockResolvedValue([]);

    render(
      <PublicationsClient organizations={[mockOrganizations[0]]} />,
    );

    expect(
      screen.queryByLabelText('Organization:'),
    ).not.toBeInTheDocument();
  });

  it('displays Pending Approval jobs with accept/reject action buttons', async () => {
    const campaign = buildCampaign();
    campaign.jobs[0].status = 'pending_approval';

    (apiGet as jest.Mock).mockResolvedValue([campaign]);

    render(<PublicationsClient organizations={mockOrganizations} />);

    await waitFor(() => {
      expect(screen.getByText('Pending Approval')).toBeInTheDocument();
    });

    expect(screen.getByText('Approve')).toBeInTheDocument();
    expect(screen.getByText('Reject')).toBeInTheDocument();
  });
});
