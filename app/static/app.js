const $ = (id) => document.getElementById(id);

const clubQuery = $("clubQuery");
const leagueQuery = $("leagueQuery");
const clubField = $("clubField");
const leagueField = $("leagueField");
const clubHint = $("clubHint");
const leagueHint = $("leagueHint");
const nation = $("nation");
const nationRequired = $("nationRequired");
const startBtn = $("startBtn");
const refreshCatalog = $("refreshCatalog");
const statusPanel = $("statusPanel");
const statusTitle = $("statusTitle");
const statusBadge = $("statusBadge");
const statusMsg = $("statusMsg");
const progressBar = $("progressBar");
const progressText = $("progressText");
const fileList = $("fileList");
const logBox = $("logBox");

let pollTimer = null;

function mode() {
  return document.querySelector('input[name="mode"]:checked').value;
}

function updateModeUI() {
  const m = mode();
  const isLeague = m === "league";
  clubField.hidden = isLeague;
  leagueField.hidden = !isLeague;
  nationRequired.textContent = isLeague
    ? "(recomendado — evita misturar países)"
    : "(opcional)";
}

document.querySelectorAll('input[name="mode"]').forEach((el) => {
  el.addEventListener("change", updateModeUI);
});

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fillSelect(el, items, emptyLabel) {
  const current = el.value;
  const opts = [`<option value="">${escapeHtml(emptyLabel)}</option>`];
  for (const v of items) {
    opts.push(`<option value="${escapeHtml(v)}">${escapeHtml(v)}</option>`);
  }
  el.innerHTML = opts.join("");
  if (current && items.includes(current)) {
    el.value = current;
  }
}

async function loadCatalog(refresh = false) {
  refreshCatalog.disabled = true;
  try {
    const q = refresh ? "true" : "false";
    const [lr, nr] = await Promise.all([
      fetch(`/api/leagues?refresh=${q}`),
      fetch(`/api/nations?refresh=${q}`),
    ]);
    const leagues = (await lr.json()).leagues || [];
    const nations = (await nr.json()).nations || [];
    fillSelect(leagueQuery, leagues, "— escolha a liga —");
    fillSelect(nation, nations, "— nenhuma —");
    leagueHint.textContent = `${leagues.length} ligas · ${nations.length} nações carregadas`;
    clubHint.textContent = "Digite o nome exato como no fminside.net";
  } catch (err) {
    leagueHint.textContent = "Falha ao carregar listas: " + err.message;
    clubHint.textContent = "Falha ao carregar listas: " + err.message;
  } finally {
    refreshCatalog.disabled = false;
  }
}

function currentQuery() {
  return mode() === "league"
    ? leagueQuery.value.trim()
    : clubQuery.value.trim();
}

function toRelFile(absPath) {
  const norm = String(absPath).replace(/\\/g, "/");
  const marker = "/output/";
  const idx = norm.toLowerCase().indexOf(marker);
  if (idx >= 0) return norm.slice(idx + marker.length);
  return norm.split("/").pop();
}

function renderJob(job) {
  statusPanel.hidden = false;
  const nat = job.nationality ? ` · ${job.nationality}` : "";
  statusTitle.textContent = `${job.mode === "club" ? "Clube" : "Liga"}: ${job.query}${nat}`;
  statusBadge.textContent = job.status;
  statusBadge.className = `badge ${job.status}`;
  statusMsg.textContent = job.message || "";

  const total = job.total || job.urls || 0;
  const done = job.done || 0;
  const pct =
    total > 0
      ? Math.min(100, Math.round((done / total) * 100))
      : job.status === "done"
        ? 100
        : 0;
  progressBar.style.width = `${pct}%`;
  progressText.textContent =
    job.stage && String(job.stage).startsWith("clubs_")
      ? statusMsg.textContent
      : job.stage === "club_crawl"
        ? statusMsg.textContent
        : job.stage === "crawl_page" ||
            job.stage === "crawl_start" ||
            job.stage === "crawl_done"
          ? `URLs: ${job.urls || 0}${job.batch ? ` · página ${job.batch}` : ""}`
          : total
            ? `Perfis: ${done}/${total} (${pct}%)`
            : "";

  // Aviso se o job parou de emitir progresso (possível travamento)
  let stallNote = "";
  if (job.status === "running" && job.updated_at) {
    const ageSec = (Date.now() - Date.parse(job.updated_at)) / 1000;
    if (ageSec > 45) {
      stallNote = ` ⚠ sem atualização há ${Math.round(ageSec)}s — pode estar lento ou travado`;
    }
  }
  if (stallNote && !String(statusMsg.textContent || "").includes("sem atualização")) {
    statusMsg.textContent = (job.message || "") + stallNote;
  }

  fileList.innerHTML = (job.files || [])
    .map((f) => {
      const rel = toRelFile(f);
      const name = rel.split("/").pop();
      return `<li><a href="/api/files/${encodeURI(rel)}" download>${name}</a> <span class="muted">${rel}</span></li>`;
    })
    .join("");

  logBox.textContent = (job.logs || []).join("\n");

  if (job.status === "done" || job.status === "error") {
    startBtn.disabled = false;
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }
}

async function pollJob(id) {
  try {
    const res = await fetch(`/api/jobs/${id}`);
    if (!res.ok) throw new Error(await res.text());
    const job = await res.json();
    renderJob(job);
  } catch (err) {
    statusMsg.textContent = "Erro ao consultar job: " + err.message;
  }
}

startBtn.addEventListener("click", async () => {
  const q = currentQuery();
  const nat = nation.value.trim();
  if (!q) {
    if (mode() === "league") leagueQuery.focus();
    else clubQuery.focus();
    return;
  }
  if (mode() === "league" && !nat) {
    const ok = confirm(
      "Sem nação, ligas com o mesmo nome (ex.: Série A) podem misturar países.\n\nContinuar mesmo assim?"
    );
    if (!ok) {
      nation.focus();
      return;
    }
  }

  const payload = {
    mode: mode(),
    query: q,
    nationality: nat,
  };
  const mp = $("maxPages").value;
  const mj = $("maxPlayers").value;
  if (mp) payload.max_pages = Number(mp);
  if (mj) payload.max_players = Number(mj);

  startBtn.disabled = true;
  statusPanel.hidden = false;
  statusMsg.textContent = "Enfileirando…";
  fileList.innerHTML = "";
  logBox.textContent = "";

  try {
    const res = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(() => pollJob(data.id), 1500);
    pollJob(data.id);
  } catch (err) {
    startBtn.disabled = false;
    statusBadge.textContent = "error";
    statusBadge.className = "badge error";
    statusMsg.textContent = String(err.message || err);
  }
});

refreshCatalog.addEventListener("click", () => loadCatalog(true));

updateModeUI();
loadCatalog(false);
