import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

export function Spinner({ className, label = "Loading" }: { className?: string; label?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2 text-sm font-semibold text-teal-800", className)} role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-teal-200 border-t-teal-700" aria-hidden />
      {label}
    </span>
  );
}

export function PageSpinner({ label = "Checking your session..." }: { label?: string }) {
  return (
    <div className="grid min-h-screen place-items-center bg-[#f4f8f7]">
      <Spinner label={label} />
    </div>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-3xl border border-dashed border-teal-200 bg-white/70 px-6 py-10 text-center">
      <h2 className="text-lg font-extrabold text-slate-900">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-600">{body}</p>
    </div>
  );
}

export function Avatar({ name }: { name: string }) {
  const initial = (name || "M").trim().charAt(0).toUpperCase();
  return (
    <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-teal-700 text-sm font-extrabold text-white">
      {initial}
    </span>
  );
}

export function Modal({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <button className="absolute inset-0 cursor-default" aria-label="Close dialog" onClick={onClose} />
      <div className="relative w-full max-w-md rounded-3xl bg-white p-6 shadow-xl">
        <h2 id="modal-title" className="text-lg font-extrabold text-slate-900">
          {title}
        </h2>
        <div className="mt-4">{children}</div>
      </div>
    </div>
  );
}
