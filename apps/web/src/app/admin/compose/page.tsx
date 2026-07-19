import { getCurrentUser } from '@/lib/session';
import { apiGet, getServerCookieHeader } from '@/lib/api';
import type { Organization } from '@/lib/types';
import { ComposeClient } from '@/components/compose-client';
import { redirect } from 'next/navigation';

export default async function ComposePage() {
  const user = await getCurrentUser();
  if (!user) redirect('/login?redirect=/admin/compose');

  const cookies = await getServerCookieHeader();
  let organizations: Organization[] = [];
  try {
    organizations = await apiGet<Organization[]>('/api/v1/organizations', { cookies });
  } catch {
    organizations = [];
  }

  if (!organizations.length) {
    return (
      <div className="rounded-2xl border border-border bg-card p-8 text-center">
        <p className="text-muted-foreground">No organization found. Create one first.</p>
      </div>
    );
  }

  return <ComposeClient organizations={organizations} />;
}
