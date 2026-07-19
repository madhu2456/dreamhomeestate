'use client';

import { useCallback, useEffect, useState } from 'react';
import { ImagePlus, Loader2, Send, Video } from 'lucide-react';

import { apiGet, apiPost, ensureCsrfToken } from '@/lib/api';
import type { Organization, SocialAccount } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/components/ui/use-toast';

interface MediaItem {
  id: string;
  kind: string;
  public_url: string;
  original_file_name?: string;
}

interface ComposeClientProps {
  organizations: Organization[];
}

export function ComposeClient({ organizations }: ComposeClientProps) {
  const { toast } = useToast();
  const [orgId, setOrgId] = useState(organizations[0]?.id ?? '');
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);
  const [library, setLibrary] = useState<MediaItem[]>([]);
  const [selectedMedia, setSelectedMedia] = useState<string[]>([]);
  const [body, setBody] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [publishing, setPublishing] = useState(false);

  const load = useCallback(async () => {
    if (!orgId) return;
    setLoading(true);
    try {
      const [acc, media] = await Promise.all([
        apiGet<SocialAccount[]>(`/api/v1/organizations/${orgId}/social-accounts`),
        apiGet<MediaItem[]>(`/api/v1/organizations/${orgId}/media-library`),
      ]);
      const active = (acc || []).filter(
        (a) => a.connection_status === 'active' && (a.provider === 'instagram' || a.provider === 'x')
      );
      setAccounts(active);
      setSelectedAccounts(active.map((a) => a.id));
      setLibrary(media || []);
    } catch (err) {
      toast({
        title: 'Failed to load',
        description: err instanceof Error ? err.message : 'Error',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [orgId, toast]);

  useEffect(() => {
    void load();
  }, [load]);

  const toggleAccount = (id: string) => {
    setSelectedAccounts((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const toggleMedia = (url: string) => {
    setSelectedMedia((prev) =>
      prev.includes(url) ? prev.filter((x) => x !== url) : [...prev, url].slice(0, 10)
    );
  };

  const onUpload = async (fileList: FileList | null) => {
    if (!fileList?.length || !orgId) return;
    setUploading(true);
    try {
      const csrf = await ensureCsrfToken();
      for (const file of Array.from(fileList)) {
        const form = new FormData();
        form.append('file', file);
        const res = await fetch(`/api/v1/organizations/${orgId}/media-library/upload`, {
          method: 'POST',
          body: form,
          credentials: 'include',
          headers: csrf ? { 'X-CSRF-Token': csrf } : {},
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(
            typeof body.detail === 'string' ? body.detail : 'Upload failed'
          );
        }
        const item = (await res.json()) as MediaItem;
        setLibrary((prev) => [item, ...prev]);
        setSelectedMedia((prev) => [...prev, item.public_url].slice(0, 10));
      }
      toast({ title: 'Uploaded', description: 'Media added to library and selected.' });
    } catch (err) {
      toast({
        title: 'Upload failed',
        description: err instanceof Error ? err.message : 'Error',
        variant: 'destructive',
      });
    } finally {
      setUploading(false);
    }
  };

  const publish = async () => {
    if (!orgId || selectedAccounts.length === 0) {
      toast({ title: 'Select accounts', variant: 'destructive' });
      return;
    }
    if (!body.trim() && selectedMedia.length === 0) {
      toast({ title: 'Add caption or media', variant: 'destructive' });
      return;
    }
    setPublishing(true);
    try {
      const campaign = await apiPost<{ id: string; jobs: unknown[] }>(
        `/api/v1/organizations/${orgId}/publications/quick-posts`,
        {
          body: body.trim(),
          media_urls: selectedMedia,
          social_account_ids: selectedAccounts,
          auto_distribute: false,
        }
      );
      toast({
        title: 'Campaign created',
        description: `Created for ${selectedAccounts.length} account(s). Approve jobs under Publications.`,
      });
      window.location.href = `/admin/publications?highlight=${campaign.id}`;
    } catch (err) {
      toast({
        title: 'Publish failed',
        description: err instanceof Error ? err.message : 'Error',
        variant: 'destructive',
      });
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">Compose</p>
        <h1 className="mt-1 font-display text-3xl font-semibold tracking-tight">Quick Post</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Post images, posters, video, and caption to multiple Instagram (and X) accounts at once —
          no listing required.
        </p>
      </div>

      {organizations.length > 1 && (
        <div className="flex items-center gap-2">
          <Label htmlFor="compose-org">Organization</Label>
          <select
            id="compose-org"
            className="h-10 rounded-xl border border-input bg-background px-3 text-sm"
            value={orgId}
            onChange={(e) => setOrgId(e.target.value)}
          >
            {organizations.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>1. Caption</CardTitle>
          <CardDescription>Instagram limit 2,200 characters. Text-only feed posts need media.</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={5}
            maxLength={2200}
            placeholder="Write your caption, hashtags, offer…"
            className="rounded-xl"
          />
          <p className="mt-1 text-right text-xs text-muted-foreground">{body.length}/2200</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>2. Media library</CardTitle>
            <CardDescription>Posters, photos, or video (mp4). Select up to 10.</CardDescription>
          </div>
          <label className="inline-flex cursor-pointer items-center gap-2">
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/webm"
              multiple
              className="hidden"
              onChange={(e) => void onUpload(e.target.files)}
              disabled={uploading}
            />
            <Button type="button" variant="outline" size="sm" asChild disabled={uploading}>
              <span>
                {uploading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <ImagePlus className="mr-2 h-4 w-4" />
                )}
                Upload
              </span>
            </Button>
          </label>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : library.length === 0 ? (
            <p className="text-sm text-muted-foreground">No media yet — upload a poster or video.</p>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
              {library.map((item) => {
                const selected = selectedMedia.includes(item.public_url);
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => toggleMedia(item.public_url)}
                    className={`relative overflow-hidden rounded-xl border-2 text-left transition ${
                      selected ? 'border-accent ring-2 ring-accent/30' : 'border-border'
                    }`}
                  >
                    {item.kind === 'video' ? (
                      <div className="flex aspect-square items-center justify-center bg-muted">
                        <Video className="h-8 w-8 text-muted-foreground" />
                      </div>
                    ) : (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={item.public_url}
                        alt={item.original_file_name || 'media'}
                        className="aspect-square w-full object-cover"
                      />
                    )}
                    <span className="block truncate px-2 py-1 text-[11px] text-muted-foreground">
                      {item.kind}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
          {selectedMedia.length > 0 && (
            <p className="mt-3 text-xs text-muted-foreground">
              Selected {selectedMedia.length} media item(s)
              <button
                type="button"
                className="ml-2 text-destructive underline"
                onClick={() => setSelectedMedia([])}
              >
                Clear
              </button>
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>3. Accounts</CardTitle>
          <CardDescription>Post to multiple Instagram / X accounts in one campaign.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {accounts.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No active accounts. Connect Instagram under Social accounts first.
            </p>
          ) : (
            accounts.map((a) => (
              <label
                key={a.id}
                className="flex cursor-pointer items-center gap-3 rounded-xl border border-border/80 px-3 py-2.5 hover:bg-muted/40"
              >
                <input
                  type="checkbox"
                  checked={selectedAccounts.includes(a.id)}
                  onChange={() => toggleAccount(a.id)}
                  className="h-4 w-4 rounded border-input"
                />
                <span className="text-sm font-medium capitalize">{a.provider}</span>
                <span className="text-sm text-muted-foreground">
                  @{a.username || a.display_name || a.provider_account_id}
                </span>
              </label>
            ))
          )}
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-3">
        <Button
          type="button"
          className="rounded-full bg-accent text-accent-foreground"
          disabled={publishing || loading}
          onClick={() => void publish()}
        >
          {publishing ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Send className="mr-2 h-4 w-4" />
          )}
          Create multi-account campaign
        </Button>
        <Button type="button" variant="outline" className="rounded-full" asChild>
          <a href="/admin/publications">View publications</a>
        </Button>
      </div>
    </div>
  );
}
