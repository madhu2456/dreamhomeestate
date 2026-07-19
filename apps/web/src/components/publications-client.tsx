'use client';

import { useEffect, useState, useCallback } from 'react';
import { Send, Loader2, RefreshCw, CheckCircle2, XCircle, RotateCcw, Ban, AlertCircle } from 'lucide-react';

import type { Organization, PublicationCampaign, PublicationJob, JobActionResponse, JobStatus } from '@/lib/types';
import { apiGet, apiPost } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/components/ui/use-toast';

const STATUS_LABELS: Record<JobStatus, string> = {
  pending_approval: 'Pending Approval',
  approved: 'Approved',
  rejected: 'Rejected',
  queued: 'Queued',
  publishing: 'Publishing',
  published: 'Published',
  failed: 'Failed',
  cancelled: 'Cancelled',
};

const STATUS_VARIANTS: Record<JobStatus, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  pending_approval: 'secondary',
  approved: 'default',
  rejected: 'destructive',
  queued: 'outline',
  publishing: 'default',
  published: 'default',
  failed: 'destructive',
  cancelled: 'outline',
};

function getAvailableActions(status: JobStatus) {
  const actions: { label: string; action: string; icon: React.ReactNode; variant: 'default' | 'destructive' | 'outline' | 'secondary' }[] = [];
  if (status === 'pending_approval') {
    actions.push({ label: 'Approve', action: 'approve', icon: <CheckCircle2 className="h-3.5 w-3.5" />, variant: 'default' });
    actions.push({ label: 'Reject', action: 'reject', icon: <XCircle className="h-3.5 w-3.5" />, variant: 'destructive' });
  }
  if (status === 'queued' || status === 'approved') {
    actions.push({ label: 'Cancel', action: 'cancel', icon: <Ban className="h-3.5 w-3.5" />, variant: 'outline' });
  }
  if (status === 'failed') {
    actions.push({ label: 'Retry', action: 'retry', icon: <RotateCcw className="h-3.5 w-3.5" />, variant: 'default' });
  }
  return actions;
}

interface PublicationsClientProps {
  organizations: Organization[];
}

export function PublicationsClient({ organizations }: PublicationsClientProps) {
  const [selectedOrgId, setSelectedOrgId] = useState(organizations[0]?.id ?? '');
  const [campaigns, setCampaigns] = useState<PublicationCampaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const { toast } = useToast();

  const fetchCampaigns = useCallback(async () => {
    if (!selectedOrgId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<PublicationCampaign[]>(
        `/api/v1/organizations/${selectedOrgId}/publications/campaigns`,
      );
      setCampaigns(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load campaigns');
    } finally {
      setLoading(false);
    }
  }, [selectedOrgId]);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  const performAction = async (jobId: string, action: string) => {
    setActionLoading(`${jobId}-${action}`);
    try {
      const result = await apiPost<JobActionResponse>(
        `/api/v1/organizations/${selectedOrgId}/publications/jobs/${jobId}/${action}`,
      );
      toast({
        title: result.message,
        description: `Job status: ${STATUS_LABELS[result.status]}`,
      });
      fetchCampaigns();
    } catch (err) {
      toast({
        title: 'Action failed',
        description: err instanceof Error ? err.message : 'Something went wrong',
        variant: 'destructive',
      });
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      {organizations.length > 1 && (
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border/80 bg-card px-3 py-2.5 shadow-sm">
          <label htmlFor="pub-org-select" className="text-sm font-medium text-muted-foreground">
            Organization
          </label>
          <select
            id="pub-org-select"
            className="h-10 min-w-[180px] rounded-xl border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            value={selectedOrgId}
            onChange={(e) => setSelectedOrgId(e.target.value)}
          >
            {organizations.map((org) => (
              <option key={org.id} value={org.id}>
                {org.name}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {campaigns.length} campaign{campaigns.length !== 1 ? 's' : ''}
        </p>
        <Button variant="outline" size="sm" className="rounded-full" onClick={fetchCampaigns} disabled={loading}>
          <RefreshCw className={`mr-2 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {loading && campaigns.length === 0 ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-destructive" />
              <CardTitle className="text-base">Error loading campaigns</CardTitle>
            </div>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
        </Card>
      ) : campaigns.length === 0 ? (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Send className="h-5 w-5 text-muted-foreground" />
              <CardTitle className="text-base">No campaigns yet</CardTitle>
            </div>
            <CardDescription>
              Create a campaign from a listing to start publishing. Go to Listings to create one.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="space-y-4">
          {campaigns.map((campaign) => (
            <CampaignCard
              key={campaign.id}
              campaign={campaign}
              onAction={performAction}
              actionLoading={actionLoading}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function CampaignCard({
  campaign,
  onAction,
  actionLoading,
}: {
  campaign: PublicationCampaign;
  onAction: (jobId: string, action: string) => Promise<void>;
  actionLoading: string | null;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-base">Campaign</CardTitle>
            <Badge variant={STATUS_VARIANTS[campaign.status]}>
              {STATUS_LABELS[campaign.status]}
            </Badge>
            <Badge variant="outline" className="ml-1">
              {campaign.jobs.length} job{campaign.jobs.length !== 1 ? 's' : ''}
            </Badge>
          </div>
          <span className="text-xs text-muted-foreground">
            {new Date(campaign.created_at).toLocaleDateString()}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>Listing: {campaign.listing_id.slice(0, 8)}...</span>
          {campaign.auto_distribute && (
            <Badge variant="secondary" className="text-[10px]">
              auto-distribute
            </Badge>
          )}
        </div>
      </CardHeader>
      {campaign.jobs.length > 0 && (
        <CardContent>
          <div className="space-y-2">
            {campaign.jobs.map((job) => (
              <JobRow
                key={job.id}
                job={job}
                onAction={onAction}
                actionLoading={actionLoading}
              />
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  );
}

function JobRow({
  job,
  onAction,
  actionLoading,
}: {
  job: PublicationJob;
  onAction: (jobId: string, action: string) => Promise<void>;
  actionLoading: string | null;
}) {
  const actions = getAvailableActions(job.status);

  return (
    <div className="rounded-lg border bg-muted/30 p-3">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium">
              Social Account: {job.social_account_id.slice(0, 8)}...
            </span>
            <Badge variant={STATUS_VARIANTS[job.status]}>
              {STATUS_LABELS[job.status]}
            </Badge>
            {job.error_code && (
              <Badge variant="destructive" className="text-[10px]">
                {job.error_code}
              </Badge>
            )}
          </div>
          {job.rendered_body && (
            <p className="mt-1 truncate text-xs text-muted-foreground">
              {job.rendered_body}
            </p>
          )}
          {job.error_message && (
            <p className="mt-1 text-xs text-destructive">{job.error_message}</p>
          )}
          {job.retry_count > 0 && (
            <p className="mt-1 text-xs text-muted-foreground">
              Retry {job.retry_count}/{job.max_retries}
            </p>
          )}
        </div>
        {actions.length > 0 && (
          <div className="flex shrink-0 items-center gap-1">
            {actions.map((btn) => (
              <Button
                key={btn.action}
                variant={btn.variant}
                size="sm"
                onClick={() => onAction(job.id, btn.action)}
                disabled={actionLoading === `${job.id}-${btn.action}`}
              >
                {actionLoading === `${job.id}-${btn.action}` ? (
                  <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                ) : (
                  btn.icon
                )}
                <span className="ml-1">{btn.label}</span>
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
