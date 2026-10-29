import type { ReactNode } from "react";
import { AlertTriangle, Inbox, RefreshCw } from "lucide-react";
import { cn } from "../../lib/cn";

export function Skeleton({ className }: { className?: string }) {
  return <span aria-hidden className={cn("block animate-pulse rounded-md bg-slate-200/80 motion-reduce:animate-none", className)} />;
}

export function ErrorState({ title = "Could not load this section", message, onRetry }: { title?: string; message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3">
      <AlertTriangle size={18} className="mt-0.5 shrink-0 text-rose-700" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-bold text-rose-900">{title}</p>
        <p className="mt-0.5 text-sm leading-6 text-rose-800">{message}</p>
      </div>
      {onRetry ? (
        <button type="button" onClick={onRetry} className="inline-flex min-h-9 items-center gap-1.5 rounded-full border border-rose-300 bg-white px-3 text-xs font-bold text-rose-900 hover:bg-rose-100">
          <RefreshCw size={13} aria-hidden /> Try again
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-2 rounded-xl border border-dashed border-slate-300 px-4 py-5">
      <Inbox size={18} className="text-slate-400" aria-hidden />
      <p className="text-sm font-bold text-slate-800">{title}</p>
      {children ? <div className="text-sm leading-6 text-slate-600">{children}</div> : null}
      {action}
    </div>
  );
}

export function SectionHeading({ id, eyebrow, title, children, actions }: { id?: string; eyebrow?: string; title: string; children?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div className="max-w-3xl">
        {eyebrow ? <p className="text-[11px] font-extrabold uppercase tracking-[0.16em] text-teal-700">{eyebrow}</p> : null}
        <h2 id={id} className="mt-1 text-xl font-extrabold tracking-tight text-[#0b1f33] [text-wrap:balance]">
          {title}
        </h2>
        {children ? <div className="mt-1.5 text-sm leading-6 text-slate-600 [text-wrap:pretty]">{children}</div> : null}
      </div>
      {actions}
    </div>
  );
}
