import { useEffect } from "react";
import { X } from "lucide-react";
import { NearbyHospitals } from "./NearbyHospitals";

export function HospitalFinderModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, open]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4" role="presentation" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="hospital-finder-title"
        className="max-h-[90dvh] w-full max-w-2xl overflow-y-auto rounded-3xl bg-white p-2 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex justify-end px-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="grid min-h-11 min-w-11 place-items-center rounded-full text-slate-500 hover:bg-teal-50"
            aria-label="Close nearby hospitals"
          >
            <X size={18} />
          </button>
        </div>
        <NearbyHospitals active />
      </div>
    </div>
  );
}
