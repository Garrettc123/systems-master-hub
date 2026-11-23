const $ = (id) => document.getElementById(id);
const apiStatus = $("apiStatus");
const apiDetail = $("apiDetail");
const overall = $("overall");
const lastChecked = $("lastChecked");
const refresh = $("refresh");
const searchForm = $("searchForm");
const searchResult = $("searchResult");
const queryInput = $("query");
const providerRows = Array.from(document.querySelectorAll(".integrations .integration-row"));
const statusCards = Array.from(document.querySelectorAll(".status-grid article"));

function setOverall(label, type = "unknown") {
  overall.textContent = label;
  overall.className = "status-pill " + (type === "safe" ? "status-safe" : type === "bad" ? "status-bad" : "status-unknown");
}
function statusLabel(state) {
  if (state === "connected") return ["Connected", "status-safe"];
  if (state === "configured") return ["Configured; not yet tested", "status-unknown"];
  if (state === "needs_credentials" || state === "not_configured") return ["Needs server credentials", "status-unknown"];
  return ["Unverified", "status-unknown"];
}
function setRowState(row, state) {
  if (!row) return;
  const pill = row.querySelector(".status-pill");
  if (!pill) return;
  const [label, klass] = statusLabel(state);
  pill.textContent = label;
  pill.className = "status-pill " + klass;
}
async function loadProviderStatus() {
  try {
    const response = await fetch("./api/phone/status", {
      method: "GET", headers: { "Accept": "application/json" },
      cache: "no-store", credentials: "same-origin"
    });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    const providers = data.providers || {};
    const names = ["slack", "perplexity", "notion"];
    const rows = { slack: providerRows[1], perplexity: providerRows[2], notion: providerRows[3] };
    names.forEach((name) => {
      const provider = providers[name] || {};
      setRowState(rows[name], provider.state || "unverified");
    });
    const configured = Number(data.configured_count || 0);
    const total = Number(data.provider_count || 3);
    if (statusCards[1]) statusCards[1].querySelector(".value").textContent = providers.slack?.configured ? "Configured" : "Not configured";
    if (statusCards[2]) statusCards[2].querySelector(".value").textContent = providers.perplexity?.configured ? "Configured" : "Not configured";
    if (configured === total) setOverall("Providers configured", "safe");
    else if (configured > 0) setOverall("Partially configured");
    else setOverall("Provider credentials missing");
  } catch (error) {
    setOverall("Integration status unavailable");
  }
}
async function checkHealth() {
  refresh.disabled = true;
  apiStatus.textContent = "Checking…";
  apiDetail.textContent = "Requesting same-origin /healthz.";
  try {
    const response = await fetch("./healthz", {
      method: "GET", headers: { "Accept": "application/json" },
      cache: "no-store", credentials: "same-origin"
    });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    apiStatus.textContent = "Responding";
    apiDetail.textContent = "Health endpoint returned HTTP " + response.status + (data.status ? " · " + String(data.status) : "") + ".";
  } catch (error) {
    apiStatus.textContent = "Unavailable";
    apiDetail.textContent = "Health check failed: " + (error?.message || "request failed") + ". The UI and API may be deployed separately.";
  } finally {
    lastChecked.textContent = "Checked " + new Date().toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"});
    refresh.disabled = false;
    await loadProviderStatus();
  }
}
function renderResults(data) {
  searchResult.replaceChildren();
  const providers = data.providers || [];
  const summary = document.createElement("p");
  summary.textContent = "Read-only search · " + (data.results || []).length + " result(s) · " +
    providers.map((p) => p.provider + ": " + p.state).join(" · ");
  searchResult.appendChild(summary);
  const results = data.results || [];
  if (!results.length) {
    const empty = document.createElement("p");
    empty.textContent = "No results returned. Check provider credentials, permissions, or the search terms.";
    searchResult.appendChild(empty);
    return;
  }
  results.forEach((item) => {
    const article = document.createElement("article");
    article.className = "search-hit";
    const heading = document.createElement("strong");
    heading.textContent = item.title || "Search result";
    article.appendChild(heading);
    if (item.text) {
      const body = document.createElement("p");
      body.textContent = item.text;
      article.appendChild(body);
    }
    if (typeof item.url === "string" && /^https:\/\//i.test(item.url)) {
      const link = document.createElement("a");
      link.href = item.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = "Open source";
      article.appendChild(link);
    }
    searchResult.appendChild(article);
  });
}
searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const q = queryInput.value.trim();
  if (q.length < 2) return;
  searchResult.textContent = "Searching configured providers in read-only mode…";
  try {
    const response = await fetch("./api/knowledge/search", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({ query: q })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      searchResult.textContent = data.detail || ("Search unavailable (HTTP " + response.status + ").");
      return;
    }
    renderResults(data);
    await loadProviderStatus();
  } catch (error) {
    searchResult.textContent = "Search unavailable. Verify the protected deployment and server-side provider configuration. " + (error?.message || "");
  }
});
refresh.addEventListener("click", checkHealth);
if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
  window.addEventListener("load", () => navigator.serviceWorker.register("./sw.js").catch(() => {}));
}
checkHealth();