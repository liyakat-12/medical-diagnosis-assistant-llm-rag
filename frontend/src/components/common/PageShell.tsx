import type { ReactNode } from "react";
import { Navbar } from "../navbar/Navbar";
import { Footer } from "../footer/Footer";
import { cn } from "../../lib/cn";

export function PageShell({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className="flex min-h-dvh flex-col bg-[#f4f8f7]">
      <Navbar />
      <main className={cn("flex-1", className)}>{children}</main>
      <Footer />
    </div>
  );
}
