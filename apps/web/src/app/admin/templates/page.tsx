import { redirect } from 'next/navigation';
import Link from 'next/link';
import { FileText, Plus } from 'lucide-react';

import { getCurrentUser } from '@/lib/session';
import { getServerCookieHeader, apiGet } from '@/lib/api';
import type { ContentTemplate, Organization } from '@/lib/types';
import { AdminPageHeader } from '@/components/admin/page-header';
import { OrgSelect } from '@/components/admin/org-select';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default async function AdminTemplatesPage({
  searchParams,
}: {
  searchParams: Promise<{ org_id?: string }>;
}) {
  const user = await getCurrentUser();
  if (!user) redirect('/login?redirect=/admin/templates');

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

  let templates: ContentTemplate[] = [];
  if (selectedOrgId) {
    try {
      templates = await apiGet<ContentTemplate[]>(
        `/api/v1/organizations/${selectedOrgId}/content/templates`,
        { cookies: cookieHeader },
      );
    } catch {
      // empty
    }
  }

  return (
    <div className="space-y-6">
      <AdminPageHeader
        title="Content templates"
        description="Write platform-aware captions for Instagram and X using listing variables."
        actions={
          selectedOrgId ? (
            <Button asChild className="rounded-full bg-accent text-accent-foreground hover:bg-accent/90">
              <Link href={`/admin/templates/new?org_id=${selectedOrgId}`}>
                <Plus className="mr-2 h-4 w-4" />
                New template
              </Link>
            </Button>
          ) : undefined
        }
      />

      <OrgSelect
        organizations={organizations}
        selectedOrgId={selectedOrgId}
        basePath="/admin/templates"
      />

      {!selectedOrgId && organizations.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No organizations found</CardTitle>
            <CardDescription>
              You need to be a member of an organization to manage content templates.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : templates.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No templates yet</CardTitle>
            <CardDescription>
              Create your first template so Dream Home Estate can generate social posts from listings.
            </CardDescription>
          </CardHeader>
          {selectedOrgId && (
            <CardContent>
              <Button asChild className="rounded-full bg-accent text-accent-foreground hover:bg-accent/90">
                <Link href={`/admin/templates/new?org_id=${selectedOrgId}`}>
                  <Plus className="mr-2 h-4 w-4" />
                  New template
                </Link>
              </Button>
            </CardContent>
          )}
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {templates.map((template) => (
            <Link
              key={template.id}
              href={`/admin/templates/${template.id}/edit?org_id=${selectedOrgId}`}
              className="group"
            >
              <Card className="h-full transition duration-300 group-hover:-translate-y-0.5 group-hover:border-accent/30 group-hover:shadow-soft">
                <CardHeader>
                  <div className="flex items-center justify-between gap-2">
                    <CardTitle className="text-lg">{template.name}</CardTitle>
                    <FileText className="h-4 w-4 text-muted-foreground" />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">{template.platform}</Badge>
                    {template.is_default && <Badge>default</Badge>}
                  </div>
                  {template.scope && (
                    <p className="mt-2 text-xs text-muted-foreground">{template.scope}</p>
                  )}
                  <p className="mt-2 text-xs text-muted-foreground">
                    v{template.version} · {template.language.toUpperCase()}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
