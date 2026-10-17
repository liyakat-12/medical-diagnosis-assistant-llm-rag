import { Phone } from "lucide-react";
import { EMERGENCY_NUMBER, EMERGENCY_TEL } from "../../utils/emergency";
import { cn } from "../../lib/cn";

export function EmergencyCallButton({ urgent = false }: { urgent?: boolean }) {
  return (
    <a
      href={EMERGENCY_TEL}
      className={cn(
        "inline-flex min-h-11 items-center gap-2 rounded-full px-3 py-1.5 text-xs font-extrabold text-white shadow-sm",
        urgent ? "bg-red-600 ring-2 ring-red-300 hover:bg-red-700" : "bg-red-600 hover:bg-red-700",
      )}
      aria-label={`Call emergency ambulance ${EMERGENCY_NUMBER}`}
    >
      <Phone size={14} /> Call {EMERGENCY_NUMBER}
    </a>
  );
}
