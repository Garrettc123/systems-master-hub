const $ = (id) => document.getElementById(id);
const apiStatus = $("apiStatus");
const apiDetail = $("apiDetail");
const overall = $("overall");
const lastChecked = $("lastChecked");
const refresh = $("refresh");
const searchForm = $("searchForm");
const searchResult = $("searchResult");
const queryInput = $("query");

function setOverall(label, type = "unknown") {
  overall.textContent = label;
  overall.className = "status-pill " + (type === "safe" ? "status-safe" : type === "bad" ? "status-bad" : "status-unknown");
}
async function checkHealth() {
  refresh.disabled = true;
  apiStatus.textContent = "Checking…";
  apiDetail.textContent = "Requesting same-origin /healthz.";
  try {
    const response = await fetch("./healthz", { method: "GET", headers: { "Accept": "application/json" }, cache: "no-store", credentials: "same-origin" });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    apiStatus.textContent = "Responding";
    apiDetail.textContent = "Health endpoint returned HTTP " + response.status + (data.status ? " · " + String(data.status) : "") + ".";
    setOverall("API responding", "safe");
  } catch (error) {
    apiStatus.textContent = "Unavailable";
    apiDetail.textContent = "Health check failed: " + (error && error.message ? error.message : "request failed") + ". UI and API may be deployed separately.";
    setOverall("Connection unverified");
  } finally {
    lastChecked.textContent = "Checked " + new Date().toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"});
    refresh.disabled = false;
  }
}
searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const q = queryInput.value.trim();
  if (!q) return;
  searchResult.textContent = "Checking for the authenticated knowledge-search endpoint…";
  try {
    const response = await fetch("./api/knowledge/search", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({ query: q })
    });
    if (response.status === 404 || response.status === 405) {
      searchResult.textContent = "Knowledge search is not connected: this deployment does not expose the required endpoint. No query was sent to Slack or Perplexity.";
      return;
    }
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    searchResult.textContent = typeof data.answer === "string" ? data.answer : JSON.stringify(data, null, 2);
  } catch (error) {
    searchResult.textContent = "Search unavailable. Connect an authenticated server-side knowledge adapter before using this feature. Details: " + (error.message || "request failed");
  }
});
refresh.addEventListener("click", checkHealth);
if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
  window.addEventListener("load", () => navigator.serviceWorker.register("./sw.js").catch(() => {}));
}
checkHealth();