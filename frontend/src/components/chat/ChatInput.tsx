import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { ArrowUp, PersonStanding, Square } from "lucide-react";
import { BodyMap } from "./BodyMap";
import {
  BODY_MAP_DISCLAIMER,
  REGION_LABELS,
  REGION_SYMPTOMS,
  buildBodyMapQuery,
  formatReviewLine,
  summarizeSelection,
  toggleItem,
  type BodyRegion,
  type BodyView,
} from "../../utils/bodyMap";
import { cn } from "../../lib/cn";

export type ChatInputHandle = {
  openMap: (region?: BodyRegion) => void;
};

export const ChatInput = forwardRef<
  ChatInputHandle,
  {
    disabled?: boolean;
    streaming?: boolean;
    error?: string;
    onSend: (value: string) => void;
    onStop: () => void;
  }
>(function ChatInput({ disabled, streaming, error, onSend, onStop }, ref) {
  const [value, setValue] = useState("");
  const [regions, setRegions] = useState<BodyRegion[]>([]);
  const [symptoms, setSymptoms] = useState<string[]>([]);
  const [mapOpen, setMapOpen] = useState(false);
  const [view, setView] = useState<BodyView>("front");
  const [activeRegion, setActiveRegion] = useState<BodyRegion | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const draftRef = useRef({ value: "", regions: [] as BodyRegion[], symptoms: [] as string[] });
  const suggestions = useMemo(() => (activeRegion ? REGION_SYMPTOMS[activeRegion] : []), [activeRegion]);
  const preview = buildBodyMapQuery(value, regions, symptoms);
  const canSend = Boolean(preview) && !disabled;
  const summary = summarizeSelection(regions, symptoms);
  const hasMapSelection = Boolean(regions.length || symptoms.length);

  useImperativeHandle(
    ref,
    () => ({
      openMap(region) {
        if (region) {
          setRegions((current) => (current.includes(region) ? current : [...current, region]));
          setActiveRegion(region);
        }
        setMapOpen(true);
      },
    }),
    [],
  );

  useEffect(() => {
    const node = textareaRef.current;
    if (!node) return;
    node.style.height = "auto";
    node.style.height = `${Math.min(node.scrollHeight, 168)}px`;
  }, [value]);

  useEffect(() => {
    if (!error) return;
    setValue(draftRef.current.value);
    setRegions(draftRef.current.regions);
    setSymptoms(draftRef.current.symptoms);
  }, [error]);

  function resetComposer() {
    setValue("");
    setRegions([]);
    setSymptoms([]);
    setActiveRegion(null);
    setMapOpen(false);
  }

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!preview || disabled) return;
    draftRef.current = { value, regions, symptoms };
    onSend(preview);
    resetComposer();
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  function toggleRegion(region: BodyRegion) {
    setRegions((current) => {
      const next = toggleItem(current, region);
      setActiveRegion(next.includes(region) ? region : next[next.length - 1] || null);
      return next;
    });
  }

  return (
    <form onSubmit={submit} className="shrink-0 border-t border-sky-100 bg-sky-50 px-3 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
      <div className="mx-auto max-w-3xl">
        <BodyMap
          selectedRegions={regions}
          selectedSymptoms={symptoms}
          suggestedSymptoms={suggestions}
          activeRegion={activeRegion}
          onActiveRegion={setActiveRegion}
          onToggleRegion={toggleRegion}
          onToggleSymptom={(symptom) => setSymptoms((current) => toggleItem(current, symptom))}
          onClear={() => {
            setRegions([]);
            setSymptoms([]);
            setActiveRegion(null);
          }}
          disabled={disabled && !streaming}
          open={mapOpen}
          onToggle={() => setMapOpen((current) => !current)}
          view={view}
          onViewChange={setView}
        />
        {hasMapSelection && summary !== "No body regions or symptoms selected" ? (
          <div className="mb-2 flex flex-wrap items-center gap-2">
            {regions.map((id) => (
              <button
                key={id}
                type="button"
                className="min-h-9 rounded-full bg-sky-700 px-3 text-xs font-bold text-white"
                onClick={() => toggleRegion(id)}
                aria-label={`Remove ${REGION_LABELS[id]}`}
              >
                {REGION_LABELS[id]} ×
              </button>
            ))}
            {symptoms.map((item) => (
              <button key={item} type="button" className="min-h-9 rounded-full border border-sky-200 bg-white px-3 text-xs font-bold text-sky-900" onClick={() => setSymptoms((current) => toggleItem(current, item))}>
                {item} ×
              </button>
            ))}
          </div>
        ) : null}
        <div className="flex items-end gap-2 rounded-[1.75rem] border border-sky-200 bg-white p-2 shadow-sm focus-within:border-sky-500">
          <button
            type="button"
            className={cn(
              "mb-0.5 inline-flex h-12 shrink-0 items-center gap-1.5 rounded-full px-3.5 text-white shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-800",
              mapOpen || hasMapSelection ? "bg-sky-900 hover:bg-sky-950" : "bg-sky-600 hover:bg-sky-700",
            )}
            onClick={() => setMapOpen(true)}
            aria-expanded={mapOpen}
            aria-label="Open body map"
            title="Tap the body where it hurts"
            disabled={disabled && !streaming}
          >
            <PersonStanding size={20} className="shrink-0" />
            <span className="text-xs font-extrabold">Body</span>
          </button>
          <label className="min-w-0 flex-1">
            <span className="sr-only">Describe your symptoms</span>
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(event) => setValue(event.target.value)}
              onKeyDown={onKeyDown}
              rows={1}
              placeholder="Message MediAssist..."
              disabled={disabled && !streaming}
              className="max-h-40 min-h-12 w-full resize-none bg-transparent px-2 py-3 text-sm leading-6 text-slate-900 outline-none"
            />
          </label>
          {streaming ? (
            <button type="button" className="mb-0.5 grid h-12 w-12 shrink-0 place-items-center rounded-full bg-rose-600 text-white hover:bg-rose-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-700" onClick={onStop} aria-label="Stop generating">
              <Square size={16} className="shrink-0 fill-current" />
            </button>
          ) : (
            <button
              type="submit"
              className="mb-0.5 grid h-12 w-12 shrink-0 place-items-center rounded-full bg-sky-600 text-white shadow-sm hover:bg-sky-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-800 disabled:cursor-not-allowed disabled:bg-sky-500 disabled:text-white disabled:opacity-90"
              disabled={!canSend}
              aria-label="Send message"
            >
              <ArrowUp size={20} strokeWidth={2.6} className="shrink-0" />
            </button>
          )}
        </div>
        {preview ? (
          <p className="mt-2 text-xs leading-5 text-slate-500">
            <span className="font-bold text-slate-700">Will send: </span>
            {formatReviewLine(value, regions, symptoms)}
          </p>
        ) : (
          <p className="mt-2 text-xs leading-5 text-slate-500">{BODY_MAP_DISCLAIMER}</p>
        )}
      </div>
    </form>
  );
});
