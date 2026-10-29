import { Fragment, useEffect, useId, type KeyboardEvent as ReactKeyboardEvent } from "react";
import { MessageSquareText, RotateCcw, X } from "lucide-react";
import {
  BODY_MAP_DISCLAIMER,
  REGION_DESCRIPTIONS,
  REGION_GROUPS,
  REGION_LABELS,
  VIEW_LABELS,
  hiddenInView,
  regionView,
  viewForRegion,
  type BodyRegion,
  type BodyView,
} from "../../utils/bodyMap";
import { cn } from "../../lib/cn";
import { DETAIL_DOTS, DETAIL_LINES, FIGURE_VIEWBOX, FIGURE_WIDTH, MIRROR, REGION_LAYERS, type RegionLayer } from "./bodyShapes";

const VIEWS: BodyView[] = ["front", "back"];
const CENTER_X = FIGURE_WIDTH / 2;
// Rough width of a 15px bold character in canvas units, used to size the hover caption pill.
const CAPTION_CHAR_WIDTH = 8.6;

function activateOnKey(event: ReactKeyboardEvent<SVGElement>, action: () => void) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    action();
  }
}

function regionClasses(selected: boolean, focused: boolean, disabled?: boolean) {
  return cn(
    "transition-[fill,stroke] duration-150 motion-reduce:transition-none [stroke-linejoin:round] [stroke-linecap:round]",
    selected ? "fill-[#7dbab1] stroke-[#1f5d56]" : "fill-[#f7f2ea] stroke-[#5d7590]",
    !disabled && (selected ? "group-hover:fill-[#69ada3]" : "group-hover:fill-[#d6ebe7] group-hover:stroke-[#2f7f77] group-focus-visible:fill-[#d6ebe7]"),
    focused ? "stroke-[#0b1f33] [stroke-width:2.4]" : "[stroke-width:1.2]",
    !disabled && "group-focus-visible:stroke-[#0b1f33] group-focus-visible:[stroke-width:2.4]",
  );
}

function RegionButton({
  layer,
  selected,
  focused,
  disabled,
  onToggle,
}: {
  layer: RegionLayer;
  selected: boolean;
  focused: boolean;
  disabled?: boolean;
  onToggle: (region: BodyRegion) => void;
}) {
  const { region, shapes } = layer;
  const label = REGION_LABELS[region];
  const captionWidth = label.length * CAPTION_CHAR_WIDTH + 26;
  const classes = regionClasses(selected, focused, disabled);
  return (
    <g
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-pressed={selected}
      aria-current={focused ? "true" : undefined}
      aria-label={`${label}${selected ? ", selected" : ""}${focused ? ", editing symptoms" : ""}`}
      data-region={region}
      className={cn("group outline-none", disabled ? "cursor-not-allowed" : "cursor-pointer")}
      onClick={() => {
        if (!disabled) onToggle(region);
      }}
      onKeyDown={(event) => {
        if (disabled) return;
        activateOnKey(event, () => onToggle(region));
      }}
    >
      <title>{REGION_DESCRIPTIONS[region]}</title>
      {shapes.map((shape, index) => (
        <Fragment key={index}>
          <path d={shape.d} fillRule="nonzero" className={classes} />
          {shape.mirror ? <path d={shape.d} transform={MIRROR} fillRule="nonzero" className={classes} /> : null}
        </Fragment>
      ))}
      <g
        aria-hidden="true"
        className="pointer-events-none opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100 motion-reduce:transition-none"
      >
        <rect x={CENTER_X - captionWidth / 2} y={-29} width={captionWidth} height={25} rx={12.5} className="fill-[#0b1f33]" />
        <text x={CENTER_X} y={-11.5} textAnchor="middle" className="fill-white text-[15px] font-bold">
          {label}
        </text>
      </g>
    </g>
  );
}

export function BodyFigure({
  view,
  selected,
  focused,
  onToggle,
  disabled,
  className,
  id,
}: {
  view: BodyView;
  selected: BodyRegion[];
  focused: BodyRegion | null;
  onToggle: (region: BodyRegion) => void;
  disabled?: boolean;
  className?: string;
  id?: string;
}) {
  const hatchId = `hatch-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const layers = REGION_LAYERS[view];
  const chosen = layers.filter((layer) => selected.includes(layer.region));
  // Front view faces the viewer, so the person's right side is on the viewer's left.
  const [leftSide, rightSide] = view === "front" ? ["Right", "Left"] : ["Left", "Right"];
  return (
    <svg
      id={id}
      viewBox={FIGURE_VIEWBOX}
      data-view={view}
      className={cn("mx-auto block h-80 w-auto max-w-full sm:h-96", className)}
      role="group"
      aria-label={`${VIEW_LABELS[view]} of the body. Select one or more regions.`}
    >
      <defs>
        <pattern id={hatchId} width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="5" height="5" fill="#7dbab1" />
          <line x1="0" y1="0" x2="0" y2="5" stroke="#ffffff" strokeOpacity="0.55" strokeWidth="1.6" />
        </pattern>
      </defs>
      <ellipse cx={CENTER_X} cy="515" rx="46" ry="4.5" className="fill-[#e3e9ef]" />
      {layers.map((layer) => (
        <RegionButton
          key={layer.region}
          layer={layer}
          selected={selected.includes(layer.region)}
          focused={focused === layer.region}
          disabled={disabled}
          onToggle={onToggle}
        />
      ))}
      <g aria-hidden="true" className="pointer-events-none" fill={`url(#${hatchId})`} stroke="#1f5d56" strokeWidth="1.8" strokeLinejoin="round" data-selected-overlay="">
        {chosen.flatMap((layer) =>
          layer.shapes.map((shape, index) => (
            <Fragment key={`${layer.region}-${index}`}>
              <path d={shape.d} />
              {shape.mirror ? <path d={shape.d} transform={MIRROR} /> : null}
            </Fragment>
          )),
        )}
      </g>
      <g aria-hidden="true" className="pointer-events-none" fill="none" stroke="#5d7590" strokeOpacity="0.5" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
        {DETAIL_LINES[view].map((d) => (
          <path key={d} d={d} />
        ))}
        {DETAIL_DOTS[view].map((dot) => (
          <circle key={`${dot.cx}-${dot.cy}`} cx={dot.cx} cy={dot.cy} r="1.4" fill="#5d7590" stroke="none" fillOpacity="0.6" />
        ))}
      </g>
      <g aria-hidden="true" className="pointer-events-none fill-[#5d7590] text-[12px] font-bold uppercase">
        <text x="22" y="530" textAnchor="middle">{leftSide}</text>
        <text x={FIGURE_WIDTH - 22} y="530" textAnchor="middle">{rightSide}</text>
      </g>
    </svg>
  );
}

function SelectionLegend() {
  return (
    <p className="mt-2 flex items-center justify-center gap-4 text-[11px] font-semibold text-slate-500" aria-hidden="true">
      <span className="inline-flex items-center gap-1.5">
        <span className="h-3 w-3 rounded-sm border border-[#5d7590] bg-[#f7f2ea]" /> Not selected
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="h-3 w-3 rounded-sm border-2 border-[#1f5d56] [background:repeating-linear-gradient(45deg,#7dbab1_0_2px,#b9dbd6_2px_4px)]" /> Selected
      </span>
    </p>
  );
}

export function BodyViewTabs({ view, onChange, controls }: { view: BodyView; onChange: (view: BodyView) => void; controls?: string }) {
  function onKeyDown(event: ReactKeyboardEvent<HTMLButtonElement>) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight" && event.key !== "Home" && event.key !== "End") return;
    event.preventDefault();
    const next = event.key === "Home" ? "front" : event.key === "End" ? "back" : view === "front" ? "back" : "front";
    onChange(next);
    const sibling = event.currentTarget.parentElement?.querySelector<HTMLButtonElement>(`[data-view="${next}"]`);
    sibling?.focus();
  }

  return (
    <div className="mx-auto grid w-full max-w-xs grid-cols-2 rounded-full bg-white p-1 ring-1 ring-slate-200" role="tablist" aria-label="Body view">
      {VIEWS.map((item) => {
        const active = view === item;
        return (
          <button
            key={item}
            type="button"
            role="tab"
            data-view={item}
            aria-selected={active}
            aria-controls={controls}
            tabIndex={active ? 0 : -1}
            className={cn(
              "min-h-10 rounded-full px-4 text-sm font-extrabold transition-colors motion-reduce:transition-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700",
              active ? "bg-[#0b1f33] text-white shadow-sm" : "text-slate-600 hover:bg-slate-100 hover:text-[#0b1f33]",
            )}
            onClick={() => onChange(item)}
            onKeyDown={onKeyDown}
          >
            {VIEW_LABELS[item]}
          </button>
        );
      })}
    </div>
  );
}

export function RegionChoices({
  selected,
  focused,
  disabled,
  onPick,
  heading = "Or choose with buttons",
}: {
  selected: BodyRegion[];
  focused?: BodyRegion | null;
  disabled?: boolean;
  onPick: (region: BodyRegion) => void;
  heading?: string;
}) {
  return (
    <div>
      <p className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-slate-500">{heading}</p>
      <div className="mt-2 space-y-3">
        {REGION_GROUPS.map((group) => (
          <fieldset key={group.label}>
            <legend className="text-xs font-bold text-[#3f5872]">{group.label}</legend>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {group.regions.map((id) => {
                const active = selected.includes(id);
                const only = regionView(id);
                return (
                  <button
                    key={id}
                    type="button"
                    disabled={disabled}
                    aria-pressed={active}
                    title={REGION_DESCRIPTIONS[id]}
                    onClick={() => onPick(id)}
                    className={cn(
                      "min-h-10 rounded-full px-3 text-xs font-bold transition-colors motion-reduce:transition-none disabled:opacity-50",
                      focused === id ? "ring-2 ring-[#0b1f33] ring-offset-1" : "",
                      active
                        ? "border border-[#1f5d56] bg-teal-700 text-white hover:bg-teal-800"
                        : "border border-slate-200 bg-white text-slate-700 hover:border-teal-300 hover:bg-teal-50/60 hover:text-teal-900",
                    )}
                  >
                    {active ? `✓ ${REGION_LABELS[id]}` : REGION_LABELS[id]}
                    {only !== "both" ? <span className="sr-only"> ({VIEW_LABELS[only]})</span> : null}
                  </button>
                );
              })}
            </div>
          </fieldset>
        ))}
      </div>
    </div>
  );
}

function OffViewNote({ selected, view }: { selected: BodyRegion[]; view: BodyView }) {
  const offView = hiddenInView(selected, view);
  if (!offView.length) return null;
  return (
    <p className="mt-1 text-center text-xs leading-5 text-slate-500">
      Also selected on the {VIEW_LABELS[view === "front" ? "back" : "front"]}: <span className="font-bold text-slate-700">{offView.map((id) => REGION_LABELS[id]).join(", ")}</span>
    </p>
  );
}

/** Inline body map card: pick areas, see what is selected, and hand off to the composer. */
export function BodyMapCard({
  view,
  onViewChange,
  selectedRegions,
  onToggleRegion,
  onClear,
  onDescribe,
  disabled,
}: {
  view: BodyView;
  onViewChange: (view: BodyView) => void;
  selectedRegions: BodyRegion[];
  onToggleRegion: (region: BodyRegion) => void;
  onClear: () => void;
  onDescribe: () => void;
  disabled?: boolean;
}) {
  function pickFromList(region: BodyRegion) {
    onViewChange(viewForRegion(region, view));
    onToggleRegion(region);
  }

  return (
    <section aria-labelledby="body-card-title" className="overflow-hidden rounded-3xl border border-slate-200 bg-white text-left shadow-sm">
      <header className="border-b border-slate-200 px-5 py-4">
        <h2 id="body-card-title" className="text-lg font-extrabold text-[#0b1f33]">
          Where do you feel it?
        </h2>
        <p className="mt-1 text-sm leading-6 text-slate-600">
          Tap one or more areas on the body, or use the list. Switch between front and back. Then describe your symptoms in your own words. This is not a diagnosis.
        </p>
      </header>
      <div className="grid md:grid-cols-2">
        <div className="border-b border-slate-200 bg-[#f4f7f9] px-4 py-4 md:border-b-0 md:border-r">
          <BodyViewTabs view={view} onChange={onViewChange} controls="body-card-figure" />
          <div className="mt-3 rounded-2xl border border-slate-200/80 bg-white px-2 pt-1 pb-2">
            <BodyFigure id="body-card-figure" view={view} selected={selectedRegions} focused={null} onToggle={onToggleRegion} disabled={disabled} className="h-[21rem] sm:h-[25rem]" />
          </div>
          <SelectionLegend />
          <OffViewNote selected={selectedRegions} view={view} />
        </div>
        <div className="flex flex-col gap-5 px-4 py-4 sm:px-5">
          <div>
            <p className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-slate-500">
              Selected areas{selectedRegions.length ? ` (${selectedRegions.length})` : ""}
            </p>
            {selectedRegions.length ? (
              <ul className="mt-2 flex flex-wrap gap-1.5" aria-label="Selected body areas" aria-live="polite">
                {selectedRegions.map((id) => (
                  <li key={id}>
                    <button
                      type="button"
                      className="inline-flex min-h-9 items-center gap-1 rounded-full bg-teal-700 px-3 text-xs font-bold text-white hover:bg-teal-800"
                      onClick={() => onToggleRegion(id)}
                      aria-label={`Remove ${REGION_LABELS[id]}`}
                    >
                      {REGION_LABELS[id]} <X size={12} aria-hidden />
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-slate-500" aria-live="polite">
                None yet.
              </p>
            )}
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={onDescribe}
                disabled={disabled}
                className="inline-flex min-h-10 items-center gap-1.5 rounded-full bg-teal-700 px-4 text-sm font-bold text-white hover:bg-teal-800 disabled:opacity-50"
              >
                <MessageSquareText size={15} aria-hidden /> {selectedRegions.length ? "Add symptoms" : "Open symptom picker"}
              </button>
              <button
                type="button"
                onClick={onClear}
                disabled={disabled || !selectedRegions.length}
                className="inline-flex min-h-10 items-center gap-1.5 rounded-full border border-slate-300 px-4 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                <RotateCcw size={14} aria-hidden /> Clear selection
              </button>
            </div>
          </div>
          <div className="border-t border-slate-200 pt-4">
            <RegionChoices selected={selectedRegions} disabled={disabled} onPick={pickFromList} heading="Body regions list" />
          </div>
          <p className="text-xs leading-5 text-slate-500">{BODY_MAP_DISCLAIMER}</p>
        </div>
      </div>
    </section>
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
  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onToggle();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onToggle]);

  function selectRegion(region: BodyRegion) {
    if (selectedRegions.includes(region) && activeRegion === region) {
      onToggleRegion(region);
      return;
    }
    onActiveRegion(region);
    if (!selectedRegions.includes(region)) onToggleRegion(region);
  }

  function pickFromList(region: BodyRegion) {
    onViewChange(viewForRegion(region, view));
    selectRegion(region);
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-labelledby="body-map-title">
      <button type="button" className="absolute inset-0 bg-[#0b1f33]/45" aria-label="Close body map" onClick={onToggle} />
      <section className="absolute inset-x-0 bottom-0 flex max-h-[min(94dvh,48rem)] flex-col overflow-hidden rounded-t-3xl bg-white shadow-2xl md:inset-auto md:left-1/2 md:top-1/2 md:w-[min(60rem,calc(100%-2rem))] md:-translate-x-1/2 md:-translate-y-1/2 md:rounded-3xl">
        <header className="flex items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
          <div>
            <p id="body-map-title" className="text-base font-extrabold text-[#0b1f33]">
              Where do you feel it?
            </p>
            <p className="mt-0.5 text-xs leading-5 text-slate-500">Select one or more areas on the front or back, then describe the symptoms in your own words. This is not a diagnosis.</p>
          </div>
          <button type="button" className="grid min-h-11 min-w-11 place-items-center rounded-full text-slate-500 hover:bg-slate-100" onClick={onToggle} aria-label="Close body map" aria-expanded={open}>
            <X size={18} />
          </button>
        </header>

        <div className="grid min-h-0 flex-1 overflow-y-auto md:grid-cols-[minmax(17rem,22rem)_1fr]">
          <div className="border-b border-slate-200 bg-[#f4f7f9] px-4 py-4 md:border-b-0 md:border-r">
            <BodyViewTabs view={view} onChange={onViewChange} controls="body-map-figure" />
            <div className="mt-3 rounded-2xl border border-slate-200/80 bg-white px-2 pt-1 pb-2">
              <BodyFigure id="body-map-figure" view={view} selected={selectedRegions} focused={activeRegion} onToggle={selectRegion} disabled={disabled} className="h-80 sm:h-[24rem]" />
            </div>
            <SelectionLegend />
            <p className="mt-2 min-h-5 text-center text-xs font-bold text-slate-600" aria-live="polite">
              {activeRegion ? `Editing: ${REGION_DESCRIPTIONS[activeRegion]}` : "Select an area. Hover it to see its name."}
            </p>
            <OffViewNote selected={selectedRegions} view={view} />
          </div>

          <div className="px-4 py-4 sm:px-5">
            <RegionChoices selected={selectedRegions} focused={activeRegion} disabled={disabled} onPick={pickFromList} />

            <div className="mt-5 border-t border-slate-200 pt-4">
              {activeRegion && suggestedSymptoms.length ? (
                <>
                  <p className="text-xs font-bold text-slate-700">Common words for {REGION_LABELS[activeRegion].toLowerCase()} discomfort</p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
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
                            "min-h-10 rounded-full px-3 text-xs font-bold transition-colors",
                            active ? "bg-[#0b1f33] text-white" : "border border-slate-200 bg-white text-slate-700 hover:border-slate-400",
                          )}
                        >
                          {active ? `✓ ${item}` : item}
                        </button>
                      );
                    })}
                  </div>
                </>
              ) : (
                <p className="text-sm leading-6 text-slate-600">Select an area to see common ways to describe it. You can still type your symptoms in your own words.</p>
              )}
            </div>
          </div>
        </div>

        <footer className="border-t border-slate-200 bg-white px-4 py-3 sm:px-5">
          {selectedRegions.length || selectedSymptoms.length ? (
            <div className="mb-3">
              <p className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-slate-500">Selected</p>
              <ul className="mt-1.5 flex flex-wrap gap-1.5" aria-label="Selected areas and symptoms">
                {selectedRegions.map((id) => (
                  <li key={`region-${id}`}>
                    <button
                      type="button"
                      className="inline-flex min-h-9 items-center gap-1 rounded-full bg-teal-700 px-3 text-xs font-bold text-white hover:bg-teal-800"
                      onClick={() => onToggleRegion(id)}
                      aria-label={`Remove ${REGION_LABELS[id]}`}
                    >
                      {REGION_LABELS[id]} <X size={12} aria-hidden />
                    </button>
                  </li>
                ))}
                {selectedSymptoms.map((item) => (
                  <li key={`symptom-${item}`}>
                    <button
                      type="button"
                      className="inline-flex min-h-9 items-center gap-1 rounded-full border border-slate-300 px-3 text-xs font-bold text-slate-700 hover:border-slate-500"
                      onClick={() => onToggleSymptom(item)}
                      aria-label={`Remove ${item}`}
                    >
                      {item} <X size={12} aria-hidden />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="mb-3 text-xs leading-5 text-slate-500">{BODY_MAP_DISCLAIMER}</p>
          )}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <button
              type="button"
              className="inline-flex min-h-11 items-center gap-1.5 rounded-full px-3 text-sm font-bold text-slate-600 hover:bg-slate-100 disabled:opacity-50"
              onClick={onClear}
              disabled={disabled || (!selectedRegions.length && !selectedSymptoms.length)}
            >
              <RotateCcw size={14} aria-hidden /> Clear all
            </button>
            <button type="button" className="min-h-11 rounded-full bg-teal-700 px-5 text-sm font-extrabold text-white hover:bg-teal-800" onClick={onToggle}>
              Use these areas
            </button>
          </div>
        </footer>
      </section>
    </div>
  );
}
