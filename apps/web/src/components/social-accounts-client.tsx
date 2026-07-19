'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Instagram, Twitter, Link2, RefreshCw, Trash2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/components/ui/use-toast';
import { apiGet, apiPost, ensureCsrfToken } from '@/lib/api';
import type { Organization, SocialAccount } from '@/lib/types';

interface CallbackParams {
  connected?: string;
  error?: string;
  provider?: string;
}

interface SocialAccountsClientProps {
  organizations: Organization[];
  initialAccounts: SocialAccount[];
  selectedOrgId: string;
  callbackParams: CallbackParams;
}

const PROVIDER_LABELS: Record<string, string> = {
  instagram: 'Instagram',
  x: 'X (Twitter)',
  mock: 'Mock',
};

const PROVIDER_ICONS: Record<string, React.ReactNode> = {
  instagram: <Instagram className="h-5 w-5" />,
  x: <Twitter className="h-5 w-5" />,
  mock: <Link2 className="h-5 w-5" />,
};

const STATUS_COLORS: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  active: 'default',
  revoked: 'destructive',
  expired: 'secondary',
  error: 'destructive',
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function SocialAccountsClient({
  organizations,
  initialAccounts,
  selectedOrgId,
  callbackParams,
}: SocialAccountsClientProps) {
  const router = useRouter();
  const { toast } = useToast();
  const [accounts, setAccounts] = useState<SocialAccount[]>(initialAccounts);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [validating, setValidating] = useState<string | null>(null);
  const [revoking, setRevoking] = useState<string | null>(null);

  // Ensure CSRF cookie exists for users who logged in before it was added
  useEffect(() => {
    void ensureCsrfToken();
  }, []);

  // Show toast based on callback params (only once on mount)
  useEffect(() => {
    if (callbackParams.connected === '1' && callbackParams.provider) {
      const label = PROVIDER_LABELS[callbackParams.provider] ?? callbackParams.provider;
      toast({
        title: 'Account connected',
        description: `Your ${label} account has been connected successfully.`,
      });
    } else if (callbackParams.error) {
      toast({
        title: 'Connection failed',
        description: callbackParams.error,
        variant: 'destructive',
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const refreshAccounts = useCallback(async () => {
    if (!selectedOrgId) return;
    try {
      const data = await apiGet<SocialAccount[]>(
        `/api/v1/organizations/${selectedOrgId}/social-accounts`
      );
      setAccounts(data);
    } catch {
      // silent
    }
  }, [selectedOrgId]);

  const handleConnect = async (provider: string) => {
    setConnecting(provider);
    try {
      await ensureCsrfToken();
      const redirectAfter = `/admin/social-accounts?org_id=${selectedOrgId}`;
      const data = await apiPost<{ authorization_url?: string }>(
        `/api/v1/organizations/${selectedOrgId}/social-accounts/${provider}/connect`,
        { redirect_after: redirectAfter }
      );

      if (data.authorization_url) {
        // Live OAuth only — send the user to Instagram / X
        window.location.href = data.authorization_url;
        return;
      }

      throw new Error('No OAuth authorization URL returned. Check provider credentials.');
    } catch (err) {
      const message =
        err instanceof Error
          ? typeof err.message === 'string'
            ? err.message
            : 'An error occurred'
          : 'An error occurred';
      toast({
        title: 'Connection failed',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setConnecting(null);
    }
  };

  const handleValidate = async (accountId: string) => {
    setValidating(accountId);
    try {
      await ensureCsrfToken();
      await apiPost(
        `/api/v1/organizations/${selectedOrgId}/social-accounts/${accountId}/validate`
      );

      await refreshAccounts();
      toast({ title: 'Validation complete', description: 'Account validated successfully.' });
    } catch (err) {
      toast({
        title: 'Validation failed',
        description: err instanceof Error ? err.message : 'An error occurred',
        variant: 'destructive',
      });
    } finally {
      setValidating(null);
    }
  };

  const handleRevoke = async (accountId: string) => {
    if (!confirm('Are you sure you want to revoke this connection? This action cannot be undone.')) {
      return;
    }
    setRevoking(accountId);
    try {
      await ensureCsrfToken();
      await apiPost(
        `/api/v1/organizations/${selectedOrgId}/social-accounts/${accountId}/revoke`
      );

      await refreshAccounts();
      toast({ title: 'Connection revoked', description: 'Account connection has been revoked.' });
    } catch (err) {
      toast({
        title: 'Revoke failed',
        description: err instanceof Error ? err.message : 'An error occurred',
        variant: 'destructive',
      });
    } finally {
      setRevoking(null);
    }
  };

  const handleOrgChange = (orgId: string) => {
    if (orgId) {
      window.location.href = `/admin/social-accounts?org_id=${orgId}`;
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-border/80 bg-card p-5 shadow-card sm:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">
          Dream Home Estate
        </p>
        <h1 className="mt-1 font-display text-3xl font-semibold tracking-tight">
          Social accounts
        </h1>
        <p className="mt-1.5 max-w-2xl text-sm text-muted-foreground">
          Connect live Instagram Business and X accounts so each dream home can publish to multiple
          profiles in one campaign.
        </p>
      </div>

      {organizations.length > 1 && (
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border/80 bg-card px-3 py-2.5 shadow-sm">
          <label htmlFor="org-select" className="text-sm font-medium text-muted-foreground">
            Organization
          </label>
          <select
            id="org-select"
            className="h-10 min-w-[180px] rounded-xl border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            value={selectedOrgId}
            onChange={(e) => handleOrgChange(e.target.value)}
          >
            {organizations.map((org) => (
              <option key={org.id} value={org.id}>
                {org.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {!selectedOrgId && organizations.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No organizations found</CardTitle>
            <CardDescription>
              You need to be a member of an organization to manage social accounts.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <>
          {/* Connect buttons */}
          <div className="flex flex-wrap gap-3">
            <Button
              onClick={() => handleConnect('instagram')}
              disabled={connecting !== null}
              className="rounded-full bg-accent text-accent-foreground hover:bg-accent/90"
            >
              {connecting === 'instagram' ? (
                <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Instagram className="mr-2 h-4 w-4" />
              )}
              Connect Instagram
            </Button>
            <Button
              variant="outline"
              onClick={() => handleConnect('x')}
              disabled={connecting !== null}
              className="rounded-full"
            >
              {connecting === 'x' ? (
                <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Twitter className="mr-2 h-4 w-4" />
              )}
              Connect X
            </Button>
          </div>

          {/* Account list */}
          {accounts.length === 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>No social accounts connected</CardTitle>
                <CardDescription>
                  Connect your first social media account to start publishing listings.
                </CardDescription>
              </CardHeader>
            </Card>
          ) : (
            <div className="grid gap-4">
              {accounts.map((account) => (
                <Card key={account.id}>
                  <CardContent className="flex items-center gap-4 p-6">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-muted">
                      {PROVIDER_ICONS[account.provider] ?? <Link2 className="h-5 w-5" />}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold truncate">
                          {account.username ?? account.display_name ?? account.provider_account_id}
                        </h3>
                        <Badge variant={STATUS_COLORS[account.connection_status] ?? 'secondary'}>
                          {account.connection_status}
                        </Badge>
                      </div>
                      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                        <span>{PROVIDER_LABELS[account.provider] ?? account.provider}</span>
                        {account.account_type && <span>{account.account_type}</span>}
                        {account.is_default_destination && (
                          <span className="font-medium text-foreground">Default</span>
                        )}
                        <span>Connected {formatDate(account.created_at)}</span>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleValidate(account.id)}
                        disabled={validating !== null}
                      >
                        {validating === account.id ? (
                          <RefreshCw className="mr-1 h-4 w-4 animate-spin" />
                        ) : null}
                        Validate
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRevoke(account.id)}
                        disabled={revoking !== null}
                      >
                        {revoking === account.id ? (
                          <RefreshCw className="mr-1 h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="mr-1 h-4 w-4" />
                        )}
                        Revoke
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
