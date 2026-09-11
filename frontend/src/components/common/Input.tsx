import { useState, type InputHTMLAttributes } from "react";
import { Eye, EyeOff } from "lucide-react";
import { cn } from "../../lib/cn";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export function Input({ label, error, className, type, id, ...props }: InputProps) {
  const [show, setShow] = useState(false);
  const inputId = id || label.toLowerCase().replace(/\s+/g, "-");
  const isPassword = type === "password";
  return (
    <label className="block" htmlFor={inputId}>
      <span className="mb-1.5 block text-sm font-bold text-slate-800">{label}</span>
      <span className="relative block">
        <input
          id={inputId}
          type={isPassword && show ? "text" : type}
          className={cn(
            "w-full rounded-2xl border bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-teal-600 focus:ring-2 focus:ring-teal-100",
            error ? "border-rose-400" : "border-teal-100",
            isPassword && "pr-12",
            className,
          )}
          {...props}
        />
        {isPassword ? (
          <button
            type="button"
            className="absolute inset-y-0 right-3 text-slate-500 hover:text-teal-800"
            onClick={() => setShow((value) => !value)}
            aria-label={show ? "Hide password" : "Show password"}
          >
            {show ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        ) : null}
      </span>
      {error ? <span className="mt-1 block text-xs font-semibold text-rose-600">{error}</span> : null}
    </label>
  );
}
