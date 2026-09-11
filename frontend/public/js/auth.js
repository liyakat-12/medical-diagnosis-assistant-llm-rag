const TOKEN_KEY = "mediassist_token";
const USER_KEY = "mediassist_user";

const form = document.getElementById("auth-form");
const nameField = document.getElementById("name-field");
const nameInput = document.getElementById("name");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const errorEl = document.getElementById("auth-error");
const submitBtn = document.getElementById("auth-submit");
const tabs = document.querySelectorAll(".tab");

let mode = "login";

if (localStorage.getItem(TOKEN_KEY)) {
  window.location.replace("/app");
}

function setMode(next) {
  mode = next;
  tabs.forEach((tab) => {
    const on = tab.dataset.mode === next;
    tab.classList.toggle("bg-white", on);
    tab.classList.toggle("text-teal-800", on);
    tab.classList.toggle("shadow-sm", on);
    tab.classList.toggle("text-slate-500", !on);
  });
  nameField.classList.toggle("hidden", next !== "register");
  nameInput.required = next === "register";
  passwordInput.autocomplete = next === "register" ? "new-password" : "current-password";
  submitBtn.textContent = next === "register" ? "Create account" : "Enter clinic";
}

tabs.forEach((tab) => tab.addEventListener("click", () => setMode(tab.dataset.mode)));

document.getElementById("fill-demo").addEventListener("click", () => {
  setMode("login");
  emailInput.value = "demo@clinic.local";
  passwordInput.value = "demo123";
  emailInput.focus();
});

function showError(message) {
  errorEl.classList.toggle("hidden", !message);
  errorEl.textContent = message || "";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("");
  submitBtn.disabled = true;
  const payload = {
    email: emailInput.value.trim(),
    password: passwordInput.value,
  };
  if (mode === "register") payload.name = nameInput.value.trim();
  try {
    const response = await fetch(mode === "register" ? "/api/auth/register" : "/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
      throw new Error(detail || "Could not sign in.");
    }
    localStorage.setItem(TOKEN_KEY, data.token);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    window.location.href = "/app";
  } catch (err) {
    showError(err.message || "Could not sign in. Is the Python API running on port 8000?");
  } finally {
    submitBtn.disabled = false;
  }
});
