import type { HospitalSearchResponse } from "../types";
import { apiFetch } from "./api";

export function fetchNearbyHospitals(lat: number, lng: number): Promise<HospitalSearchResponse> {
  return apiFetch<HospitalSearchResponse>(`/hospitals/nearby?lat=${encodeURIComponent(lat)}&lng=${encodeURIComponent(lng)}`);
}
