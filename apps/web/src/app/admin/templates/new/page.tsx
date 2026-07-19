'use client';

import { Suspense, useCallback, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';

import { apiPost } from '@/lib/api';
import type { ContentTemplate, PreviewResponse } from '@/lib/types';
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

function NewTemplateForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const orgId = searchParams.get('org_id') ?? '';
  const { toast } = useToast();
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [previewVars, setPreviewVars] = useState<string>('{}');

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    defaultValues: {
      name: '',
      platform: 'mock',
      language: 'en',
      campaign_tag: '',
      scope: '',
      body_template: '{{ title }} - {{ price_formatted }}',
      title_template: '',
      variables: 'title, price_formatted, bedrooms, bathrooms, city',
      is_default: false,
    },
  });

  const bodyTemplate = watch('body_template');
  const titleTemplate = watch('title_template');
  const platform = watch('platform');

  async function onSubmit(data: FormValues) {
    setError(null);
    try {
      const variables = data.variables
        .split(',')
        .map((v) => v.trim())
        .filter(Boolean);

      const template = await apiPost<ContentTemplate>(
        `/api/v1/organizations/${orgId}/content/templates`,
        {
          ...data,
          variables,
          campaign_tag: data.campaign_tag || null,
          scope: data.scope || null,
          title_template: data.title_template || null,
        },
      );
      toast({ title: 'Template created', description: 'Content template has been created.' });
      router.push(`/admin/templates/${template.id}/edit?org_id=${orgId}`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create template');
    }
  }

  const handleDryRun = useCallback(async () => {
    setError(null);
    try {
      let variables: Record<string, string> = {};
      try {
        variables = JSON.parse(previewVars);
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
  }, [orgId, bodyTemplate, titleTemplate, platform, previewVars]);

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">New Template</h1>
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={handleDryRun}>
            Preview
          </Button>
          <Button type="submit">Create Template</Button>
        </div>
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
              <Input id="scope" {...register('scope')} placeholder="e.g. weekly-digest" />
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
                placeholder="Optional: {{ title }} — {{ city }}"
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

      {preview && (
        <Card>
          <CardHeader>
            <CardTitle>Preview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Preview Variables (JSON)</Label>
              <Textarea
                value={previewVars}
                onChange={(e) => setPreviewVars(e.target.value)}
                rows={3}
                className="font-mono text-xs"
              />
              <Button type="button" variant="outline" size="sm" onClick={handleDryRun}>
                Refresh Preview
              </Button>
            </div>

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
                    preview.length_exceeded ? 'text-destructive font-bold' : 'text-muted-foreground'
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
          </CardContent>
        </Card>
      )}
    </form>
  );
}

export default function NewTemplatePage() {
  return (
    <Suspense fallback={<p>Loading...</p>}>
      <NewTemplateForm />
    </Suspense>
  );
}
