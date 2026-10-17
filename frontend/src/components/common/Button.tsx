import type { ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
}

export function Button({ className, variant = "primary", size = "md", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-full font-bold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 disabled:cursor-not-allowed disabled:opacity-60",
        variant === "primary" && "bg-teal-700 text-white hover:bg-teal-800",
        variant === "secondary" && "border border-teal-200 bg-white text-teal-900 hover:bg-teal-50",
        variant === "ghost" && "text-slate-700 hover:bg-teal-50",
        variant === "danger" && "bg-rose-600 text-white hover:bg-rose-700",
        size === "sm" && "min-h-9 px-3 py-1.5 text-xs",
        size === "md" && "min-h-11 px-5 py-2.5 text-sm",
        size === "lg" && "min-h-12 px-6 py-3 text-sm",
        className,
      )}
      {...props}
    />
  );
}
