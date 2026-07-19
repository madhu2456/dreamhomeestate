import { redirect } from 'next/navigation';
import { Building2 } from 'lucide-react';

import { getCurrentUser } from '@/lib/session';
import { getServerCookieHeader, apiGet } from '@/lib/api';
import type { Organization } from '@/lib/types';
import { AdminPageHeader } from '@/components/admin/page-header';
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default async function OrganizationsPage() {
  const user = await getCurrentUser();
  if (!user) redirect('/login?redirect=/admin/organizations');

  let organizations: Organization[] = [];
  try {
    const cookieHeader = await getServerCookieHeader();
    organizations = await apiGet<Organization[]>('/api/v1/organizations', {
      cookies: cookieHeader,
    });
  } catch {
    // empty
  }

  return (
    <div className="space-y-6">
      <AdminPageHeader
        title="Organizations"
        description="Workspaces that own listings, social accounts, templates, and campaigns for Dream Home Estate."
      />

      {organizations.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No organizations yet</CardTitle>
            <CardDescription>
              Ask an owner to add you to a Dream Home Estate workspace, or create one via the API /
              CLI.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {organizations.map((org) => (
            <Card
              key={org.id}
              className="transition duration-300 hover:border-accent/30 hover:shadow-soft"
            >
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                  <Building2 className="h-5 w-5" />
                </div>
                <CardTitle className="text-lg">{org.name}</CardTitle>
                <CardDescription className="font-mono text-xs">{org.slug}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
