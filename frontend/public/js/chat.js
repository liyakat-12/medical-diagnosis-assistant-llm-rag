if (!isLoggedIn()) {
  window.location.replace("/login");
}

const token = getToken();
const historyEl = document.getElementById("history");
const messagesEl = document.getElementById("messages");
const queryEl = document.getElementById("query");
const sendBtn = document.getElementById("send");
const statusEl = document.getElementById("status");
const sidebar = document.getElementById("sidebar");
const ACTIVE_KEY = "mediassist_active_chat";

const STARTERS = [
  { title: "Cold-like symptoms", text: "I have a runny nose and sore throat for two days" },
  { title: "Burning when I pee", text: "Burning when I pee and I need to go often" },
  { title: "Chest pain", text: "Sudden crushing chest pain and shortness of breath" },
  { title: "One-sided headache", text: "Throbbing headache on one side with nausea and light sensitivity" },
];

const SHORT_GUIDANCE = {
  self_care: "Home care is usually enough. See a doctor if it worsens.",
  consult_doctor: "Book a doctor visit soon.",
  emergency: "Seek emergency care now.",
};

const TRIAGE_STYLE = {
  self_care: "bg-emerald-600",
  consult_doctor: "bg-amber-500",
  emergency: "bg-rose-600",
};

let chats = [];
let activeId = sessionStorage.getItem(ACTIVE_KEY);
let busy = false;
let currentMessages = [];
let selectedSymptoms = new Set();

const picksEl = document.getElementById("symptom-picks");

document.getElementById("toggle-sidebar")?.addEventListener("click", () => {
  sidebar.classList.toggle("sidebar-closed");
});

document.getElementById("new-chat")?.addEventListener("click", () => {
  selectedSymptoms = new Set();
  if (queryEl) queryEl.value = "";
  renderSymptomPicks();
  createChat();
  sidebar.classList.add("sidebar-closed");
});

document.getElementById("composer")?.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage();
});

queryEl?.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});

queryEl?.addEventListener("input", () => {
  queryEl.style.height = "auto";
  queryEl.style.height = `${Math.min(queryEl.scrollHeight, 160)}px`;
  syncSelectedFromInput();
});

function isSelected(text) {
  return selectedSymptoms.has(text);
}

function syncInputFromSelected() {
  queryEl.value = STARTERS.filter((item) => selectedSymptoms.has(item.text))
    .map((item) => item.text)
    .join(". ");
  queryEl.style.height = "auto";
  queryEl.style.height = `${Math.min(queryEl.scrollHeight, 160)}px`;
}

function syncSelectedFromInput() {
  const value = queryEl.value.toLowerCase();
  selectedSymptoms = new Set(STARTERS.filter((item) => value.includes(item.text.toLowerCase())).map((item) => item.text));
  renderSymptomPicks();
  renderEmptyStarters();
}

function starterClass(selected) {
  return selected
    ? "rounded-2xl border-2 border-teal-700 bg-teal-700 px-3 py-2 text-left text-white shadow-sm"
    : "rounded-2xl border border-emerald-100 bg-white px-3 py-2 text-left text-slate-800 shadow-sm hover:border-teal-600";
}

function renderSymptomPicks() {
  if (!picksEl) return;
  picksEl.innerHTML = STARTERS.map((item, index) => {
    const selected = isSelected(item.text);
    return `<button type="button" data-symptom-index="${index}" class="${starterClass(selected)}">
      <span class="block text-xs font-extrabold">${escapeHtml(item.title)}</span>
    </button>`;
  }).join("");
}

function toggleSymptom(text) {
  if (selectedSymptoms.has(text)) selectedSymptoms.delete(text);
  else selectedSymptoms.add(text);
  syncInputFromSelected();
  renderSymptomPicks();
  renderEmptyStarters();
  queryEl.focus();
}

picksEl?.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-symptom-index]");
  if (!button) return;
  const item = STARTERS[Number(button.dataset.symptomIndex)];
  if (item) toggleSymptom(item.text);
});

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers || {}),
    },
  });
  if (response.status === 401) {
    clearSession();
    window.location.replace("/login");
    throw new Error("Please sign in again.");
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
    throw new Error(detail || "Request failed.");
  }
  return data;
}

function setBusy(on, label) {
  busy = on;
  sendBtn.disabled = on;
  statusEl.classList.toggle("hidden", !label);
  statusEl.textContent = label || "";
}

function renderHistory() {
  if (!chats.length) {
    historyEl.innerHTML = `<p class="px-3 py-2 text-sm text-teal-100">No chats yet.</p>`;
    return;
  }
  historyEl.innerHTML = chats
    .map((chat) => {
      const on = chat.id === activeId;
      return `<button type="button" data-id="${escapeHtml(chat.id)}" class="block w-full rounded-xl px-3 py-2.5 text-left text-sm ${on ? "bg-white text-teal-900" : "text-teal-50 hover:bg-white/10"}">
        <span class="line-clamp-2 font-semibold">${escapeHtml(chat.title || "New chat")}</span>
      </button>`;
    })
    .join("");
}

historyEl?.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-id]");
  if (!button) return;
  openChat(button.dataset.id);
  sidebar.classList.add("sidebar-closed");
});

messagesEl?.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-symptom-index]");
  if (!button) return;
  const item = STARTERS[Number(button.dataset.symptomIndex)];
  if (item) toggleSymptom(item.text);
});

function assistantCard(result) {
  if (!result) {
    return `<p class="text-sm text-slate-600">No reply stored.</p>`;
  }
  if (result.refused) {
    const recs = (result.recommendations || []).map((item) => `<li class="text-sm leading-6 text-slate-700">${escapeHtml(item)}</li>`).join("");
    return `<p class="whitespace-pre-wrap text-sm leading-6 text-slate-700">${escapeHtml(result.answer)}</p>
      ${recs ? `<div class="mt-3 rounded-2xl border border-teal-100 bg-teal-50/80 p-3"><p class="text-xs font-extrabold uppercase tracking-widest text-teal-700">Recommendations</p><ul class="mt-2 list-disc space-y-1 pl-4">${recs}</ul></div>` : ""}`;
  }
  const level = result.triage?.level || "consult_doctor";
  const ranked = (result.citations && result.citations.length ? result.citations : result.possible_conditions || []).slice(0, 4);
  const matches = ranked.length
    ? ranked
        .map((item, index) => {
          const name = escapeHtml(item.condition || item.title || "Match");
          const pct = Math.round((item.relevance_score || 0) * 100);
          return `<div class="flex items-center justify-between gap-2 rounded-xl bg-emerald-50 px-3 py-2">
            <span class="text-sm font-bold text-slate-900">${index + 1}. ${name}</span>
            <span class="text-xs font-extrabold text-teal-700">${pct}%</span>
          </div>`;
        })
        .join("")
    : "";
  const citations = (result.citations || [])
    .map((item) => {
      const title = escapeHtml(item.title || item.condition || "Source");
      const source = escapeHtml(item.source || "");
      const inner = `<span class="block text-sm font-bold text-slate-900">${title}</span><span class="text-xs text-slate-500">${source}</span>`;
      if (item.url) {
        return `<a class="block rounded-xl border border-emerald-100 px-3 py-2 no-underline hover:bg-emerald-50" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${inner}</a>`;
      }
      return `<div class="rounded-xl border border-emerald-100 px-3 py-2">${inner}</div>`;
    })
    .join("");
  const recs = (result.recommendations && result.recommendations.length
    ? result.recommendations
    : [SHORT_GUIDANCE[level] || result.triage?.guidance].filter(Boolean)
  ).slice(0, 4);
  const recHtml = recs
    .map((item) => `<li class="text-sm leading-6 text-slate-700">${escapeHtml(item)}</li>`)
    .join("");
  return `
    <p class="whitespace-pre-wrap text-sm leading-6 text-slate-700">${escapeHtml(result.answer)}</p>
    <div class="mt-3 rounded-2xl border border-teal-100 bg-teal-50/80 p-3">
      <p class="text-xs font-extrabold uppercase tracking-widest text-teal-700">Recommendations</p>
      <ul class="mt-2 list-disc space-y-1 pl-4">${recHtml}</ul>
    </div>
    ${matches ? `<div class="mt-3 space-y-2"><p class="text-xs font-extrabold uppercase tracking-widest text-slate-400">Possible matches</p>${matches}</div>` : ""}
    <div class="${TRIAGE_STYLE[level] || TRIAGE_STYLE.consult_doctor} mt-3 rounded-xl px-3 py-2 text-white">
      <p class="text-sm font-extrabold">${escapeHtml(result.triage?.label || "Urgency")}</p>
      <p class="text-xs text-white/90">${escapeHtml(SHORT_GUIDANCE[level] || result.triage?.guidance || "")}</p>
    </div>
    ${citations ? `<div class="mt-3 space-y-2"><p class="text-xs font-extrabold uppercase tracking-widest text-slate-400">Citations</p>${citations}</div>` : ""}
    <p class="mt-3 text-xs leading-5 text-slate-500">${escapeHtml(result.disclaimer || "")}</p>
  `;
}

function renderEmptyStarters() {
  const host = document.getElementById("empty-starters");
  if (!host) return;
  host.innerHTML = STARTERS.map((item, index) => {
    const selected = isSelected(item.text);
    return `<button type="button" data-symptom-index="${index}" class="p-4 ${starterClass(selected)}">
      <span class="block text-sm font-extrabold">${escapeHtml(item.title)}</span>
      <span class="mt-1 block text-xs leading-5 ${selected ? "text-teal-100" : "text-slate-500"}">${escapeHtml(item.text)}</span>
    </button>`;
  }).join("");
}

function renderMessages(messages) {
  currentMessages = messages || [];
  if (!currentMessages.length) {
    messagesEl.innerHTML = `
      <div class="mx-auto mt-10 max-w-2xl text-center">
        <h1 class="text-2xl font-extrabold text-slate-900">How can we help?</h1>
        <p class="mt-2 text-sm text-slate-500">Select one or more symptoms. They will appear in the box below, then press Send.</p>
        <div id="empty-starters" class="mt-6 grid gap-3 sm:grid-cols-2"></div>
      </div>`;
    renderEmptyStarters();
    return;
  }
  messagesEl.innerHTML = currentMessages
    .map((item) => {
      if (item.role === "user") {
        return `<div class="ml-auto max-w-2xl rounded-3xl rounded-br-md bg-teal-700 px-4 py-3 text-sm leading-6 text-white">${escapeHtml(item.content)}</div>`;
      }
      if (!item.result) {
        return `<div class="mr-auto max-w-2xl rounded-3xl rounded-bl-md bg-white p-4 text-sm font-semibold text-slate-500 shadow-sm">Checking safety and matching documents…</div>`;
      }
      return `<div class="mr-auto max-w-2xl rounded-3xl rounded-bl-md bg-white p-4 shadow-sm">${assistantCard(item.result)}</div>`;
    })
    .join("");
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function loadChats() {
  chats = await api("/api/chats");
  if (!chats.length) {
    await createChat();
    return;
  }
  const exists = chats.some((chat) => chat.id === activeId);
  await openChat(exists ? activeId : chats[0].id);
}

async function createChat() {
  const chat = await api("/api/chats", { method: "POST" });
  activeId = chat.id;
  sessionStorage.setItem(ACTIVE_KEY, activeId);
  chats = await api("/api/chats");
  renderHistory();
  renderMessages([]);
  queryEl?.focus();
}

async function openChat(id) {
  activeId = id;
  sessionStorage.setItem(ACTIVE_KEY, activeId);
  renderHistory();
  const chat = await api(`/api/chats/${id}`);
  renderMessages(chat.messages || []);
}

async function sendMessage() {
  const query = queryEl.value.trim();
  if (!query || busy) return;
  if (!activeId) await createChat();
  const prior = (currentMessages || []).filter((item) => item.role !== "assistant" || item.result);
  queryEl.value = "";
  queryEl.style.height = "auto";
  selectedSymptoms = new Set();
  renderSymptomPicks();
  renderMessages([
    ...prior,
    { role: "user", content: query },
    { role: "assistant", content: "", result: null },
  ]);
  setBusy(true, "Checking safety and matching documents…");
  try {
    const chat = await api(`/api/chats/${activeId}/messages`, {
      method: "POST",
      body: JSON.stringify({ query, top_k: 4 }),
    });
    chats = await api("/api/chats");
    renderHistory();
    renderMessages(chat.messages || []);
    setBusy(false, "");
  } catch (err) {
    renderMessages(prior);
    queryEl.value = query;
    syncSelectedFromInput();
    messagesEl.insertAdjacentHTML(
      "beforeend",
      `<div class="mx-auto max-w-2xl rounded-2xl bg-white p-4 text-sm text-rose-600">${escapeHtml(err.message)}</div>`
    );
    setBusy(false, "");
  }
}

renderSymptomPicks();
loadChats().catch((err) => {
  messagesEl.innerHTML = `<p class="p-6 text-sm text-rose-600">${escapeHtml(err.message)}</p>`;
});
