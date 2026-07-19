import { redirect } from 'next/navigation';

import { getCurrentUser } from '@/lib/session';
import { AdminPageHeader } from '@/components/admin/page-header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export default async function SettingsPage() {
  const user = await getCurrentUser();
  if (!user) redirect('/login?redirect=/admin/settings');

  return (
    <div className="space-y-6">
      <AdminPageHeader
        title="Settings"
        description="Organization profile and workspace preferences for Dream Home Estate."
      />

      <Card>
        <CardHeader>
          <CardTitle>Organization profile</CardTitle>
          <CardDescription>
            Update how your Dream Home Estate workspace appears publicly.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="max-w-xl space-y-4">
            <div className="space-y-2">
              <Label htmlFor="org-name">Organization name</Label>
              <Input id="org-name" placeholder="Dream Home Estate" defaultValue="Dream Home Estate" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="org-slug">Slug</Label>
              <Input id="org-slug" placeholder="dream-home-estate" />
              <p className="text-xs text-muted-foreground">
                Used in URLs and public-facing links.
              </p>
            </div>
            <Button type="submit" disabled className="rounded-full">
              Save changes (coming soon)
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Notifications</CardTitle>
          <CardDescription>
            Configure alerts for campaign outcomes and connection health.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Notification preferences will be available in a future update.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
