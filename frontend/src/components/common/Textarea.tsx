import type { TextareaHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
}

export function Textarea({ label, className, id, ...props }: TextareaProps) {
  const fieldId = id || label?.toLowerCase().replace(/\s+/g, "-");
  return (
    <label className="block w-full" htmlFor={fieldId}>
      {label ? <span className="sr-only">{label}</span> : null}
      <textarea
        id={fieldId}
        className={cn(
          "w-full resize-none rounded-2xl border border-teal-100 bg-white px-4 py-3 text-sm leading-6 text-slate-900 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100",
          className,
        )}
        {...props}
      />
    </label>
  );
}
