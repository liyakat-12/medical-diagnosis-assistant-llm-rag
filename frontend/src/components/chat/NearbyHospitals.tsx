import { useEffect, useState } from "react";
import { MapPin, Phone } from "lucide-react";
import { fetchNearbyHospitals } from "../../services/hospitals";
import type { NearbyHospital } from "../../types";
import { EMERGENCY_NUMBER, EMERGENCY_TEL } from "../../utils/emergency";
import { cn } from "../../lib/cn";

function phoneHref(phone: string): string {
  const cleaned = phone.replace(/[^\d+]/g, "");
  return cleaned ? `tel:${cleaned}` : EMERGENCY_TEL;
}

function googleEmbedSrc(origin: { lat: number; lng: number } | null, selected: NearbyHospital | null): string {
  if (selected) {
    const query = `${selected.name} @${selected.lat},${selected.lng}`;
    return `https://maps.google.com/maps?q=${encodeURIComponent(query)}&z=16&output=embed`;
  }
  if (origin) {
    return `https://maps.google.com/maps?q=hospital&ll=${origin.lat},${origin.lng}&z=14&output=embed`;
  }
  return "";
}

function googleOpenUrl(origin: { lat: number; lng: number } | null, selected: NearbyHospital | null): string {
  if (selected) return selected.maps_url;
  if (origin) return `https://www.google.com/maps/search/hospitals/@${origin.lat},${origin.lng},14z`;
  return "https://www.google.com/maps/search/hospitals";
}

export function NearbyHospitals({ active }: { active: boolean }) {
  const [hospitals, setHospitals] = useState<NearbyHospital[]>([]);
  const [origin, setOrigin] = useState<{ lat: number; lng: number } | null>(null);
  const [selected, setSelected] = useState<NearbyHospital | null>(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    setLoading(true);
    setStatus("Finding hospitals near you...");

    if (!navigator.geolocation) {
      setLoading(false);
      setStatus("Location is not available in this browser. Call 108 for ambulance help.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const here = { lat: position.coords.latitude, lng: position.coords.longitude };
        if (!cancelled) setOrigin(here);
        try {
          const result = await fetchNearbyHospitals(here.lat, here.lng);
          if (cancelled) return;
          setHospitals(result.hospitals);
          setSelected(result.hospitals[0] || null);
          setStatus(result.error || (result.hospitals.length ? "" : "No hospitals were found nearby."));
        } catch (err) {
          if (!cancelled) setStatus(err instanceof Error ? err.message : "Unable to load nearby hospitals.");
        } finally {
          if (!cancelled) setLoading(false);
        }
      },
      () => {
        if (cancelled) return;
        setLoading(false);
        setStatus("Allow location access to see the map and nearby hospitals, or call 108.");
      },
      { enableHighAccuracy: false, timeout: 12000, maximumAge: 300000 },
    );

    return () => {
      cancelled = true;
    };
  }, [active]);

  if (!active) return null;

  const embedSrc = googleEmbedSrc(origin, selected);

  return (
    <section className="min-w-0 rounded-3xl border border-teal-100 bg-white px-4 py-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-extrabold text-slate-900">Nearby hospitals</p>
          <p className="text-xs text-slate-500">Map, names, distance, and contact numbers around you.</p>
        </div>
        <a
          href={EMERGENCY_TEL}
          className="inline-flex min-h-11 shrink-0 items-center rounded-full bg-red-600 px-3 text-xs font-extrabold text-white hover:bg-red-700"
        >
          Call {EMERGENCY_NUMBER}
        </a>
      </div>
      {embedSrc ? (
        <div className="mb-3 overflow-hidden rounded-2xl border border-teal-100">
          <iframe
            title="Nearby hospitals map"
            src={embedSrc}
            className="h-64 w-full border-0 md:h-80"
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
            allowFullScreen
          />
          <div className="flex items-center justify-between gap-2 border-t border-teal-100 bg-teal-50 px-3 py-2">
            <p className="truncate text-xs font-semibold text-slate-600">
              {selected ? selected.name : "Hospitals near your location"}
            </p>
            <a
              href={googleOpenUrl(origin, selected)}
              target="_blank"
              rel="noreferrer"
              className="shrink-0 text-xs font-extrabold text-teal-800"
            >
              Open in Google Maps
            </a>
          </div>
        </div>
      ) : null}
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
