'use client';

import { useRouter } from 'next/navigation';

import type { Organization } from '@/lib/types';

interface OrgSelectProps {
  organizations: Organization[];
  selectedOrgId: string;
  /** Path prefix without query, e.g. /admin/listings */
  basePath: string;
}

export function OrgSelect({ organizations, selectedOrgId, basePath }: OrgSelectProps) {
  const router = useRouter();

  if (organizations.length <= 1) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border/80 bg-card px-3 py-2.5 shadow-sm">
      <label htmlFor="org-select" className="text-sm font-medium text-muted-foreground">
        Organization
      </label>
      <select
        id="org-select"
        className="h-10 min-w-[180px] rounded-xl border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        value={selectedOrgId}
        onChange={(e) => {
          const id = e.target.value;
          if (id) router.push(`${basePath}?org_id=${id}`);
        }}
      >
        {organizations.map((org) => (
          <option key={org.id} value={org.id}>
            {org.name}
          </option>
        ))}
      </select>
    </div>
  );
}
