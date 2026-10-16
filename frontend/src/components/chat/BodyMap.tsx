import type { KeyboardEvent } from "react";
import { REGION_LABELS, REGION_ORDER, type BodyRegion, type BodyView } from "../../utils/bodyMap";
import { cn } from "../../lib/cn";

function activateOnKey(event: KeyboardEvent<SVGElement>, action: () => void) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    action();
  }
}

function RegionPath({
  region,
  label,
  selected,
  disabled,
  d,
  onToggle,
}: {
  region: BodyRegion;
  label: string;
  selected: boolean;
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
      aria-label={`${label}${selected ? ", selected" : ""}`}
      fill={selected ? "#0f766e" : "#c5ddd8"}
      fillOpacity={selected ? 0.95 : 0.72}
      stroke={selected ? "#134e4a" : "#5f9c91"}
      strokeWidth={selected ? 2.6 : 1.3}
      className={cn(
        "outline-none transition-[fill,fill-opacity,stroke-width] duration-150",
        disabled ? "cursor-not-allowed" : "cursor-pointer hover:fill-[#8ec4ba] active:fill-[#5f9c91] focus-visible:stroke-[#0f766e] focus-visible:stroke-[3]",
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

function Figure({
  view,
  selected,
  onToggle,
  disabled,
}: {
  view: BodyView;
  selected: BodyRegion[];
  onToggle: (region: BodyRegion) => void;
  disabled?: boolean;
}) {
  const isOn = (region: BodyRegion) => selected.includes(region);
  return (
    <svg viewBox="0 0 160 280" className="mx-auto h-64 w-40 max-w-full sm:h-72 sm:w-44" role="group" aria-label={`${view} view of the body. Select a region.`}>
      <ellipse cx="80" cy="272" rx="36" ry="5" fill="#d9ebe7" />
      <path d="M54 78 C32 90 24 118 28 146 C30 156 40 156 42 146 L48 108 L50 168 C50 214 46 244 40 262 C39 266 44 268 46 264 L54 232 L80 232 L106 264 C108 268 113 266 112 262 C106 244 102 214 102 168 L104 108 L110 146 C112 156 122 156 124 146 C128 118 120 90 98 78 Z" fill="#eef7f5" stroke="#8eb5ad" strokeWidth="1.2" />
      <RegionPath region="head" label="Head" selected={isOn("head")} disabled={disabled} onToggle={onToggle} d="M80 18 C94 18 104 30 104 44 C104 58 94 68 80 68 C66 68 56 58 56 44 C56 30 66 18 80 18 Z" />
      {view === "front" ? (
        <>
          <RegionPath region="chest" label="Chest" selected={isOn("chest")} disabled={disabled} onToggle={onToggle} d="M58 76 C58 72 66 70 80 70 C94 70 102 72 102 76 L102 118 C102 124 94 128 80 128 C66 128 58 124 58 118 Z" />
          <RegionPath region="abdomen" label="Abdomen" selected={isOn("abdomen")} disabled={disabled} onToggle={onToggle} d="M60 130 C60 126 68 124 80 124 C92 124 100 126 100 130 L100 168 C100 174 92 178 80 178 C68 178 60 174 60 168 Z" />
        </>
      ) : (
        <RegionPath region="back" label="Back" selected={isOn("back")} disabled={disabled} onToggle={onToggle} d="M58 76 C58 72 66 70 80 70 C94 70 102 72 102 76 L102 168 C102 174 94 178 80 178 C66 178 58 174 58 168 Z" />
      )}
      <RegionPath region="arm" label="Arm" selected={isOn("arm")} disabled={disabled} onToggle={onToggle} d="M54 80 C40 88 30 112 32 138 C33 146 41 146 42 138 C44 118 50 98 58 90 Z" />
      <RegionPath region="arm" label="Arm" selected={isOn("arm")} disabled={disabled} onToggle={onToggle} d="M106 80 C120 88 130 112 128 138 C127 146 119 146 118 138 C116 118 110 98 102 90 Z" />
      <RegionPath region="leg" label="Leg" selected={isOn("leg")} disabled={disabled} onToggle={onToggle} d="M62 180 C62 176 70 174 76 174 C80 174 82 178 82 182 L78 258 C77 264 70 264 68 258 C64 236 62 206 62 190 Z" />
      <RegionPath region="leg" label="Leg" selected={isOn("leg")} disabled={disabled} onToggle={onToggle} d="M84 182 C84 178 86 174 90 174 C96 174 104 176 104 180 L104 190 C104 206 102 236 98 258 C96 264 89 264 88 258 Z" />
    </svg>
  );
}

export function BodyMap({
  selectedRegions,
  selectedSymptoms,
  suggestedSymptoms,
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
  const symptomSummary = selectedSymptoms.join(", ");

  return (
    <section className="mb-3 rounded-3xl border border-teal-100 bg-gradient-to-b from-white to-teal-50/40 px-4 py-3" aria-label="Body map">
      <div className="flex items-center justify-between gap-3">
        <button type="button" className="min-h-11 min-w-0 text-left" onClick={onToggle} aria-expanded={open}>
          <p className="text-xs font-extrabold uppercase tracking-[0.16em] text-teal-800">Tap where it hurts</p>
          <p className="mt-0.5 truncate text-xs leading-5 text-slate-500">
            {open
              ? "Describe discomfort by body region. This is not a diagnosis."
              : summary || symptomSummary
                ? `${summary}${summary && symptomSummary ? " · " : ""}${symptomSummary}`
                : "Minimized. Expand to choose a body region."}
          </p>
        </button>
        <div className="flex shrink-0 items-center gap-2">
          {(selectedRegions.length || selectedSymptoms.length) && open ? (
            <button type="button" className="min-h-11 px-2 text-xs font-bold text-teal-800" onClick={onClear} disabled={disabled}>
              Clear all
            </button>
          ) : null}
          <button
            type="button"
            onClick={onToggle}
            className="min-h-11 rounded-full border border-teal-200 bg-white px-3 py-1 text-xs font-extrabold text-teal-800"
            aria-expanded={open}
            aria-label={open ? "Minimize body map" : "Expand body map"}
          >
            {open ? "Minimize" : "Expand"}
          </button>
        </div>
      </div>

      {open ? (
        <div className="mt-3 max-h-[min(52vh,28rem)] overflow-y-auto">
          <div className="mb-3 flex justify-center gap-2" role="tablist" aria-label="Body view">
            {(["front", "back"] as BodyView[]).map((item) => (
              <button
                key={item}
                type="button"
                role="tab"
                aria-selected={view === item}
                className={cn(
                  "min-h-11 min-w-20 rounded-full px-4 text-xs font-extrabold capitalize",
                  view === item ? "bg-teal-800 text-white" : "border border-teal-200 bg-white text-teal-900",
                )}
                onClick={() => onViewChange(item)}
              >
                {item}
              </button>
            ))}
          </div>
          <Figure view={view} selected={selectedRegions} onToggle={onToggleRegion} disabled={disabled} />
          <p className="mt-2 text-center text-sm font-bold text-slate-800" aria-live="polite">
            {selectedRegions.length ? `Selected: ${summary}` : "No region selected"}
          </p>
          <p className="mt-3 text-center text-[11px] font-bold uppercase tracking-wide text-slate-400">Or choose with buttons</p>
          <div className="mt-2 flex flex-wrap justify-center gap-2">
            {REGION_ORDER.map((id) => {
              const active = selectedRegions.includes(id);
              return (
                <button
                  key={id}
                  type="button"
                  disabled={disabled}
                  aria-pressed={active}
                  onClick={() => onToggleRegion(id)}
                  className={cn(
                    "min-h-11 rounded-full px-3 py-1.5 text-xs font-bold",
                    active ? "bg-teal-800 text-white shadow-sm" : "border border-teal-200 bg-white text-teal-900 hover:bg-teal-50",
                  )}
                >
                  {active ? `✓ ${REGION_LABELS[id]}` : REGION_LABELS[id]}
                </button>
              );
            })}
          </div>
          <p className="mt-4 text-[11px] font-bold uppercase tracking-wide text-slate-400">Suggested symptoms</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {[...suggestedSymptoms, ...selectedSymptoms.filter((item) => !suggestedSymptoms.includes(item))].map((item) => {
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
                    active ? "bg-teal-800 text-white" : "border border-teal-100 bg-teal-50 text-teal-900 hover:bg-teal-100",
                  )}
                >
                  {active ? `✓ ${item}` : item}
                </button>
              );
            })}
          </div>
        </div>
      ) : null}
    </section>
  );
}
