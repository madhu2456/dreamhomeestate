'use client';

import { Suspense, useCallback, useEffect, useState } from 'react';
import { useRouter, useParams, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';

import { apiGet, apiPatch, apiPost } from '@/lib/api';
import type { ContentTemplate, Listing, PreviewResponse } from '@/lib/types';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/components/ui/use-toast';

interface FormValues {
  name: string;
  platform: 'instagram' | 'x' | 'mock';
  language: string;
  campaign_tag: string;
  scope: string;
  body_template: string;
  title_template: string;
  variables: string;
  is_default: boolean;
}

function EditTemplateForm() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const orgId = searchParams.get('org_id') ?? '';
  const templateId = params.id as string;
  const { toast } = useToast();

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [previewVarInput, setPreviewVarInput] = useState<string>('{}');
  const [listings, setListings] = useState<Listing[]>([]);
  const [selectedListingId, setSelectedListingId] = useState<string>('');

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors },
  } = useForm<FormValues>();

  const bodyTemplate = watch('body_template');
  const titleTemplate = watch('title_template');
  const platform = watch('platform');

  useEffect(() => {
    async function load() {
      try {
        const [template, orgListings] = await Promise.all([
          apiGet<ContentTemplate>(
            `/api/v1/organizations/${orgId}/content/templates/${templateId}`,
          ),
          apiGet<Listing[]>(`/api/v1/organizations/${orgId}/listings`),
        ]);
        reset({
          name: template.name,
          platform: template.platform,
          language: template.language,
          campaign_tag: template.campaign_tag ?? '',
          scope: template.scope ?? '',
          body_template: template.body_template,
          title_template: template.title_template ?? '',
          variables: (template.variables ?? []).join(', '),
          is_default: template.is_default,
        });
        setListings(orgListings);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load template');
      } finally {
        setLoading(false);
      }
    }
    if (orgId && templateId) load();
  }, [orgId, templateId, reset]);

  async function onSubmit(data: FormValues) {
    setError(null);
    try {
      const variables = data.variables
        .split(',')
        .map((v) => v.trim())
        .filter(Boolean);

      await apiPatch<ContentTemplate>(
        `/api/v1/organizations/${orgId}/content/templates/${templateId}`,
        {
          ...data,
          variables,
          campaign_tag: data.campaign_tag || null,
          scope: data.scope || null,
          title_template: data.title_template || null,
        },
      );
      toast({ title: 'Saved', description: 'Template updated successfully.' });
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update template');
    }
  }

  const handlePreviewWithListing = useCallback(async () => {
    if (!selectedListingId) {
      toast({ title: 'Select a listing', variant: 'destructive' });
      return;
    }
    setError(null);
    try {
      const result = await apiPost<PreviewResponse>(
        `/api/v1/organizations/${orgId}/content/preview`,
        {
          listing_id: selectedListingId,
          template_id: templateId,
        },
      );
      setPreview(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed');
    }
  }, [orgId, templateId, selectedListingId, toast]);

  const handleDryRun = useCallback(async () => {
    setError(null);
    try {
      let variables: Record<string, string> = {};
      try {
        variables = JSON.parse(previewVarInput);
      } catch {
        setError('Preview variables must be valid JSON');
        return;
      }
      const result = await apiPost<PreviewResponse>(
        `/api/v1/organizations/${orgId}/content/preview/dry-run`,
        {
          body_template: bodyTemplate,
          title_template: titleTemplate || null,
          platform,
          variables,
        },
      );
      setPreview(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed');
    }
  }, [orgId, bodyTemplate, titleTemplate, platform, previewVarInput]);

  if (loading) {
    return <p className="text-muted-foreground">Loading template...</p>;
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Edit Template</h1>
        <Button type="submit">Save Changes</Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Template Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input id="name" {...register('name', { required: true })} />
              {errors.name && <p className="text-xs text-destructive">Required</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="platform">Platform</Label>
              <select
                id="platform"
                {...register('platform')}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="mock">Mock</option>
                <option value="instagram">Instagram</option>
                <option value="x">X / Twitter</option>
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="language">Language</Label>
              <Input id="language" {...register('language')} />
            </div>

            <div className="space-y-2">
              <Label htmlFor="campaign_tag">Campaign Tag</Label>
              <Input id="campaign_tag" {...register('campaign_tag')} />
            </div>

            <div className="space-y-2">
              <Label htmlFor="scope">Scope</Label>
              <Input id="scope" {...register('scope')} />
            </div>

            <div className="space-y-2">
              <Label htmlFor="variables">
                Variables <span className="text-xs text-muted-foreground">(comma separated)</span>
              </Label>
              <Input id="variables" {...register('variables')} />
            </div>

            <div className="flex items-center gap-2">
              <input type="checkbox" id="is_default" {...register('is_default')} />
              <Label htmlFor="is_default">Set as default template</Label>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Templates</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title_template">Title Template</Label>
              <Textarea
                id="title_template"
                {...register('title_template')}
                rows={2}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="body_template">Body Template</Label>
              <Textarea
                id="body_template"
                {...register('body_template', { required: true })}
                rows={8}
              />
              {errors.body_template && (
                <p className="text-xs text-destructive">Required</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Preview</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-end gap-4">
            <div className="flex-1 space-y-2">
              <Label htmlFor="preview-listing">Preview with Listing</Label>
              <select
                id="preview-listing"
                value={selectedListingId}
                onChange={(e) => setSelectedListingId(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="">Select a listing...</option>
                {listings.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.title}
                  </option>
                ))}
              </select>
            </div>
            <Button type="button" variant="outline" onClick={handlePreviewWithListing}>
              Preview with Listing
            </Button>
          </div>

          <div className="space-y-2">
            <Label>Quick Preview Variables (JSON)</Label>
            <div className="flex gap-2">
              <Textarea
                value={previewVarInput}
                onChange={(e) => setPreviewVarInput(e.target.value)}
                rows={2}
                className="flex-1 font-mono text-xs"
              />
              <Button type="button" variant="outline" onClick={handleDryRun}>
                Preview
              </Button>
            </div>
          </div>

          {preview && (
            <div className="space-y-4">
              {preview.errors.length > 0 && (
                <Alert variant="destructive">
                  <AlertDescription>{preview.errors.join(', ')}</AlertDescription>
                </Alert>
              )}

              {preview.title && (
                <div>
                  <Label>Title</Label>
                  <div className="mt-1 rounded-md border bg-muted p-3">
                    <p className="text-sm">{preview.title}</p>
                  </div>
                </div>
              )}

              <div>
                <div className="flex items-center justify-between">
                  <Label>Body</Label>
                  <span
                    className={`text-xs ${
                      preview.length_exceeded
                        ? 'text-destructive font-bold'
                        : 'text-muted-foreground'
                    }`}
                  >
                    {preview.length}
                    {preview.max_length != null ? ` / ${preview.max_length}` : ''} chars
                    {preview.length_exceeded ? ' (exceeded!)' : ''}
                  </span>
                </div>
                <div className="mt-1 rounded-md border bg-muted p-3">
                  <p className="whitespace-pre-wrap text-sm">{preview.body}</p>
                </div>
              </div>

              {preview.warnings.length > 0 && (
                <div>
                  <Label>Warnings</Label>
                  <ul className="mt-1 list-inside list-disc text-sm text-muted-foreground">
                    {preview.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </form>
  );
}

export default function EditTemplatePage() {
  return (
    <Suspense fallback={<p>Loading...</p>}>
      <EditTemplateForm />
    </Suspense>
  );
}
