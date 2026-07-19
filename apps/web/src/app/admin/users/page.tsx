import { redirect } from 'next/navigation';

import { getCurrentUser } from '@/lib/session';
import { getServerCookieHeader, apiGet } from '@/lib/api';
import type { User } from '@/lib/types';
import { AdminPageHeader } from '@/components/admin/page-header';
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default async function UsersPage() {
  const user = await getCurrentUser();
  if (!user) redirect('/login?redirect=/admin/users');

  let users: User[] = [];
  try {
    const cookieHeader = await getServerCookieHeader();
    users = await apiGet<User[]>('/api/v1/users', {
      cookies: cookieHeader,
    });
  } catch {
    // empty
  }

  return (
    <div className="space-y-6">
      <AdminPageHeader
        title="Users"
        description="Team members with access to Dream Home Estate workspaces and roles."
      />

      {users.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No users found</CardTitle>
            <CardDescription>
              Users appear here once they are created. Use the API or CLI to invite teammates.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-border/80 bg-card shadow-card">
          <table className="w-full text-sm">
            <thead className="border-b border-border/80 bg-muted/40">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Email
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Organizations
                </th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t border-border/60 transition hover:bg-muted/30">
                  <td className="px-4 py-3.5 font-medium">{u.full_name}</td>
                  <td className="px-4 py-3.5 text-muted-foreground">{u.email}</td>
                  <td className="px-4 py-3.5">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        u.is_active
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-muted-foreground">
                    {u.memberships?.map((m) => m.organization.name).join(', ') || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
