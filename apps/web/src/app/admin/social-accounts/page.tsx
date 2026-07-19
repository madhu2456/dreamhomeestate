import { redirect } from 'next/navigation';

import { getCurrentUser } from '@/lib/session';
import { getServerCookieHeader, apiGet } from '@/lib/api';
import type { Organization, SocialAccount } from '@/lib/types';
import { SocialAccountsClient } from '@/components/social-accounts-client';

interface SocialAccountsPageProps {
  searchParams: Promise<{
    org_id?: string;
    connected?: string;
    error?: string;
    provider?: string;
  }>;
}

export default async function SocialAccountsPage({ searchParams }: SocialAccountsPageProps) {
  const user = await getCurrentUser();
  if (!user) redirect('/login?redirect=/admin/social-accounts');

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

  let accounts: SocialAccount[] = [];
  if (selectedOrgId) {
    try {
      accounts = await apiGet<SocialAccount[]>(
        `/api/v1/organizations/${selectedOrgId}/social-accounts`,
        { cookies: cookieHeader }
      );
    } catch {
      // empty
    }
  }

  const callbackParams = {
    connected: params.connected,
    error: params.error,
    provider: params.provider,
  };

  return (
    <SocialAccountsClient
      organizations={organizations}
      initialAccounts={accounts}
      selectedOrgId={selectedOrgId}
      callbackParams={callbackParams}
    />
  );
}
