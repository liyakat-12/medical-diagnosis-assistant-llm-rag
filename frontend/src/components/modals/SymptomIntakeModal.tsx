import { useEffect } from "react";
import { FollowUpCard, formatFollowUpQuery, type FollowUpAnswers } from "../chat/FollowUpCard";

export { formatFollowUpQuery, type FollowUpAnswers };

export function SymptomIntakeModal({
  symptoms,
  onContinue,
  onSkip,
}: {
  symptoms: string;
  onContinue: (answers: FollowUpAnswers) => void;
  onSkip: () => void;
}) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onSkip();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onSkip]);

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4" role="presentation" onClick={onSkip}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="symptom-intake-title"
        className="max-h-[90dvh] w-full max-w-xl overflow-y-auto rounded-3xl bg-white p-1 shadow-xl animate-in fade-in zoom-in-95"
        onClick={(event) => event.stopPropagation()}
      >
        <FollowUpCard symptoms={symptoms} onContinue={onContinue} onSkip={onSkip} />
      </div>
    </div>
  );
}
