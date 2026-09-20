const money = (n) => (n === null || n === undefined) ? "-" : `${n.toFixed(2)} €`;

async function fetchJSON(url, options) {
  const resp = await fetch(url, options);
  if (!resp.ok) throw new Error(`${url}: ${resp.status}`);
  return resp.json();
}

async function loadSummary() {
  const el = document.getElementById("summary-cards");
  if (!el) return;
  const s = await fetchJSON("/api/summary");
  el.innerHTML = `
    <div class="card"><div class="label">Beneficio acumulado</div><div class="value profit">${money(s.total_profit)}</div></div>
    <div class="card"><div class="label">Compras realizadas</div><div class="value">${s.num_purchases}</div></div>
    <div class="card"><div class="label">Oportunidades pendientes</div><div class="value">${s.num_pending}</div></div>
  `;
}

function currencyBadge(status) {
  const labelMap = { eur: "EUR ✓", no_eur: "No EUR", sin_confirmar: "¿EUR?" };
  return `<span class="badge badge-${status}">${labelMap[status] || status}</span>`;
}

function conditionBadge(cond) {
  const labelMap = { con_caratula: "Con carátula", sin_caratula: "Sin carátula", sin_confirmar: "Sin confirmar" };
  return `<span class="badge badge-${cond}">${labelMap[cond] || cond}</span>`;
}

function currentConditionFilter() {
  const checked = document.querySelector('input[name="condition-filter"]:checked');
  return checked ? checked.value : "todas";
}

async function loadDeals() {
  const body = document.getElementById("deals-body");
  if (!body) return;
  const deals = await fetchJSON("/api/deals?status=pendiente");
  const filter = currentConditionFilter();
  const filtered = filter === "todas" ? deals
    : filter === "packs" ? deals.filter(d => d.is_pack)
    : deals.filter(d => d.condition === filter);

  if (filtered.length === 0) {
    body.innerHTML = `<tr><td colspan="11" class="empty">No hay oportunidades todavía. Pulsa "Buscar oportunidades reales" o carga los datos de ejemplo.</td></tr>`;
    return;
  }

  body.innerHTML = filtered.map(d => `
    <tr data-id="${d.id}">
      <td>${d.is_pack ? "📦 " : ""}${d.title}${d.is_pack && d.matched_titles ? `<div class="pack-contents">Contiene: ${d.matched_titles.split(" | ").join(", ")}</div>` : ""}</td>
      <td>${d.platform}</td>
      <td>${conditionBadge(d.condition)}</td>
      <td>${d.source}</td>
      <td>${money(d.listing_price)}</td>
      <td>${currencyBadge(d.currency_status)}</td>
      <td>${d.seller_location || "-"}</td>
      <td>${money(d.cex_cash_price)}</td>
      <td class="profit-pos">${money(d.profit_estimate)}</td>
      <td>${d.margin_pct != null ? d.margin_pct + "%" : "-"}</td>
      <td class="actions-cell">
        ${d.listing_url ? `<a class="listing-link" href="${d.listing_url}" target="_blank" rel="noopener">Ver anuncio</a>` : ""}
        ${d.currency_status === "sin_confirmar" ? `<button class="btn btn-small btn-check" data-action="ask" data-url="${d.listing_url || ''}" data-id="${d.id}">Preguntar/Comprobar</button>` : ""}
        <button class="btn btn-small btn-buy" data-action="buy" data-id="${d.id}" data-price="${d.listing_price}">Comprado</button>
        <button class="btn btn-small btn-discard" data-action="discard" data-id="${d.id}">Descartar</button>
      </td>
    </tr>
  `).join("");
}

async function loadPurchases() {
  const body = document.getElementById("purchases-body");
  if (!body) return;
  const deals = await fetchJSON("/api/deals?status=comprado");
  if (deals.length === 0) {
    body.innerHTML = `<tr><td colspan="8" class="empty">Todavía no has marcado ninguna compra.</td></tr>`;
    return;
  }
  body.innerHTML = deals.map(d => `
    <tr>
      <td>${d.title}</td>
      <td>${d.platform}</td>
      <td>${conditionBadge(d.condition)}</td>
      <td>${d.source}</td>
      <td>${money(d.bought_price)}</td>
      <td>${money(d.cex_cash_price)}</td>
      <td class="profit-pos">${money(d.bought_profit)}</td>
      <td>${d.bought_at ? new Date(d.bought_at).toLocaleString("es-ES") : "-"}</td>
    </tr>
  `).join("");
}

let chartInstance = null;
async function loadChart() {
  const canvas = document.getElementById("profit-chart");
  if (!canvas) return;
  const data = await fetchJSON("/api/chart");
  const labels = data.labels.map(l => new Date(l).toLocaleDateString("es-ES"));
  if (chartInstance) chartInstance.destroy();
  chartInstance = new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Beneficio acumulado (€)",
        data: data.cumulative_profit,
        borderColor: "#22c55e",
        backgroundColor: "rgba(34,197,94,0.15)",
        fill: true,
        tension: 0.25,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: "#e2e8f0" } } },
      scales: {
        x: { ticks: { color: "#94a3b8" }, grid: { color: "#334155" } },
        y: { ticks: { color: "#94a3b8" }, grid: { color: "#334155" } },
      },
    },
  });
}

async function refreshAll() {
  await Promise.all([loadSummary(), loadDeals(), loadPurchases(), loadChart()]);
}

document.addEventListener("click", async (ev) => {
  const btn = ev.target.closest("button[data-action]");
  if (!btn) return;
  const { action, id } = btn.dataset;

  if (action === "buy") {
    const suggested = btn.dataset.price;
    const price = prompt("¿Por cuánto has comprado el juego? (€)", suggested);
    if (price === null) return;
    const parsed = parseFloat(price.replace(",", "."));
    if (isNaN(parsed)) { alert("Precio no válido"); return; }
    await fetchJSON(`/deals/${id}/buy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ buy_price: parsed }),
    });
    await refreshAll();
  }

  if (action === "discard") {
    await fetchJSON(`/deals/${id}/discard`, { method: "POST" });
    await refreshAll();
  }

  if (action === "ask") {
    const template = document.getElementById("ask-message-template");
    const message = template ? template.content.textContent.trim() : "¿El precio está en euros?";
    try {
      await navigator.clipboard.writeText(message);
      alert("Mensaje copiado al portapapeles:\n\n" + message + "\n\nSe abrirá el anuncio para que se lo pegues al vendedor.");
    } catch (e) {
      alert("Pregúntale al vendedor: " + message);
    }
    const url = btn.dataset.url;
    if (url) window.open(url, "_blank", "noopener");

    const setEur = confirm("Cuando el vendedor te responda: ¿confirmó que el precio es en EUR? Aceptar = Sí, Cancelar = No");
    await fetchJSON(`/deals/${id}/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ currency_status: setEur ? "eur" : "no_eur" }),
    });
    await refreshAll();
  }
});

document.addEventListener("change", (ev) => {
  if (ev.target.name === "condition-filter") loadDeals();
});

const scanBtn = document.getElementById("btn-scan");
if (scanBtn) {
  scanBtn.addEventListener("click", async () => {
    const status = document.getElementById("scan-status");
    scanBtn.disabled = true;
    status.textContent = "Buscando... esto puede tardar un rato.";
    try {
      const stats = await fetchJSON("/scan", { method: "POST" });
      if (stats.games_checked === 0 && stats.errors && stats.errors.length) {
        status.textContent = stats.errors[0];
      } else {
        status.textContent = `Listo: ${stats.games_checked} juegos revisados, ${stats.deals_found} oportunidades encontradas (${stats.packs_found || 0} packs).`;
      }
      await refreshAll();
    } catch (e) {
      status.textContent = "Error durante el escaneo, revisa la consola/logs del servidor.";
    } finally {
      scanBtn.disabled = false;
    }
  });
}

const demoBtn = document.getElementById("btn-demo");
if (demoBtn) {
  demoBtn.addEventListener("click", async () => {
    await fetchJSON("/scan/demo", { method: "POST" });
    await refreshAll();
  });
}

async function loadGames() {
  const body = document.getElementById("games-body");
  if (!body) return;
  const games = await fetchJSON("/api/games");
  if (games.length === 0) {
    body.innerHTML = `<tr><td colspan="5" class="empty">Todavía no has añadido ningún juego. Búscalo en es.webuy.com y añade su precio "pagamos en efectivo" arriba.</td></tr>`;
    return;
  }
  body.innerHTML = games.map(g => `
    <tr>
      <td>${g.title}</td>
      <td>${g.platform}</td>
      <td>${money(g.cex_cash_price)}</td>
      <td>${g.updated_at ? new Date(g.updated_at).toLocaleDateString("es-ES") : "-"}</td>
      <td><button class="btn btn-small btn-delete" data-action="delete-game" data-id="${g.id}">Eliminar</button></td>
    </tr>
  `).join("");
}

const addGameBtn = document.getElementById("btn-add-game");
if (addGameBtn) {
  addGameBtn.addEventListener("click", async () => {
    const title = document.getElementById("game-title").value.trim();
    const platform = document.getElementById("game-platform").value;
    const price = parseFloat(document.getElementById("game-price").value.replace(",", "."));
    if (!title || isNaN(price) || price <= 0) {
      alert("Rellena el nombre del juego y un precio válido.");
      return;
    }
    const resp = await fetch("/api/games", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, platform, cex_cash_price: price }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      alert(err.error || "No se pudo añadir el juego");
      return;
    }
    document.getElementById("game-title").value = "";
    document.getElementById("game-price").value = "";
    await loadGames();
  });
}

document.addEventListener("click", async (ev) => {
  const btn = ev.target.closest('button[data-action="delete-game"]');
  if (!btn) return;
  await fetchJSON(`/games/${btn.dataset.id}/delete`, { method: "POST" });
  await loadGames();
});

const bulkAddBtn = document.getElementById("btn-bulk-add");
if (bulkAddBtn) {
  bulkAddBtn.addEventListener("click", async () => {
    const textarea = document.getElementById("bulk-games");
    const resultEl = document.getElementById("bulk-result");
    const text = textarea.value.trim();
    if (!text) return;
    bulkAddBtn.disabled = true;
    const result = await fetchJSON("/api/games/bulk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    bulkAddBtn.disabled = false;
    let msg = `Añadidos: ${result.added}.`;
    if (result.errors && result.errors.length) {
      msg += ` Errores:\n` + result.errors.join("\n");
    } else {
      textarea.value = "";
    }
    resultEl.textContent = msg;
    resultEl.style.whiteSpace = "pre-line";
    await loadGames();
  });
}

loadGames();
refreshAll();
