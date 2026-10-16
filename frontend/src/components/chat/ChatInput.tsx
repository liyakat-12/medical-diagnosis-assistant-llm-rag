import { useMemo, useState, type FormEvent, type KeyboardEvent } from "react";
import { Send, Square } from "lucide-react";
import { Textarea } from "../common/Textarea";
import { Button } from "../common/Button";
import { BodyMap } from "./BodyMap";
import {
  BODY_MAP_DISCLAIMER,
  buildBodyMapQuery,
  formatReviewLine,
  suggestedSymptoms,
  toggleItem,
  type BodyRegion,
  type BodyView,
} from "../../utils/bodyMap";

export function ChatInput({
  disabled,
  streaming,
  onSend,
  onStop,
}: {
  disabled?: boolean;
  streaming?: boolean;
  onSend: (value: string) => void;
  onStop: () => void;
}) {
  const [value, setValue] = useState("");
  const [regions, setRegions] = useState<BodyRegion[]>([]);
  const [symptoms, setSymptoms] = useState<string[]>([]);
  const [mapOpen, setMapOpen] = useState(true);
  const [view, setView] = useState<BodyView>("front");
  const suggestions = useMemo(() => suggestedSymptoms(regions), [regions]);
  const preview = buildBodyMapQuery(value, regions, symptoms);
  const canSend = Boolean(preview) && !disabled;

  function resetComposer() {
    setValue("");
    setRegions([]);
    setSymptoms([]);
    setMapOpen(false);
  }

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!preview || disabled) return;
    onSend(preview);
    resetComposer();
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form onSubmit={submit} className="border-t border-teal-100/80 bg-white/90 p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur">
      <div className="mx-auto max-w-3xl">
        <BodyMap
          selectedRegions={regions}
          selectedSymptoms={symptoms}
          suggestedSymptoms={suggestions}
          onToggleRegion={(region) => setRegions((current) => toggleItem(current, region))}
          onToggleSymptom={(symptom) => setSymptoms((current) => toggleItem(current, symptom))}
          onClear={() => {
            setRegions([]);
            setSymptoms([]);
          }}
          disabled={disabled && !streaming}
          open={mapOpen}
          onToggle={() => setMapOpen((current) => !current)}
          view={view}
          onViewChange={setView}
        />
        <div className="flex items-end gap-2 rounded-[1.6rem] border border-teal-100 bg-white p-2 shadow-sm">
          <Textarea
            label="Describe your symptoms"
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={onKeyDown}
            rows={2}
            placeholder="Add extra detail in your own words..."
            disabled={disabled && !streaming}
            className="border-0 bg-transparent px-3 py-2 shadow-none focus:border-0 focus:ring-0"
          />
          {streaming ? (
            <Button type="button" variant="danger" className="mb-1 h-11 w-11 shrink-0 rounded-full px-0" onClick={onStop} aria-label="Stop generating">
              <Square size={16} />
            </Button>
          ) : (
            <Button type="submit" className="mb-1 h-11 w-11 shrink-0 rounded-full px-0" disabled={!canSend} aria-label="Send message">
              <Send size={16} />
            </Button>
          )}
        </div>
        {preview ? (
          <p className="mt-2 text-xs leading-5 text-slate-600">
            <span className="font-extrabold text-slate-800">Will send: </span>
            {formatReviewLine(value, regions, symptoms)}
          </p>
        ) : (
          <p className="mt-2 text-xs leading-5 text-slate-500">{BODY_MAP_DISCLAIMER}</p>
        )}
      </div>
    </form>
  );
}
