const STORAGE_KEY = "job-scanner-web-settings-v1";
const API_BASE_KEY = "job-scanner-web-api-base";
const DEFAULT_API_BASE = window.location.origin;

const THEMES = [
  "Neon Pulse",
  "Cyber Sunset",
  "Matrix Mint",
  "Electric Violet",
  "Arctic Glow",
  "High Contrast",
];

const STATES = ["", "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"];
const RESULT_COLUMNS = ["title", "company", "location", "site", "pay", "posted", "term"];
const COLUMN_LABELS = {
  title: "Title",
  company: "Company",
  location: "Location",
  site: "Site",
  pay: "Pay",
  posted: "Posted",
  term: "Matched",
};
const JOB_BOARDS = [
  "LinkedIn",
  "Indeed",
  "ZipRecruiter",
  "Dice",
  "USAJOBS",
  "BrassRing",
  "Disney Jobs",
  "Paramount Jobs",
  "Warner Bros Jobs",
  "Universal Jobs",
  "Sony Pictures Jobs",
  "Netflix Jobs",
  "Glassdoor",
];

const state = {
  tab: "all",
  theme: "Neon Pulse",
  density: "Comfortable",
  textScale: 16,
  visibleColumns: [...RESULT_COLUMNS],
  selectedBoards: JOB_BOARDS.filter((board) => board !== "Glassdoor"),
  rows: [],
  newRows: [],
  selectedId: "",
  settings: {},
  statusMessage: "Ready",
  locationMessage: "Location: not searched yet",
  scanInFlight: false,
  autoScanHandle: null,
  hasScannedOnce: false,
};

const els = {};

document.addEventListener("DOMContentLoaded", () => {
  cacheDom();
  populateStaticControls();
  hydrateApiBaseFromQuery();
  loadSettings();
  bindEvents();
  syncAutoScan();
  render();
});

function cacheDom() {
  els.body = document.body;
  els.themeSelect = document.getElementById("themeSelect");
  els.densitySelect = document.getElementById("densitySelect");
  els.textDown = document.getElementById("textDown");
  els.textUp = document.getElementById("textUp");
  els.state = document.getElementById("state");
  els.jobBoards = document.getElementById("jobBoards");
  els.columnToggles = document.getElementById("columnToggles");
  els.resultsHead = document.getElementById("resultsHead");
  els.resultsBody = document.getElementById("resultsBody");
  els.detailPane = document.getElementById("detailPane");
  els.statusText = document.getElementById("statusText");
  els.locationText = document.getElementById("locationText");
  els.resultsText = document.getElementById("resultsText");
  els.tabs = [...document.querySelectorAll(".tab")];
  els.startupSound = document.getElementById("startupSound");
  els.resultsPanel = document.querySelector(".results-panel");
}

function populateStaticControls() {
  THEMES.forEach((theme) => {
    const option = document.createElement("option");
    option.value = theme;
    option.textContent = theme;
    els.themeSelect.appendChild(option);
  });

  STATES.forEach((abbr) => {
    const option = document.createElement("option");
    option.value = abbr;
    option.textContent = abbr || "State";
    els.state.appendChild(option);
  });

  JOB_BOARDS.forEach((board) => {
    const label = document.createElement("label");
    label.className = "chip";
    label.innerHTML = `<input type="checkbox" value="${board}"><span>${board}</span>`;
    els.jobBoards.appendChild(label);
  });

  RESULT_COLUMNS.forEach((column) => {
    const label = document.createElement("label");
    label.className = "chip";
    label.innerHTML = `<input type="checkbox" value="${column}"><span>${COLUMN_LABELS[column]}</span>`;
    els.columnToggles.appendChild(label);
  });
}

function loadSettings() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    state.settings = stored;
    state.theme = stored.theme || state.theme;
    state.density = stored.density || state.density;
    state.textScale = stored.textScale || state.textScale;
    state.visibleColumns = stored.visibleColumns || state.visibleColumns;
    state.selectedBoards = stored.selectedBoards || state.selectedBoards;

    setInputValue("zipCode", stored.zipCode || "");
    setInputValue("city", stored.city || "");
    setInputValue("state", stored.state || "");
    setInputValue("distance", stored.distance || "");
    setInputValue("hoursOld", stored.hoursOld || "");
    setInputValue("resultsPerTerm", stored.resultsPerTerm || "");
    setInputValue("payMin", stored.payMin || "");
    setInputValue("payMax", stored.payMax || "");
    setInputValue("searchTitles", stored.searchTitles || "");
    setInputValue("customUrl", stored.customUrl || "");
    setCheckboxValue("remoteOnly", Boolean(stored.remoteOnly));
    setCheckboxValue("autoScan", Boolean(stored.autoScan));
    setInputValue("autoScanMinutes", stored.autoScanMinutes || "15");
    setCheckboxValue("desktopAlert", stored.desktopAlert ?? true);
    setCheckboxValue("flashAlert", stored.flashAlert ?? true);
    setCheckboxValue("soundAlert", stored.soundAlert ?? false);
    if (stored.apiBase) {
      localStorage.setItem(API_BASE_KEY, stored.apiBase);
    }
  } catch {
    // Ignore malformed settings.
  }
}

function bindEvents() {
  els.themeSelect.addEventListener("change", () => {
    state.theme = els.themeSelect.value;
    saveSettings();
    render();
  });

  els.densitySelect.addEventListener("change", () => {
    state.density = els.densitySelect.value;
    saveSettings();
    render();
  });

  els.textDown.addEventListener("click", () => {
    state.textScale = Math.max(13, state.textScale - 1);
    saveSettings();
    render();
  });

  els.textUp.addEventListener("click", () => {
    state.textScale = Math.min(22, state.textScale + 1);
    saveSettings();
    render();
  });

  els.tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      state.tab = tab.dataset.tab;
      render();
    });
  });

  document.getElementById("scanButton").addEventListener("click", () => runScan(false));
  document.getElementById("exportButton").addEventListener("click", exportCsv);
  document.getElementById("testSound").addEventListener("click", playSound);
  document.getElementById("autoScan").addEventListener("change", () => {
    saveSettings();
    syncAutoScan();
  });
  document.getElementById("autoScanMinutes").addEventListener("change", () => {
    saveSettings();
    syncAutoScan();
  });

  document.querySelectorAll("input, textarea, select").forEach((input) => {
    input.addEventListener("change", saveSettings);
    input.addEventListener("input", saveSettings);
  });

  els.jobBoards.querySelectorAll("input").forEach((input) => {
    input.addEventListener("change", () => {
      state.selectedBoards = [...els.jobBoards.querySelectorAll("input:checked")].map((box) => box.value);
      saveSettings();
    });
  });

  els.columnToggles.querySelectorAll("input").forEach((input) => {
    input.addEventListener("change", () => {
      state.visibleColumns = [...els.columnToggles.querySelectorAll("input:checked")].map((box) => box.value);
      if (!state.visibleColumns.length) {
        state.visibleColumns = ["title"];
        els.columnToggles.querySelector('input[value="title"]').checked = true;
      }
      saveSettings();
      render();
    });
  });
}

function render() {
  els.body.dataset.theme = state.theme;
  els.body.dataset.density = state.density;
  els.body.style.setProperty("--font-size", `${state.textScale}px`);
  els.themeSelect.value = state.theme;
  els.densitySelect.value = state.density;

  syncCheckboxGroup(els.jobBoards, state.selectedBoards);
  syncCheckboxGroup(els.columnToggles, state.visibleColumns);

  renderResults();
  renderDetails();
  renderStatus();
}

function renderResults() {
  const rows = state.tab === "new" ? state.newRows : state.rows;
  els.tabs.forEach((tab) => {
    const isActive = tab.dataset.tab === state.tab;
    tab.classList.toggle("active", isActive);
    if (tab.dataset.tab === "new") {
      tab.textContent = `New Jobs${state.newRows.length ? ` (${state.newRows.length})` : ""}`;
    }
  });

  els.resultsHead.innerHTML = "";
  state.visibleColumns.forEach((column) => {
    const th = document.createElement("th");
    th.textContent = COLUMN_LABELS[column];
    els.resultsHead.appendChild(th);
  });

  els.resultsBody.innerHTML = "";
  if (!rows.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = Math.max(state.visibleColumns.length, 1);
    td.textContent = state.scanInFlight ? "Scanning..." : "No results yet.";
    tr.appendChild(td);
    els.resultsBody.appendChild(tr);
    return;
  }

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    if (row.id === state.selectedId) tr.classList.add("selected");
    tr.addEventListener("click", () => {
      state.selectedId = row.id;
      render();
    });

    state.visibleColumns.forEach((column) => {
      const td = document.createElement("td");
      td.textContent = row[column] || "Unknown";
      tr.appendChild(td);
    });

    els.resultsBody.appendChild(tr);
  });
}

function renderDetails() {
  const activeRows = state.tab === "new" ? state.newRows : state.rows;
  const selected = activeRows.find((row) => row.id === state.selectedId) || state.rows.find((row) => row.id === state.selectedId);
  if (!selected) {
    els.detailPane.textContent = "Select a job to inspect the description, salary info, and links.";
    return;
  }

  const urlMarkup = selected.job_url
    ? `<a href="${escapeAttribute(selected.job_url)}" target="_blank" rel="noopener">${escapeHtml(selected.job_url)}</a>`
    : "Not provided";
  const companyUrlMarkup = selected.company_url
    ? `<a href="${escapeAttribute(selected.company_url)}" target="_blank" rel="noopener">${escapeHtml(selected.company_url)}</a>`
    : "Not provided";

  els.detailPane.innerHTML =
    `<strong>Title:</strong> ${escapeHtml(selected.title)}<br>` +
    `<strong>Company:</strong> ${escapeHtml(selected.company)}<br>` +
    `<strong>Location:</strong> ${escapeHtml(selected.location)}<br>` +
    `<strong>Site:</strong> ${escapeHtml(selected.site)}<br>` +
    `<strong>Matched search:</strong> ${escapeHtml(selected.term || "Unknown")}<br>` +
    `<strong>Posted:</strong> ${escapeHtml(selected.posted || "Unknown")}<br>` +
    `<strong>Remote:</strong> ${escapeHtml(selected.remote || "Unknown")}<br>` +
    `<strong>Job type:</strong> ${escapeHtml(selected.job_type || "Unknown")}<br>` +
    `<strong>Salary:</strong> ${escapeHtml(selected.pay || "Not listed")}<br>` +
    `<strong>Listing URL:</strong> ${urlMarkup}<br>` +
    `<strong>Company URL:</strong> ${companyUrlMarkup}<br><br>` +
    `<strong>Description:</strong><br>${formatMultiline(selected.description || "No description available.")}`;
}

function renderStatus() {
  els.statusText.textContent = state.statusMessage;
  els.locationText.textContent = state.locationMessage;
  els.resultsText.textContent = `Results: ${(state.tab === "new" ? state.newRows : state.rows).length}`;
}

async function runScan(isAutoScan) {
  if (state.scanInFlight) return;

  const payload = buildPayload();
  if (!payload.searchTitles.trim()) {
    state.statusMessage = "Enter one or more search titles before scanning.";
    renderStatus();
    return;
  }

  if (!payload.zipCode && !(payload.city && payload.state)) {
    state.statusMessage = "Enter either a ZIP code or a city and state.";
    renderStatus();
    return;
  }

  state.scanInFlight = true;
  state.statusMessage = isAutoScan ? "Auto-scan running..." : "Scanning live job sources...";
  render();

  try {
    const response = await fetch(`${getApiBase()}/api/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const body = await response.json().catch(() => ({}));
    if (!response.ok || !body.ok) {
      throw new Error(body.error || `Scan failed with status ${response.status}`);
    }

    const previousIds = new Set(state.rows.map((row) => row.id));
    const incomingRows = Array.isArray(body.results) ? body.results : [];
    state.newRows = state.hasScannedOnce ? incomingRows.filter((row) => !previousIds.has(row.id)) : [...incomingRows];
    state.rows = incomingRows;
    state.hasScannedOnce = true;
    state.locationMessage = body.location?.display_name ? `Location: ${body.location.display_name}` : makeLocationText();
    state.statusMessage = `Search complete${isAutoScan ? " (auto)" : ""}`;

    const activeRows = state.tab === "new" ? state.newRows : state.rows;
    if (!activeRows.some((row) => row.id === state.selectedId)) {
      state.selectedId = (state.newRows[0] || state.rows[0] || {}).id || "";
    }

    if (state.newRows.length) {
      await handleNewJobAlerts(state.newRows, previousIds.size > 0);
    }
  } catch (error) {
    if (error instanceof TypeError) {
      state.statusMessage = "Could not reach the live API. Run python web_app.py locally or open this page with ?api=https://your-backend-host.";
    } else {
      state.statusMessage = error instanceof Error ? error.message : "Scan failed.";
    }
  } finally {
    state.scanInFlight = false;
    render();
  }
}

async function handleNewJobAlerts(newRows, shouldNotify) {
  if (!shouldNotify) return;

  if (document.getElementById("flashAlert").checked) {
    els.resultsPanel.classList.remove("flash");
    void els.resultsPanel.offsetWidth;
    els.resultsPanel.classList.add("flash");
  }

  if (document.getElementById("soundAlert").checked) {
    playSound();
  }

  if (document.getElementById("desktopAlert").checked && "Notification" in window) {
    if (Notification.permission === "default") {
      try {
        await Notification.requestPermission();
      } catch {
        // Ignore browser refusal.
      }
    }
    if (Notification.permission === "granted") {
      const sampleTitles = newRows.slice(0, 3).map((row) => row.title).join(", ");
      const body = `${newRows.length} new job${newRows.length === 1 ? "" : "s"} found${sampleTitles ? `: ${sampleTitles}` : ""}`;
      new Notification("Job Scanner", { body });
    }
  }
}

function syncAutoScan() {
  if (state.autoScanHandle) {
    clearInterval(state.autoScanHandle);
    state.autoScanHandle = null;
  }

  if (!document.getElementById("autoScan").checked) return;

  const minutes = Number(document.getElementById("autoScanMinutes").value || 0);
  if (!Number.isFinite(minutes) || minutes <= 0) return;

  state.autoScanHandle = window.setInterval(() => {
    runScan(true);
  }, minutes * 60 * 1000);
}

function buildPayload() {
  return {
    zipCode: document.getElementById("zipCode").value.trim(),
    city: document.getElementById("city").value.trim(),
    state: document.getElementById("state").value.trim(),
    distance: document.getElementById("distance").value.trim(),
    hoursOld: document.getElementById("hoursOld").value.trim(),
    resultsPerTerm: document.getElementById("resultsPerTerm").value.trim(),
    payMin: document.getElementById("payMin").value.trim(),
    payMax: document.getElementById("payMax").value.trim(),
    searchTitles: document.getElementById("searchTitles").value,
    customUrl: document.getElementById("customUrl").value.trim(),
    remoteOnly: document.getElementById("remoteOnly").checked,
    selectedBoards: state.selectedBoards,
  };
}

function playSound() {
  els.startupSound.currentTime = 0;
  els.startupSound.play().catch(() => {
    // Browser may block autoplay until user interaction.
  });
}

function exportCsv() {
  const rows = state.tab === "new" ? state.newRows : state.rows;
  const header = state.visibleColumns.map((column) => COLUMN_LABELS[column]).join(",");
  const lines = rows.map((row) =>
    state.visibleColumns.map((column) => csvEscape(row[column] || "Unknown")).join(",")
  );
  const blob = new Blob([[header, ...lines].join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "job_scanner_web_results.csv";
  link.click();
  URL.revokeObjectURL(url);
}

function csvEscape(value) {
  const text = String(value).replace(/"/g, '""');
  return `"${text}"`;
}

function saveSettings() {
  const payload = {
    theme: state.theme,
    density: state.density,
    textScale: state.textScale,
    visibleColumns: state.visibleColumns,
    selectedBoards: state.selectedBoards,
    zipCode: document.getElementById("zipCode").value,
    city: document.getElementById("city").value,
    state: document.getElementById("state").value,
    distance: document.getElementById("distance").value,
    hoursOld: document.getElementById("hoursOld").value,
    resultsPerTerm: document.getElementById("resultsPerTerm").value,
    payMin: document.getElementById("payMin").value,
    payMax: document.getElementById("payMax").value,
    searchTitles: document.getElementById("searchTitles").value,
    customUrl: document.getElementById("customUrl").value,
    remoteOnly: document.getElementById("remoteOnly").checked,
    autoScan: document.getElementById("autoScan").checked,
    autoScanMinutes: document.getElementById("autoScanMinutes").value,
    desktopAlert: document.getElementById("desktopAlert").checked,
    flashAlert: document.getElementById("flashAlert").checked,
    soundAlert: document.getElementById("soundAlert").checked,
    apiBase: getApiBase(),
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

function getApiBase() {
  return localStorage.getItem(API_BASE_KEY)?.trim() || DEFAULT_API_BASE;
}

function hydrateApiBaseFromQuery() {
  const apiBase = new URLSearchParams(window.location.search).get("api");
  if (!apiBase) return;
  localStorage.setItem(API_BASE_KEY, apiBase.trim().replace(/\/+$/, ""));
}

function makeLocationText() {
  const zip = document.getElementById("zipCode").value.trim();
  const city = document.getElementById("city").value.trim();
  const stateCode = document.getElementById("state").value.trim();
  if (zip) return `Location: ZIP ${zip}`;
  if (city && stateCode) return `Location: ${city}, ${stateCode}`;
  return "Location: not searched yet";
}

function syncCheckboxGroup(container, selectedValues) {
  container.querySelectorAll("input").forEach((input) => {
    input.checked = selectedValues.includes(input.value);
  });
}

function setInputValue(id, value) {
  const node = document.getElementById(id);
  if (node) node.value = value;
}

function setCheckboxValue(id, value) {
  const node = document.getElementById(id);
  if (node) node.checked = value;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}

function formatMultiline(value) {
  return escapeHtml(value).replace(/\n/g, "<br>");
}
