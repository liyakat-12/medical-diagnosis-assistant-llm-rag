import { useEffect, type KeyboardEvent as ReactKeyboardEvent } from "react";
import { REGION_LABELS, REGION_ORDER, type BodyRegion, type BodyView } from "../../utils/bodyMap";
import { cn } from "../../lib/cn";

function activateOnKey(event: ReactKeyboardEvent<SVGElement>, action: () => void) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    action();
  }
}

function RegionPath({
  region,
  label,
  selected,
  focused,
  disabled,
  d,
  onToggle,
}: {
  region: BodyRegion;
  label: string;
  selected: boolean;
  focused: boolean;
  disabled?: boolean;
  d: string;
  onToggle: (region: BodyRegion) => void;
}) {
  return (
    <path
      d={d}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-pressed={selected}
      aria-current={focused ? "true" : undefined}
      aria-label={`${label}${selected ? ", selected" : ""}${focused ? ", editing symptoms" : ""}`}
      fill={selected ? "#0369a1" : "#7dd3fc"}
      fillOpacity={selected ? 0.98 : 0.92}
      stroke={focused ? "#0f172a" : selected ? "#0c4a6e" : "#0284c7"}
      strokeWidth={focused ? 3 : selected ? 2.4 : 1.6}
      strokeDasharray={focused && !selected ? "4 3" : undefined}
      className={cn(
        "outline-none transition-[fill,fill-opacity,stroke-width] duration-150",
        disabled ? "cursor-not-allowed" : "cursor-pointer hover:fill-[#38bdf8] active:fill-[#0ea5e9] focus-visible:stroke-[#0369a1] focus-visible:stroke-[3]",
      )}
      onClick={() => {
        if (!disabled) onToggle(region);
      }}
      onKeyDown={(event) => {
        if (disabled) return;
        activateOnKey(event, () => onToggle(region));
      }}
    />
  );
}

export function BodyFigure({
  view,
  selected,
  focused,
  onToggle,
  disabled,
}: {
  view: BodyView;
  selected: BodyRegion[];
  focused: BodyRegion | null;
  onToggle: (region: BodyRegion) => void;
  disabled?: boolean;
}) {
  const isOn = (region: BodyRegion) => selected.includes(region);
  return (
    <svg viewBox="0 0 160 280" className="mx-auto h-56 w-36 max-w-full sm:h-64 sm:w-40" role="group" aria-label={`${view} view of the body. Select a region.`}>
      <ellipse cx="80" cy="272" rx="36" ry="5" fill="#bae6fd" />
      <path d="M54 78 C32 90 24 118 28 146 C30 156 40 156 42 146 L48 108 L50 168 C50 214 46 244 40 262 C39 266 44 268 46 264 L54 232 L80 232 L106 264 C108 268 113 266 112 262 C106 244 102 214 102 168 L104 108 L110 146 C112 156 122 156 124 146 C128 118 120 90 98 78 Z" fill="#e0f2fe" stroke="#38bdf8" strokeWidth="1.4" />
      <RegionPath region="head" label="Head" selected={isOn("head")} focused={focused === "head"} disabled={disabled} onToggle={onToggle} d="M80 18 C94 18 104 30 104 44 C104 58 94 68 80 68 C66 68 56 58 56 44 C56 30 66 18 80 18 Z" />
      {view === "front" ? (
        <>
          <RegionPath region="chest" label="Chest" selected={isOn("chest")} focused={focused === "chest"} disabled={disabled} onToggle={onToggle} d="M58 76 C58 72 66 70 80 70 C94 70 102 72 102 76 L102 118 C102 124 94 128 80 128 C66 128 58 124 58 118 Z" />
          <RegionPath region="abdomen" label="Abdomen" selected={isOn("abdomen")} focused={focused === "abdomen"} disabled={disabled} onToggle={onToggle} d="M60 130 C60 126 68 124 80 124 C92 124 100 126 100 130 L100 168 C100 174 92 178 80 178 C68 178 60 174 60 168 Z" />
        </>
      ) : (
        <RegionPath region="back" label="Back" selected={isOn("back")} focused={focused === "back"} disabled={disabled} onToggle={onToggle} d="M58 76 C58 72 66 70 80 70 C94 70 102 72 102 76 L102 168 C102 174 94 178 80 178 C66 178 58 174 58 168 Z" />
      )}
      <RegionPath region="arm" label="Arm" selected={isOn("arm")} focused={focused === "arm"} disabled={disabled} onToggle={onToggle} d="M54 80 C40 88 30 112 32 138 C33 146 41 146 42 138 C44 118 50 98 58 90 Z" />
      <RegionPath region="arm" label="Arm" selected={isOn("arm")} focused={focused === "arm"} disabled={disabled} onToggle={onToggle} d="M106 80 C120 88 130 112 128 138 C127 146 119 146 118 138 C116 118 110 98 102 90 Z" />
      <RegionPath region="leg" label="Leg" selected={isOn("leg")} focused={focused === "leg"} disabled={disabled} onToggle={onToggle} d="M62 180 C62 176 70 174 76 174 C80 174 82 178 82 182 L78 258 C77 264 70 264 68 258 C64 236 62 206 62 190 Z" />
      <RegionPath region="leg" label="Leg" selected={isOn("leg")} focused={focused === "leg"} disabled={disabled} onToggle={onToggle} d="M84 182 C84 178 86 174 90 174 C96 174 104 176 104 180 L104 190 C104 206 102 236 98 258 C96 264 89 264 88 258 Z" />
    </svg>
  );
}

export function BodyMap({
  selectedRegions,
  selectedSymptoms,
  suggestedSymptoms,
  activeRegion,
  onActiveRegion,
  onToggleRegion,
  onToggleSymptom,
  onClear,
  disabled,
  open,
  onToggle,
  view,
  onViewChange,
}: {
  selectedRegions: BodyRegion[];
  selectedSymptoms: string[];
  suggestedSymptoms: string[];
  activeRegion: BodyRegion | null;
  onActiveRegion: (region: BodyRegion | null) => void;
  onToggleRegion: (region: BodyRegion) => void;
  onToggleSymptom: (symptom: string) => void;
  onClear: () => void;
  disabled?: boolean;
  open: boolean;
  onToggle: () => void;
  view: BodyView;
  onViewChange: (view: BodyView) => void;
}) {
  const summary = selectedRegions.map((region) => REGION_LABELS[region]).join(", ");

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onToggle();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onToggle]);

  function selectRegion(region: BodyRegion) {
    onActiveRegion(region);
    if (!selectedRegions.includes(region)) onToggleRegion(region);
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-labelledby="body-map-title">
      <button type="button" className="absolute inset-0 bg-slate-900/40" aria-label="Close body map" onClick={onToggle} />
      <section className="absolute inset-x-0 bottom-0 flex max-h-[min(92dvh,44rem)] flex-col rounded-t-3xl border border-sky-200 bg-sky-50 shadow-2xl md:inset-auto md:left-1/2 md:top-1/2 md:w-[min(48rem,calc(100%-2rem))] md:-translate-x-1/2 md:-translate-y-1/2 md:rounded-3xl">
        <div className="flex items-start justify-between gap-3 border-b border-sky-100 bg-white px-4 py-3">
          <div>
            <p id="body-map-title" className="text-sm font-extrabold text-slate-900">
              Tap where it hurts
            </p>
            <p className="mt-0.5 text-xs leading-5 text-slate-500">Choose a region, then the symptoms that match. This is not a diagnosis.</p>
          </div>
          <button type="button" className="min-h-11 min-w-11 rounded-full text-slate-500 hover:bg-sky-50" onClick={onToggle} aria-label="Close body map" aria-expanded={open}>
            ×
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          <div className="mb-3 flex justify-center gap-2" role="tablist" aria-label="Body view">
            {(["front", "back"] as BodyView[]).map((item) => (
              <button
                key={item}
                type="button"
                role="tab"
                aria-selected={view === item}
                className={cn(
                  "min-h-11 min-w-20 rounded-full px-4 text-xs font-extrabold capitalize",
                  view === item ? "bg-sky-700 text-white" : "border border-sky-200 bg-white text-sky-900",
                )}
                onClick={() => onViewChange(item)}
              >
                {item}
              </button>
            ))}
          </div>
          <div className="grid gap-6 md:grid-cols-[11rem_1fr] md:items-start">
            <BodyFigure view={view} selected={selectedRegions} focused={activeRegion} onToggle={selectRegion} disabled={disabled} />
            <div>
              <p className="text-center text-sm font-bold text-slate-800 md:text-left" aria-live="polite">
                {activeRegion ? `Symptoms for ${REGION_LABELS[activeRegion]}` : selectedRegions.length ? `Selected: ${summary}` : "Select a body region to see matching symptoms"}
              </p>
              <p className="mt-3 text-center text-[11px] font-bold uppercase tracking-wide text-slate-400 md:text-left">Or choose with buttons</p>
              <div className="mt-2 flex flex-wrap justify-center gap-2 md:justify-start">
                {REGION_ORDER.map((id) => {
                  const active = selectedRegions.includes(id);
                  const focused = activeRegion === id;
                  return (
                    <button
                      key={id}
                      type="button"
                      disabled={disabled}
                      aria-pressed={active}
                      onClick={() => selectRegion(id)}
                      className={cn(
                        "min-h-11 rounded-full px-3 py-1.5 text-xs font-bold",
                        focused ? "ring-2 ring-slate-900 ring-offset-1" : "",
                        active ? "bg-sky-700 text-white shadow-sm" : "border border-sky-200 bg-white text-sky-900 hover:bg-sky-100",
                      )}
                    >
                      {active ? `✓ ${REGION_LABELS[id]}` : REGION_LABELS[id]}
                    </button>
                  );
                })}
              </div>
              <div className="mt-4">
                {activeRegion && suggestedSymptoms.length ? (
                  <>
                    <p className="text-[11px] font-bold uppercase tracking-wide text-slate-400">Suggested symptoms</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {suggestedSymptoms.map((item) => {
                        const active = selectedSymptoms.includes(item);
                        return (
                          <button
                            key={item}
                            type="button"
                            disabled={disabled}
                            aria-pressed={active}
                            onClick={() => onToggleSymptom(item)}
                            className={cn(
                              "min-h-11 rounded-full px-3 py-1.5 text-xs font-bold",
                              active ? "bg-sky-700 text-white" : "border border-sky-100 bg-white text-sky-900 hover:bg-sky-100",
                            )}
                          >
                            {active ? `✓ ${item}` : item}
                          </button>
                        );
                      })}
                    </div>
                  </>
                ) : (
                  <p className="rounded-2xl bg-white px-3 py-3 text-sm leading-6 text-slate-600 ring-1 ring-sky-100">Tap the figure or a region button. Then pick one or more symptoms for that area.</p>
                )}
              </div>
            </div>
          </div>
        </div>
        <div className="border-t border-sky-100 bg-white px-4 py-3">
          {selectedRegions.length || selectedSymptoms.length ? (
            <div className="mb-3 flex flex-wrap gap-2">
              {selectedRegions.map((id) => (
                <button
                  key={`region-${id}`}
                  type="button"
                  className="min-h-9 rounded-full bg-sky-700 px-3 text-xs font-bold text-white"
                  onClick={() => onToggleRegion(id)}
                  aria-label={`Remove ${REGION_LABELS[id]}`}
                >
                  {REGION_LABELS[id]} ×
                </button>
              ))}
              {selectedSymptoms.map((item) => (
                <button
                  key={`symptom-${item}`}
                  type="button"
                  className="min-h-9 rounded-full border border-sky-200 px-3 text-xs font-bold text-sky-900"
                  onClick={() => onToggleSymptom(item)}
                  aria-label={`Remove ${item}`}
                >
                  {item} ×
                </button>
              ))}
            </div>
          ) : null}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <button type="button" className="min-h-11 px-2 text-sm font-bold text-slate-500" onClick={onClear} disabled={disabled || (!selectedRegions.length && !selectedSymptoms.length)}>
              Clear all
            </button>
            <button type="button" className="min-h-11 rounded-full bg-sky-700 px-5 text-sm font-extrabold text-white hover:bg-sky-800" onClick={onToggle}>
              Use these symptoms
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
