'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Check, ImagePlus, Loader2, Send, Trash2, Video, X } from 'lucide-react';

import { apiDelete, apiGet, apiPost, ensureCsrfToken } from '@/lib/api';
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
  /** Selected media library item IDs (order = publish order) */
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [body, setBody] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [publishing, setPublishing] = useState(false);

  const libraryById = useMemo(() => {
    const map = new Map<string, MediaItem>();
    for (const item of library) map.set(item.id, item);
    return map;
  }, [library]);

  const selectedMediaItems = useMemo(
    () => selectedIds.map((id) => libraryById.get(id)).filter(Boolean) as MediaItem[],
    [selectedIds, libraryById]
  );

  const selectedMediaUrls = useMemo(
    () => selectedMediaItems.map((m) => m.public_url).filter(Boolean),
    [selectedMediaItems]
  );

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
      // Drop selections that no longer exist in the library
      setSelectedIds((prev) => {
        const ids = new Set((media || []).map((m) => m.id));
        return prev.filter((id) => ids.has(id));
      });
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

  const toggleMedia = (id: string) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((x) => x !== id);
      }
      if (prev.length >= 10) {
        toast({
          title: 'Limit reached',
          description: 'You can select up to 10 media items.',
          variant: 'destructive',
        });
        return prev;
      }
      return [...prev, id];
    });
  };

  const clearSelection = () => {
    setSelectedIds([]);
  };

  const removeFromSelection = (id: string) => {
    setSelectedIds((prev) => prev.filter((x) => x !== id));
  };

  const deleteFromLibrary = async (item: MediaItem) => {
    if (!orgId) return;
    const ok = window.confirm(
      `Remove “${item.original_file_name || item.kind}” from the media library? This cannot be undone.`
    );
    if (!ok) return;

    setDeletingId(item.id);
    try {
      await ensureCsrfToken();
      await apiDelete(`/api/v1/organizations/${orgId}/media-library/${item.id}`);
      setLibrary((prev) => prev.filter((m) => m.id !== item.id));
      setSelectedIds((prev) => prev.filter((id) => id !== item.id));
      toast({ title: 'Removed', description: 'Media deleted from library.' });
    } catch (err) {
      toast({
        title: 'Delete failed',
        description: err instanceof Error ? err.message : 'Error',
        variant: 'destructive',
      });
    } finally {
      setDeletingId(null);
    }
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
          const errBody = await res.json().catch(() => ({}));
          throw new Error(
            typeof errBody.detail === 'string' ? errBody.detail : 'Upload failed'
          );
        }
        const item = (await res.json()) as MediaItem;
        setLibrary((prev) => [item, ...prev]);
        setSelectedIds((prev) => {
          if (prev.includes(item.id) || prev.length >= 10) return prev;
          return [...prev, item.id];
        });
      }
      toast({ title: 'Uploaded', description: 'Media added and selected for this post.' });
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
    if (!body.trim() && selectedMediaUrls.length === 0) {
      toast({ title: 'Add caption or media', variant: 'destructive' });
      return;
    }
    const hasInstagram = accounts.some(
      (a) => selectedAccounts.includes(a.id) && a.provider === 'instagram'
    );
    if (hasInstagram && selectedMediaUrls.length === 0) {
      toast({
        title: 'Image or video required for Instagram',
        description:
          'Instagram cannot publish text-only posts. Upload a poster/photo, select it, then publish.',
        variant: 'destructive',
      });
      return;
    }
    setPublishing(true);
    try {
      const campaign = await apiPost<{ id: string; jobs: unknown[] }>(
        `/api/v1/organizations/${orgId}/publications/quick-posts`,
        {
          body: body.trim(),
          media_urls: selectedMediaUrls,
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
          <CardDescription>
            Instagram limit 2,200 characters. Instagram always needs at least one image or video
            (text-only is not allowed by Instagram&apos;s API).
          </CardDescription>
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
        <CardHeader className="flex flex-row items-center justify-between space-y-0 gap-3">
          <div>
            <CardTitle>2. Media library</CardTitle>
            <CardDescription>
              Click a tile to select/deselect (max 10). Use the trash icon to delete from the library.
            </CardDescription>
          </div>
          <label className="inline-flex cursor-pointer items-center gap-2 shrink-0">
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/webm"
              multiple
              className="hidden"
              onChange={(e) => {
                void onUpload(e.target.files);
                e.target.value = '';
              }}
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
        <CardContent className="space-y-4">
          {/* Selected for this post */}
          {selectedMediaItems.length > 0 && (
            <div className="rounded-xl border border-accent/40 bg-accent/5 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="text-sm font-medium">
                  Selected for this post ({selectedMediaItems.length}/10)
                </p>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-8 text-destructive hover:text-destructive"
                  onClick={clearSelection}
                >
                  Clear selection
                </Button>
              </div>
              <div className="flex flex-wrap gap-2">
                {selectedMediaItems.map((item, index) => (
                  <div
                    key={item.id}
                    className="relative h-16 w-16 overflow-hidden rounded-lg border border-border bg-muted"
                  >
                    {item.kind === 'video' ? (
                      <div className="flex h-full items-center justify-center">
                        <Video className="h-5 w-5 text-muted-foreground" />
                      </div>
                    ) : (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={item.public_url}
                        alt=""
                        className="h-full w-full object-cover"
                      />
                    )}
                    <span className="absolute left-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-accent text-[10px] font-bold text-accent-foreground">
                      {index + 1}
                    </span>
                    <button
                      type="button"
                      className="absolute right-0.5 top-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-background/90 text-foreground shadow"
                      onClick={(e) => {
                        e.stopPropagation();
                        removeFromSelection(item.id);
                      }}
                      aria-label="Remove from selection"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {loading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : library.length === 0 ? (
            <p className="text-sm text-muted-foreground">No media yet — upload a poster or video.</p>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
              {library.map((item) => {
                const selected = selectedIds.includes(item.id);
                const order = selected ? selectedIds.indexOf(item.id) + 1 : null;
                return (
                  <div
                    key={item.id}
                    className={`relative overflow-hidden rounded-xl border-2 text-left transition ${
                      selected ? 'border-accent ring-2 ring-accent/30' : 'border-border'
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => toggleMedia(item.id)}
                      className="block w-full focus-ring"
                      aria-pressed={selected}
                      aria-label={selected ? 'Deselect media' : 'Select media'}
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
                      <span className="flex items-center justify-between gap-1 truncate px-2 py-1 text-[11px] text-muted-foreground">
                        <span className="truncate">{item.kind}</span>
                        {selected && (
                          <span className="inline-flex items-center gap-0.5 text-accent">
                            <Check className="h-3 w-3" />
                            {order}
                          </span>
                        )}
                      </span>
                    </button>
                    <button
                      type="button"
                      className="absolute right-1.5 top-1.5 flex h-7 w-7 items-center justify-center rounded-lg bg-background/90 text-destructive shadow hover:bg-destructive hover:text-destructive-foreground disabled:opacity-50"
                      onClick={(e) => {
                        e.stopPropagation();
                        void deleteFromLibrary(item);
                      }}
                      disabled={deletingId === item.id}
                      aria-label="Delete from library"
                      title="Delete from library"
                    >
                      {deletingId === item.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </div>
                );
              })}
            </div>
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
