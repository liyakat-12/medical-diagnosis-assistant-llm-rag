import type { User } from "../types";
import { apiFetch } from "./api";

export function fetchMe(): Promise<User> {
  return apiFetch<User>("/auth/me");
}

export function login(email: string, password: string): Promise<User> {
  return apiFetch<User>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function register(name: string, email: string, password: string): Promise<User> {
  return apiFetch<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
}

export function logout(): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>("/auth/logout", { method: "POST" });
}

export function refreshSession(): Promise<User> {
  return apiFetch<User>("/auth/refresh", { method: "POST" });
}

export function updateProfile(fields: { name?: string; medical_disclaimer_accepted?: boolean }): Promise<User> {
  return apiFetch<User>("/users/me", {
    method: "PATCH",
    body: JSON.stringify(fields),
  });
}
