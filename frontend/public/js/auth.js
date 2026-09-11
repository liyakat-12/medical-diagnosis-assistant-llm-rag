const form = document.getElementById("auth-form");
const mode = form?.dataset.mode || "login";
const errorEl = document.getElementById("auth-error");
const submitBtn = document.getElementById("auth-submit");

if (isLoggedIn()) {
  window.location.replace("/chat");
}

function showError(message) {
  if (!errorEl) return;
  errorEl.classList.toggle("hidden", !message);
  errorEl.textContent = message || "";
}

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("");
  if (submitBtn) submitBtn.disabled = true;
  const payload = {
    email: document.getElementById("email")?.value.trim(),
    password: document.getElementById("password")?.value,
  };
  if (mode === "register") payload.name = document.getElementById("name")?.value.trim();
  try {
    const response = await fetch(mode === "register" ? "/api/auth/register" : "/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
      throw new Error(detail || "Could not continue.");
    }
    saveSession(data.token, data.user);
    window.location.href = "/chat";
  } catch (err) {
    showError(err.message || "Could not continue. Is the API running on port 8000?");
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
});
