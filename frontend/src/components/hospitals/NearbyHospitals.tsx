import { useEffect, useRef, useState, type FormEvent } from "react";
import { MapPin, Phone } from "lucide-react";
import { fetchHospitalsAtPlace, fetchHospitalsNearMe, fetchNearbyHospitals } from "../../services/hospitals";
import type { NearbyHospital } from "../../types";
import { EMERGENCY_NUMBER, EMERGENCY_TEL } from "../../utils/emergency";
import { cn } from "../../lib/cn";

function phoneHref(phone: string): string {
  const cleaned = phone.replace(/[^\d+]/g, "");
  return cleaned ? `tel:${cleaned}` : EMERGENCY_TEL;
}

function isValidCoord(lat?: number, lng?: number): boolean {
  return (
    typeof lat === "number" &&
    typeof lng === "number" &&
    Number.isFinite(lat) &&
    Number.isFinite(lng) &&
    !(Math.abs(lat) < 1e-6 && Math.abs(lng) < 1e-6) &&
    lat >= -90 &&
    lat <= 90 &&
    lng >= -180 &&
    lng <= 180
  );
}

function latLngToWorld(lat: number, lng: number, zoom: number): { x: number; y: number } {
  const n = 2 ** zoom;
  const x = ((lng + 180) / 360) * n;
  const latRad = (lat * Math.PI) / 180;
  const y = ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n;
  return { x, y };
}

function chooseZoom(center: { lat: number; lng: number }, points: { lat: number; lng: number }[]): number {
  for (let zoom = 14; zoom >= 11; zoom -= 1) {
    const world = latLngToWorld(center.lat, center.lng, zoom);
    const tile = { x: Math.floor(world.x), y: Math.floor(world.y) };
    const inside = points.every((point) => {
      const pos = latLngToWorld(point.lat, point.lng, zoom);
      return Math.abs(pos.x - tile.x) < 1.45 && Math.abs(pos.y - tile.y) < 1.45;
    });
    if (inside) return zoom;
  }
  return 12;
}

function googleOpenUrl(origin: { lat: number; lng: number } | null, selected: NearbyHospital | null): string {
  if (selected) return selected.maps_url;
  if (origin) return `https://www.google.com/maps/search/hospitals/@${origin.lat},${origin.lng},14z`;
  return "https://www.google.com/maps/search/hospitals";
}

function HospitalMap({
  lat,
  lng,
  label,
  hospitals,
  selected,
  onSelect,
}: {
  lat: number;
  lng: number;
  label: string;
  hospitals: NearbyHospital[];
  selected: NearbyHospital | null;
  onSelect: (hospital: NearbyHospital) => void;
}) {
  const zoom = chooseZoom({ lat, lng }, hospitals);
  const center = latLngToWorld(lat, lng, zoom);
  const tile = { x: Math.floor(center.x), y: Math.floor(center.y) };
  const tiles: { x: number; y: number }[] = [];
  for (let dy = -1; dy <= 1; dy += 1) {
    for (let dx = -1; dx <= 1; dx += 1) {
      tiles.push({ x: tile.x + dx, y: tile.y + dy });
    }
  }

  return (
    <div className="mb-3 overflow-hidden rounded-2xl border border-teal-100 bg-slate-100">
      <div className="relative h-64 w-full md:h-80" role="img" aria-label={label}>
        <div className="absolute inset-0 grid grid-cols-3 grid-rows-3">
          {tiles.map((item) => (
            <img
              key={`${item.x}-${item.y}`}
              alt=""
              src={`https://tile.openstreetmap.org/${zoom}/${item.x}/${item.y}.png`}
              referrerPolicy="no-referrer"
              className="h-full w-full object-cover"
            />
          ))}
        </div>
        {hospitals.map((hospital) => {
          const world = latLngToWorld(hospital.lat, hospital.lng, zoom);
          const left = ((world.x - (tile.x - 1)) / 3) * 100;
          const top = ((world.y - (tile.y - 1)) / 3) * 100;
          if (left < 2 || left > 98 || top < 2 || top > 98) return null;
          const active = selected?.name === hospital.name && selected?.lat === hospital.lat;
          return (
            <button
              key={`${hospital.name}-${hospital.lat}`}
              type="button"
              title={hospital.name}
              aria-label={hospital.name}
              onClick={() => onSelect(hospital)}
              className={cn(
                "absolute z-10 -translate-x-1/2 -translate-y-full drop-shadow",
                active ? "text-red-600" : "text-teal-800",
              )}
              style={{ left: `${left}%`, top: `${top}%` }}
            >
              <MapPin size={active ? 30 : 22} fill="currentColor" />
            </button>
          );
        })}
      </div>
      <div className="flex items-center justify-between gap-2 border-t border-teal-100 bg-teal-50 px-3 py-2">
        <p className="truncate text-xs font-semibold text-slate-600">
          {label}
          <span className="ml-1 font-medium text-slate-400">© OpenStreetMap</span>
        </p>
        <a
          href={`https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=15/${lat}/${lng}`}
          target="_blank"
          rel="noreferrer"
          className="shrink-0 text-xs font-extrabold text-teal-800"
        >
          Open map
        </a>
      </div>
    </div>
  );
}

export function NearbyHospitals({ active }: { active: boolean }) {
  const [hospitals, setHospitals] = useState<NearbyHospital[]>([]);
  const [origin, setOrigin] = useState<{ lat: number; lng: number } | null>(null);
  const [selected, setSelected] = useState<NearbyHospital | null>(null);
  const [areaLabel, setAreaLabel] = useState("");
  const [status, setStatus] = useState("Allow location to see hospitals near you.");
  const [loading, setLoading] = useState(false);
  const [place, setPlace] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const askedRef = useRef(false);

  function applyResult(result: Awaited<ReturnType<typeof fetchHospitalsNearMe>>, fallbackLabel: string) {
    const here = result.origin;
    const rows = (result.hospitals || []).filter((item) => isValidCoord(item.lat, item.lng));
    if (here && isValidCoord(here.lat, here.lng)) setOrigin({ lat: here.lat, lng: here.lng });
    setHospitals(rows);
    setSelected(rows[0] || null);
    setAreaLabel(here?.label || fallbackLabel);
    setStatus(result.error || (rows.length ? "" : "No hospitals were found nearby."));
  }

  async function runSearch(task: (signal: AbortSignal) => Promise<void>) {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    try {
      await task(controller.signal);
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setStatus(err instanceof Error ? err.message : "Unable to load nearby hospitals.");
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
        setLoading(false);
      }
    }
  }

  async function loadAround(here: { lat: number; lng: number }, note: string) {
    setOrigin(here);
    setStatus(note);
    await runSearch(async (signal) => {
      const result = await fetchNearbyHospitals(here.lat, here.lng, signal);
      applyResult(result, note);
    });
  }

  async function loadFromNetwork() {
    setStatus("Finding hospitals in your city...");
    await runSearch(async (signal) => {
      const result = await fetchHospitalsNearMe(signal);
      applyResult(result, result.origin?.label || "your city");
    });
  }

  function useMyLocation() {
    if (!navigator.geolocation) {
      void loadFromNetwork();
      return;
    }
    setLoading(true);
    setStatus("Getting your current location...");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        void loadAround(
          { lat: position.coords.latitude, lng: position.coords.longitude },
          "Showing hospitals near your current location.",
        );
      },
      () => {
        void loadFromNetwork();
      },
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 120000 },
    );
  }

  async function searchPlace(event: FormEvent) {
    event.preventDefault();
    const query = place.trim();
    if (query.length < 2 || loading) return;
    setStatus(`Finding hospitals near ${query}...`);
    await runSearch(async (signal) => {
      const result = await fetchHospitalsAtPlace(query, signal);
      applyResult(result, query);
    });
  }

  useEffect(() => {
    if (!active || askedRef.current) return;
    askedRef.current = true;
    useMyLocation();
    return () => abortRef.current?.abort();
    // Ask once when the hospital panel first becomes visible.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  if (!active) return null;

  const pin = origin || (selected ? { lat: selected.lat, lng: selected.lng } : null);

  return (
    <section className="min-w-0 rounded-3xl border border-teal-100 bg-white px-4 py-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <p id="hospital-finder-title" className="text-sm font-extrabold text-slate-900">Nearby hospitals</p>
          <p className="text-xs text-slate-500">Uses your live location. Bengaluru shows Bengaluru hospitals; Srinagar shows Srinagar hospitals.</p>
        </div>
        <a
          href={EMERGENCY_TEL}
          className="inline-flex min-h-11 shrink-0 items-center rounded-full bg-red-600 px-3 text-xs font-extrabold text-white hover:bg-red-700"
        >
          Call {EMERGENCY_NUMBER}
        </a>
      </div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={useMyLocation}
          disabled={loading}
          className="inline-flex min-h-10 items-center rounded-full bg-sky-600 px-3 text-xs font-extrabold text-white hover:bg-sky-700 disabled:opacity-60"
        >
          Use my location
        </button>
        <form className="flex min-w-0 flex-1 gap-2" onSubmit={(event) => void searchPlace(event)}>
          <input
            value={place}
            onChange={(event) => setPlace(event.target.value)}
            placeholder="Or type a city: Bengaluru, Srinagar"
            disabled={loading}
            className="min-h-10 min-w-0 flex-1 rounded-full border border-teal-200 px-3 text-sm disabled:bg-slate-50"
          />
          <button type="submit" disabled={loading} className="min-h-10 rounded-full border border-teal-300 px-3 text-xs font-extrabold text-teal-900 disabled:opacity-60">
            Show
          </button>
        </form>
      </div>
      {pin ? (
        <HospitalMap
          lat={pin.lat}
          lng={pin.lng}
          label={selected?.name || areaLabel || "Hospitals near you"}
          hospitals={hospitals}
          selected={selected}
          onSelect={setSelected}
        />
      ) : (
        <div className="mb-3 flex h-40 items-center justify-center rounded-2xl border border-dashed border-teal-200 bg-teal-50 px-4 text-center text-sm font-semibold text-teal-800">
          Allow location, or type your city, to see the live map.
        </div>
      )}
      <div className="mb-2 flex justify-end gap-3">
        {!loading && status && !hospitals.length ? (
          <button type="button" onClick={useMyLocation} className="text-xs font-extrabold text-teal-800">
            Try again
          </button>
        ) : null}
        <a
          href={googleOpenUrl(origin, selected)}
          target="_blank"
          rel="noreferrer"
          className="text-xs font-extrabold text-teal-800"
        >
          Open in Google Maps
        </a>
      </div>
      {loading ? <p className="text-sm font-semibold text-teal-800">{status || "Finding hospitals near you..."}</p> : null}
      {!loading && status ? <p className="text-sm text-slate-600">{status}</p> : null}
      {hospitals.length ? (
        <ul className="mt-3 space-y-2">
          {hospitals.map((item) => (
            <li key={`${item.name}-${item.lat}`}>
              <button
                type="button"
                onClick={() => setSelected(item)}
                className={cn(
                  "w-full rounded-2xl border px-3 py-3 text-left",
                  selected?.name === item.name && selected?.lat === item.lat
                    ? "border-teal-600 bg-teal-50"
                    : "border-teal-100 hover:bg-teal-50/70",
                )}
              >
                <p className="break-anywhere text-sm font-extrabold text-slate-900">
                  • {item.name}
                  {item.emergency ? <span className="ml-2 text-xs font-bold text-red-700">Emergency</span> : null}
                </p>
                <p className="mt-1 text-xs leading-5 text-slate-500">
                  {item.distance_km} km · {item.address}
                </p>
                <div className="mt-2 flex flex-wrap gap-3 text-xs font-bold">
                  {item.phone ? (
                    <a href={phoneHref(item.phone)} className="inline-flex items-center gap-1 text-teal-800" onClick={(event) => event.stopPropagation()}>
                      <Phone size={13} /> {item.phone}
                    </a>
                  ) : (
                    <a href={EMERGENCY_TEL} className="inline-flex items-center gap-1 text-red-700" onClick={(event) => event.stopPropagation()}>
                      <Phone size={13} /> No listed number · Call {EMERGENCY_NUMBER}
                    </a>
                  )}
                  <a href={item.maps_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-slate-600" onClick={(event) => event.stopPropagation()}>
                    <MapPin size={13} /> Directions
                  </a>
                </div>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
