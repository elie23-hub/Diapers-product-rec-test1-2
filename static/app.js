const statusLine = document.getElementById("statusLine");
const summaryCards = document.getElementById("summaryCards");
const cityCards = document.getElementById("cityCards");
const cells = document.getElementById("cells");
const reasons = document.getElementById("reasons");
const rosterBody = document.getElementById("rosterBody");
const rosterEmpty = document.getElementById("rosterEmpty");
const errorBox = document.getElementById("errorBox");
const refreshBtn = document.getElementById("refreshBtn");
const exportBtn = document.getElementById("exportBtn");
const searchBox = document.getElementById("searchBox");
const filterRow = document.getElementById("filterRow");

let latest = null;
let filter = "all";

function fmtTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function setBusy(busy) {
  refreshBtn.disabled = busy;
  exportBtn.disabled = busy || !latest;
  refreshBtn.textContent = busy ? "Refreshing…" : "Refresh from Kobo";
}

function card(label, value, note) {
  return `
    <article class="card">
      <p class="label">${esc(label)}</p>
      <p class="value">${esc(value)}</p>
      ${note ? `<p class="note">${esc(note)}</p>` : ""}
    </article>`;
}

function chip(label, value, tone = "") {
  const shown = value == null || value === "" ? "—" : value;
  return `
    <div class="chip ${tone}">
      <p class="k">${esc(label)}</p>
      <p class="v">${esc(shown)}</p>
    </div>`;
}

function renderSummary(data) {
  summaryCards.innerHTML = [
    card("Recruitment submissions", data.recruitment_rows, `${data.recruitment_ids} unique IDs`),
    card("Passed recruitment", data.passed, `${data.screened_out} screened out`),
    card("Product 1 done", data.product_1_done, `${data.waiting_t1} passed recruits still to do`),
    card("Product 2 done", data.product_2_done, `${data.waiting_t2} passed recruits still to do`),
  ].join("");

  cityCards.innerHTML = [
    card("Both products · Jeddah", data.both_jeddah, `${data.passed_jeddah} passed in Jeddah`),
    card("Both products · Riyadh", data.both_riyadh, `${data.passed_riyadh} passed in Riyadh`),
    card("Both products · Total", data.both, `${data.passed_saudi} Saudi · ${data.passed_expat} Expat Arab`),
  ].join("");
}

function renderProduct(title, tone, form, waiting) {
  const avg = form.avg_performance == null ? "—" : form.avg_performance;
  return `
    <article class="cell">
      <div class="cell-banner ${tone}">
        <div class="cell-title"><h3>${esc(title)}</h3></div>
        <div class="rows-pill">
          <span class="n">${esc(form.rows)}</span>
          <span class="t">Rows</span>
        </div>
      </div>
      <div class="metrics">
        <div class="metric">
          <p class="k">Matched to passed</p>
          <p class="v">${esc(form.matched_passed)}</p>
          <p class="p">${esc(form.unmatched)} IDs not placed</p>
        </div>
        <div class="metric">
          <p class="k">Used all period</p>
          <p class="v">${esc(form.used_all)}</p>
          <p class="p">T4 = used the test product</p>
        </div>
        <div class="metric">
          <p class="k">Leaks</p>
          <p class="v">${esc(form.leakage)}</p>
          <p class="p">Q7a = yes</p>
        </div>
        <div class="metric">
          <p class="k">Allergies</p>
          <p class="v">${esc(form.allergy)}</p>
          <p class="p">Q7c = yes</p>
        </div>
      </div>
      <div class="days">
        <article class="day-card">
          <div class="day-grid">
            ${chip("Used another product", form.used_other, form.used_other ? "warn" : "")}
            ${chip("Satisfied", form.satisfied)}
            ${chip("Would buy", form.would_buy)}
            ${chip("Avg performance", avg)}
          </div>
        </article>
      </div>
      <div class="complete-row">
        <div>
          <p class="label">Passed recruits still to do this test</p>
          <p class="sub">Same respondent ID is not on this link yet</p>
        </div>
        <div class="value">${esc(waiting)}</div>
      </div>
    </article>`;
}

function renderReasons(data) {
  const items = data.screen_reasons || [];
  const max = Math.max(1, ...items.map((item) => item.count));
  if (!items.length) {
    reasons.innerHTML = `<p class="empty">No screened-out respondents.</p>`;
    return;
  }
  reasons.innerHTML = items.map((item) => `
    <div class="reason">
      <div class="reason-top">
        <span>${esc(item.label)}</span>
        <strong>${esc(item.count)}</strong>
      </div>
      <div class="bar"><span style="width:${Math.round(100 * item.count / max)}%"></span></div>
    </div>
  `).join("");
}

function matches(person) {
  if (filter === "waiting" && !(person.passed && !person.both)) return false;
  if (filter === "both" && !(person.passed && person.both)) return false;
  if (filter === "screened" && person.stage !== "screened") return false;
  if (filter === "product_only" && person.stage !== "product_only") return false;
  const q = searchBox.value.trim().toLowerCase();
  if (!q) return true;
  return [person.id, person.name, person.phone, person.interviewer, person.city]
    .join(" ")
    .toLowerCase()
    .includes(q);
}

function productCell(status, usage) {
  if (status !== "Submitted") return `<span class="wait">Not yet</span>`;
  return `<span class="ok">${esc(usage || "Submitted")}</span>`;
}

function renderRoster() {
  const people = (latest?.roster || []).filter(matches);
  rosterBody.innerHTML = people.map((person) => `
    <tr>
      <td>${esc(person.id)}</td>
      <td>
        <div class="who">${esc(person.name || "—")}</div>
        <div class="meta">${esc(person.phone)}${person.interviewer ? ` · ${esc(person.interviewer)}` : ""}</div>
      </td>
      <td>${esc(person.city || "—")}</td>
      <td>${esc(person.nationality || "—")}<div class="meta">${esc(person.age_bracket)}</div></td>
      <td>${person.passed ? `<span class="ok">${esc(person.recruitment)}</span>` : esc(person.recruitment)}</td>
      <td>${productCell(person.product_1, person.product_1_usage)}</td>
      <td>${productCell(person.product_2, person.product_2_usage)}</td>
    </tr>
  `).join("");
  rosterEmpty.hidden = people.length > 0;
}

function render(data) {
  latest = data;
  const extra = [];
  if (data.duplicate_ids) extra.push(`${data.duplicate_ids} duplicate recruitment IDs`);
  if (data.missing_recruitment_id) extra.push(`${data.missing_recruitment_id} recruitment rows without an ID`);
  statusLine.textContent = [
    data.source,
    `${data.recruitment_rows} recruitment rows`,
    `Updated ${fmtTime(data.generated_at)}`,
    ...extra,
  ].join(" · ");
  renderSummary(data);
  cells.innerHTML =
    renderProduct("Product 1", "t1", data.product_1, data.waiting_t1) +
    renderProduct("Product 2", "t2", data.product_2, data.waiting_t2);
  renderReasons(data);
  renderRoster();
  errorBox.hidden = true;
  exportBtn.disabled = false;
}

function showError(message) {
  errorBox.hidden = false;
  errorBox.textContent = message;
}

async function refresh() {
  setBusy(true);
  try {
    const res = await fetch("/api/stats", { cache: "no-store" });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      throw new Error(data.detail || data.error || `Request failed (${res.status})`);
    }
    render(data);
  } catch (err) {
    showError(err.message || String(err));
    statusLine.textContent = "Could not refresh from Kobo.";
  } finally {
    setBusy(false);
  }
}

function csvCell(value) {
  const text = String(value ?? "");
  if (/[",\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

function exportCsv() {
  if (!latest) return;
  const header = [
    "respondent_id", "name", "phone", "interviewer", "city", "nationality", "age_bracket",
    "recruitment", "product_1", "product_1_usage", "product_2", "product_2_usage", "both_products",
  ];
  const lines = [header.join(",")];
  for (const person of latest.roster) {
    lines.push([
      person.id, person.name, person.phone, person.interviewer, person.city, person.nationality,
      person.age_bracket, person.recruitment, person.product_1, person.product_1_usage,
      person.product_2, person.product_2_usage, person.both ? "yes" : "no",
    ].map(csvCell).join(","));
  }
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "diapers_2026_progress.csv";
  a.click();
  URL.revokeObjectURL(url);
}

refreshBtn.addEventListener("click", refresh);
exportBtn.addEventListener("click", exportCsv);
searchBox.addEventListener("input", () => latest && renderRoster());
filterRow.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-filter]");
  if (!button) return;
  filter = button.dataset.filter;
  for (const item of filterRow.querySelectorAll("button")) {
    item.classList.toggle("on", item === button);
  }
  if (latest) renderRoster();
});

refresh();
setInterval(refresh, 60000);
