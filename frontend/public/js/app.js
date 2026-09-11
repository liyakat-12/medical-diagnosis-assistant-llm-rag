const TOKEN_KEY = "mediassist_token";
const USER_KEY = "mediassist_user";

const EXAMPLES = [
  { title: "Runny nose", text: "I have a runny nose and sore throat for two days", hint: "Cold-like" },
  { title: "Burning urine", text: "Burning when I pee and I need to go often", hint: "UTI-like" },
  { title: "Chest pain", text: "Sudden crushing chest pain and shortness of breath", hint: "Emergency check" },
  { title: "One-sided headache", text: "Throbbing headache on one side with nausea and light sensitivity", hint: "Migraine-like" },
];

const SHORT_GUIDANCE = {
  self_care: "Home care is usually enough. See a doctor if it worsens.",
  consult_doctor: "Book a doctor visit soon.",
  emergency: "Seek emergency care now.",
};

const TRIAGE_STYLE = {
  self_care: "bg-gradient-to-r from-emerald-500 to-sky-500",
  consult_doctor: "bg-gradient-to-r from-amber-400 to-orange-500",
  emergency: "bg-gradient-to-r from-rose-500 to-red-600",
};

const token = localStorage.getItem(TOKEN_KEY);
if (!token) window.location.replace("/");

const queryEl = document.getElementById("query");
const submitBtn = document.getElementById("submit");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");
const examplesEl = document.getElementById("examples");
const userChip = document.getElementById("user-chip");

try {
  const user = JSON.parse(localStorage.getItem(USER_KEY) || "{}");
  userChip.textContent = user.name || user.email || "Signed in";
  userChip.classList.remove("hidden");
} catch {
  userChip.textContent = "Signed in";
}

examplesEl.innerHTML = EXAMPLES.map(
  (item) => `
    <button type="button" class="chip min-w-[10rem] rounded-2xl bg-white px-4 py-3 text-left shadow-md shadow-teal-900/5 hover:-translate-y-0.5" data-text="${item.text}">
      <span class="block text-sm font-extrabold text-slate-900">${item.title}</span>
      <span class="block text-xs font-semibold text-slate-500">${item.hint}</span>
    </button>`
).join("");

examplesEl.addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;
  queryEl.value = chip.dataset.text;
  queryEl.focus();
});

document.getElementById("logout").addEventListener("click", async () => {
  try {
    await fetch("/api/auth/logout", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    /* ignore */
  }
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  window.location.replace("/");
});

function setBusy(busy, label) {
  submitBtn.disabled = busy;
  statusEl.classList.toggle("hidden", !label);
  statusEl.textContent = label || "";
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderResult(data) {
  if (data.refused) {
    resultEl.innerHTML = `
      <article class="rounded-[1.5rem] border border-rose-100 bg-white p-6 shadow-sm">
        <h3 class="text-xs font-extrabold uppercase tracking-widest text-rose-500">Request not answered</h3>
        <p class="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">${escapeHtml(data.answer)}</p>
      </article>`;
    resultEl.classList.remove("hidden");
    resultEl.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }

  const level = data.triage?.level || "consult_doctor";
  const banner = TRIAGE_STYLE[level] || TRIAGE_STYLE.consult_doctor;
  const ranked = (data.citations && data.citations.length ? data.citations : data.possible_conditions || []).slice(0, 4);

  const outcomeHtml = ranked.length
    ? ranked
        .map((item, index) => {
          const name = escapeHtml(item.condition || item.title || "Match");
          const source = escapeHtml(item.source || "");
          const pct = Math.round((item.relevance_score || 0) * 100);
          return `<div class="flex items-center justify-between gap-3 rounded-2xl border border-emerald-100 bg-emerald-50/70 px-4 py-3">
            <span>
              <span class="block font-extrabold text-slate-900">${index + 1}. ${name}</span>
              <span class="text-xs font-semibold text-slate-500">${source}</span>
            </span>
            <span class="rounded-full bg-white px-2.5 py-1 text-xs font-extrabold text-teal-700">${pct}%</span>
          </div>`;
        })
        .join("")
    : `<p class="text-sm text-slate-500">No matching conditions in the knowledge base.</p>`;

  const citations = data.citations || [];
  const citationHtml = citations.length
    ? citations
        .map((item) => {
          const title = escapeHtml(item.title || item.condition || "Source");
          const source = escapeHtml(item.source || "");
          const inner = `<span class="block font-extrabold text-slate-900">${title}</span><span class="text-xs font-semibold text-slate-500">${source}</span>`;
          if (item.url) {
            return `<a class="block rounded-2xl border border-emerald-100 px-4 py-3 no-underline hover:bg-emerald-50/70" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${inner}</a>`;
          }
          return `<div class="rounded-2xl border border-emerald-100 px-4 py-3">${inner}</div>`;
        })
        .join("")
    : `<p class="text-sm text-slate-500">No sources were retrieved.</p>`;

  resultEl.innerHTML = `
    <article class="rounded-[1.5rem] bg-white p-6 shadow-sm">
      <h3 class="text-xs font-extrabold uppercase tracking-widest text-slate-400">Possible matches</h3>
      <div class="mt-3 grid gap-2">${outcomeHtml}</div>
    </article>
    <div class="${banner} flex items-center justify-between rounded-[1.5rem] px-5 py-4 text-white">
      <div>
        <h3 class="text-lg font-extrabold">${escapeHtml(data.triage?.label || "Urgency")}</h3>
        <p class="mt-1 text-sm text-white/90">${escapeHtml(SHORT_GUIDANCE[level] || data.triage?.guidance || "")}</p>
      </div>
    </div>
    <article class="rounded-[1.5rem] bg-white p-6 shadow-sm">
      <h3 class="text-xs font-extrabold uppercase tracking-widest text-slate-400">Citations</h3>
      <div class="mt-3 grid gap-2">${citationHtml}</div>
      <p class="mt-4 text-xs leading-5 text-slate-500">${escapeHtml(data.disclaimer)}</p>
    </article>
  `;
  resultEl.classList.remove("hidden");
  resultEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function checkSymptoms() {
  const query = queryEl.value.trim();
  if (!query) {
    queryEl.focus();
    return;
  }
  setBusy(true, "Checking safety and matching documents…");
  try {
    const response = await fetch("/api/diagnose", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ query, top_k: 4 }),
    });
    if (response.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      window.location.replace("/");
      return;
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Could not complete the check.");
    renderResult(data);
    setBusy(false, "");
  } catch (err) {
    resultEl.innerHTML = `<article class="rounded-[1.5rem] bg-white p-6 shadow-sm"><p class="text-sm text-rose-600">${escapeHtml(err.message)}</p></article>`;
    resultEl.classList.remove("hidden");
    setBusy(false, "");
  }
}

submitBtn.addEventListener("click", checkSymptoms);
queryEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    checkSymptoms();
  }
});
