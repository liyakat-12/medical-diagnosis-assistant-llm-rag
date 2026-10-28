import { Phone } from "lucide-react";
import { EMERGENCY_NUMBER, EMERGENCY_TEL } from "../../utils/emergency";
import { cn } from "../../lib/cn";

export function EmergencyCallButton({ urgent = false }: { urgent?: boolean }) {
  return (
    <a
      href={EMERGENCY_TEL}
      className={cn(
        "inline-flex min-h-11 items-center gap-2 rounded-full px-3 py-1.5 text-xs font-extrabold shadow-sm",
        urgent
          ? "bg-red-600 text-white ring-2 ring-red-300 hover:bg-red-700"
          : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50",
      )}
      aria-label={`Call emergency ambulance ${EMERGENCY_NUMBER}`}
    >
      <Phone size={14} />
      {urgent ? `Call ${EMERGENCY_NUMBER}` : `112`}
    </a>
  );
}
