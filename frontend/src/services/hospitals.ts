import type { HospitalSearchResponse } from "../types";
import { apiFetch } from "./api";

const CACHE_TTL_MS = 5 * 60 * 1000;
const cache = new Map<string, { expires: number; data: HospitalSearchResponse }>();

function roundCoord(value: number): number {
  return Math.round(value * 1000) / 1000;
}

function readCache(key: string): HospitalSearchResponse | null {
  const hit = cache.get(key);
  if (!hit) return null;
  if (hit.expires <= Date.now()) {
    cache.delete(key);
    return null;
  }
  return hit.data;
}

function writeCache(key: string, data: HospitalSearchResponse): HospitalSearchResponse {
  if (!data.error) {
    cache.set(key, { expires: Date.now() + CACHE_TTL_MS, data });
  }
  return data;
}

async function cachedFetch(key: string, path: string, signal?: AbortSignal): Promise<HospitalSearchResponse> {
  const hit = readCache(key);
  if (hit) return hit;
  const data = await apiFetch<HospitalSearchResponse>(path, { signal });
  return writeCache(key, data);
}

export function fetchNearbyHospitals(lat: number, lng: number, signal?: AbortSignal): Promise<HospitalSearchResponse> {
  const key = `geo:${roundCoord(lat)},${roundCoord(lng)}`;
  return cachedFetch(key, `/hospitals/nearby?lat=${encodeURIComponent(lat)}&lng=${encodeURIComponent(lng)}`, signal);
}

export function fetchHospitalsAtPlace(place: string, signal?: AbortSignal): Promise<HospitalSearchResponse> {
  const query = place.trim();
  const key = `place:${query.toLowerCase()}`;
  return cachedFetch(key, `/hospitals/nearby?q=${encodeURIComponent(query)}`, signal);
}

export function fetchHospitalsNearMe(signal?: AbortSignal): Promise<HospitalSearchResponse> {
  return cachedFetch("ip:me", "/hospitals/nearby", signal);
}
