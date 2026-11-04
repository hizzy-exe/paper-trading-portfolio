const els = {
  error: document.getElementById("error"),
  status: document.getElementById("status-label"),
  totalValue: document.getElementById("total-value"),
  totalCost: document.getElementById("total-cost"),
  totalPnl: document.getElementById("total-pnl"),
  totalCount: document.getElementById("total-count"),
  body: document.getElementById("holdings-body"),
  form: document.getElementById("add-form"),
  refresh: document.getElementById("refresh-btn"),
  quoteForm: document.getElementById("quote-form"),
  quoteResult: document.getElementById("quote-result"),
  quoteSymbolLabel: document.getElementById("quote-symbol-label"),
  quotePrice: document.getElementById("quote-price"),
  quoteChange: document.getElementById("quote-change"),
  useQuoteBtn: document.getElementById("use-quote-btn"),
  addSymbol: document.getElementById("add-symbol"),
  addType: document.getElementById("add-type"),
  addCost: document.getElementById("add-cost"),
};

let lastQuote = null;

function money(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });
}

function pct(n) {
  if (n == null || Number.isNaN(n)) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

function cls(n) {
  if (n == null || Number.isNaN(n)) return "";
  return n >= 0 ? "pos" : "neg";
}

function showError(msg) {
  els.error.textContent = msg;
  els.error.classList.add("visible");
}

function clearError() {
  els.error.classList.remove("visible");
  els.error.textContent = "";
}

function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function loadHoldings() {
  els.status.textContent = "Loading…";
  try {
    const res = await fetch("/api/holdings");
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || "Failed to load");

    clearError();
    const s = data.summary || {};
    els.totalValue.textContent = money(s.total_value);
    els.totalCost.textContent = s.total_cost != null ? money(s.total_cost) : "—";
    els.totalPnl.textContent = s.total_pnl != null ? money(s.total_pnl) : "—";
    els.totalPnl.className = "value " + cls(s.total_pnl);
    els.totalCount.textContent = String(s.count ?? 0);

    const rows = data.holdings || [];
    if (!rows.length) {
      els.body.innerHTML =
        '<tr><td colspan="8" class="muted">No holdings yet. Add one above.</td></tr>';
    } else {
      els.body.innerHTML = rows
        .map((h) => {
          const pnlText =
            h.pnl != null
              ? `${money(h.pnl)}${h.pnl_pct != null ? ` (${pct(h.pnl_pct)})` : ""}`
              : "—";
          return `
            <tr>
              <td><strong>${escapeHtml(h.symbol)}</strong></td>
              <td>${escapeHtml(h.asset_type)}</td>
              <td>${h.quantity}</td>
              <td>${money(h.price)}</td>
              <td>${money(h.value)}</td>
              <td class="${cls(h.pnl)}">${pnlText}</td>
              <td class="${cls(h.change_24h)}">${pct(h.change_24h)}</td>
              <td><button class="btn-del" data-id="${h.id}">Delete</button></td>
            </tr>
          `;
        })
        .join("");

      els.body.querySelectorAll(".btn-del").forEach((btn) => {
        btn.addEventListener("click", () => removeHolding(btn.dataset.id));
      });
    }

    els.status.textContent = "Live";
  } catch (err) {
    showError(err.message);
    els.status.textContent = "Error";
  }
}

async function removeHolding(id) {
  try {
    const res = await fetch(`/api/holdings/${id}`, { method: "DELETE" });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Delete failed");
    }
    await loadHoldings();
  } catch (err) {
    showError(err.message);
  }
}

els.quoteForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const symbol = document.getElementById("quote-symbol").value.trim();
  const assetType = document.getElementById("quote-type").value;
  if (!symbol) return;

  els.status.textContent = "Quoting…";
  try {
    const res = await fetch(
      `/api/quote/${assetType}/${encodeURIComponent(symbol)}`
    );
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Quote failed");
    if (data.error) throw new Error(data.error);
    if (data.price == null) throw new Error("No price returned for that symbol");

    lastQuote = data;
    clearError();
    els.quoteSymbolLabel.textContent = data.symbol;
    els.quotePrice.textContent = money(data.price);
    els.quoteChange.textContent = pct(data.change_24h);
    els.quoteChange.className = "quote-change " + cls(data.change_24h);
    els.quoteResult.classList.remove("hidden");
    els.status.textContent = "Live";
  } catch (err) {
    lastQuote = null;
    els.quoteResult.classList.add("hidden");
    showError(err.message);
    els.status.textContent = "Error";
  }
});

els.useQuoteBtn.addEventListener("click", () => {
  if (!lastQuote) return;
  els.addSymbol.value = lastQuote.symbol;
  els.addType.value = lastQuote.asset_type;
  // pre-fill cost basis with current price so P&L starts near zero unless user edits
  if (lastQuote.price != null) {
    els.addCost.value = Number(lastQuote.price).toFixed(2);
  }
  els.addSymbol.focus();
});

els.form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(els.form);
  const payload = {
    symbol: String(fd.get("symbol") || "").trim(),
    asset_type: String(fd.get("asset_type") || "stock"),
    quantity: Number(fd.get("quantity")),
    cost_basis:
      fd.get("cost_basis") === "" || fd.get("cost_basis") == null
        ? null
        : Number(fd.get("cost_basis")),
    notes: "",
  };

  try {
    const res = await fetch("/api/holdings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || JSON.stringify(data) || "Add failed");
    }
    els.form.reset();
    await loadHoldings();
  } catch (err) {
    showError(err.message);
  }
});

els.refresh.addEventListener("click", () => loadHoldings());

loadHoldings();
setInterval(loadHoldings, 60000);
