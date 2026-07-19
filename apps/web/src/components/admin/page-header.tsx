import { cn } from '@/lib/utils';

interface AdminPageHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}

export function AdminPageHeader({
  eyebrow = 'Dream Home Estate',
  title,
  description,
  actions,
  className,
}: AdminPageHeaderProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-4 rounded-2xl border border-border/80 bg-card p-5 shadow-card sm:flex-row sm:items-end sm:justify-between sm:p-6',
        className
      )}
    >
      <div className="min-w-0">
        {eyebrow && (
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">{eyebrow}</p>
        )}
        <h1 className="mt-1 font-display text-3xl font-semibold tracking-tight text-foreground">
          {title}
        </h1>
        {description && (
          <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
