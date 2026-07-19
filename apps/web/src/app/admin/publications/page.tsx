import { redirect } from 'next/navigation';
import { getCurrentUser } from '@/lib/session';
import { getServerCookieHeader, apiGet } from '@/lib/api';
import type { Organization } from '@/lib/types';
import { AdminPageHeader } from '@/components/admin/page-header';
import { PublicationsClient } from '@/components/publications-client';

export default async function AdminPublicationsPage() {
  const user = await getCurrentUser();
  if (!user) redirect('/login?redirect=/admin/publications');

  const cookieHeader = await getServerCookieHeader();

  let organizations: Organization[] = [];
  try {
    organizations = await apiGet<Organization[]>('/api/v1/organizations', {
      cookies: cookieHeader,
    });
  } catch {
    // empty
  }

  return (
    <div className="space-y-6">
      <AdminPageHeader
        title="Publications"
        description="Approve campaigns and track live posts to Instagram and X across every connected Dream Home Estate account."
      />
      <PublicationsClient organizations={organizations} />
    </div>
  );
}
