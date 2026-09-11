const TOKEN_KEY = "mediassist_token";
const USER_KEY = "mediassist_user";

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function getUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || "null");
  } catch {
    return null;
  }
}

function isLoggedIn() {
  return Boolean(getToken());
}

function saveSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

async function logoutAndLeave() {
  const token = getToken();
  try {
    if (token) {
      await fetch("/api/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    }
  } catch {
    /* ignore */
  }
  clearSession();
  window.location.replace("/");
}

function renderNav() {
  const host = document.getElementById("nav-actions");
  if (!host) return;
  const user = getUser();
  if (isLoggedIn()) {
    host.innerHTML = `
      <a href="/chat" class="rounded-full bg-teal-700 px-4 py-2 text-sm font-bold text-white hover:bg-teal-800">Chat</a>
      <span class="hidden text-sm font-semibold text-slate-600 sm:inline">${escapeHtml(user?.name || user?.email || "Signed in")}</span>
      <button type="button" id="nav-logout" class="rounded-full border border-emerald-200 bg-white px-4 py-2 text-sm font-bold text-teal-800 hover:bg-emerald-50">Sign out</button>
    `;
    document.getElementById("nav-logout")?.addEventListener("click", logoutAndLeave);
  } else {
    host.innerHTML = `
      <a href="/login" class="rounded-full border border-emerald-200 bg-white px-4 py-2 text-sm font-bold text-teal-800 hover:bg-emerald-50">Login</a>
      <a href="/register" class="rounded-full bg-teal-700 px-4 py-2 text-sm font-bold text-white hover:bg-teal-800">Register</a>
    `;
  }
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

document.addEventListener("DOMContentLoaded", renderNav);
