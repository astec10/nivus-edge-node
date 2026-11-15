(() => {
  "use strict";

  const byId = (id) => document.getElementById(id);
  const status = byId("refresh-status");
  const dot = byId("connection-dot");
  const connectionLabel = byId("connection-label");
  const items = Array.from(document.querySelectorAll("#milestones .item"));
  const filterButtons = Array.from(document.querySelectorAll("#filters [data-filter]"));
  const emptyMessage = byId("empty-filter");
  const stateNames = {
    all: "todos",
    active: "em andamento",
    blocked: "aguardando",
    planned: "planejados",
    done: "concluídos",
  };

  const pageStamp = new Date(document.lastModified);
  if (byId("page-updated")) {
    byId("page-updated").textContent = Number.isNaN(pageStamp.getTime())
      ? "data não disponível"
      : pageStamp.toLocaleString("pt-BR");
  }

  function updateCounters() {
    const counts = { all: items.length, active: 0, blocked: 0, planned: 0, done: 0 };
    items.forEach((item) => {
      const state = item.dataset.status;
      if (Object.prototype.hasOwnProperty.call(counts, state)) counts[state] += 1;
    });

    filterButtons.forEach((button) => {
      const count = button.querySelector("[data-count]");
      if (count) count.textContent = String(counts[button.dataset.filter] || 0);
    });

    const completion = byId("milestone-completion");
    if (completion) completion.textContent = counts.done + " / " + items.length;
    const summary = byId("milestone-state-summary");
    if (summary) {
      summary.textContent =
        counts.active + " em andamento · " +
        counts.blocked + " aguardando · " +
        counts.planned + " planejados";
    }
    return counts;
  }

  function applyFilter(selectedButton) {
    const selected = selectedButton.dataset.filter || "all";
    filterButtons.forEach((button) => {
      const isSelected = button === selectedButton;
      button.classList.toggle("active", isSelected);
      button.setAttribute("aria-pressed", String(isSelected));
    });

    let shown = 0;
    items.forEach((item) => {
      const visible = selected === "all" || item.dataset.status === selected;
      item.hidden = !visible;
      if (visible) shown += 1;
    });

    if (emptyMessage) emptyMessage.hidden = shown !== 0;
    const filterSummary = byId("filter-summary");
    if (filterSummary) {
      filterSummary.textContent =
        "Mostrando " + shown + " de " + items.length +
        " marcos · filtro: " + (stateNames[selected] || "todos");
    }
  }

  filterButtons.forEach((button) => {
    button.addEventListener("click", () => applyFilter(button));
  });
  updateCounters();
  applyFilter(filterButtons.find((button) => button.classList.contains("active")) || filterButtons[0]);

  document.querySelectorAll('[data-when="now"]').forEach((element) => {
    element.textContent = "agora · " + new Date().toLocaleTimeString("pt-BR");
  });
  setInterval(() => {
    document.querySelectorAll('[data-when="now"]').forEach((element) => {
      element.textContent = "agora · " + new Date().toLocaleTimeString("pt-BR");
    });
  }, 1000);

  const scriptElement = document.querySelector('script[src*="progress.js"]');
  const pageUrl = location.href.split("#")[0];
  const scriptUrl = scriptElement ? scriptElement.src : new URL("./progress.js", location.href).href;
  let checking = false;
  let baselineHtml = null;
  let baselineScript = null;
  let secondsUntilCheck = 20;

  const checkButton = byId("check-now");
  const controlsStatus = byId("controls-status");
  if (controlsStatus) controlsStatus.textContent = "Controles ativos";

  async function fetchText(url) {
    const response = await fetch(url, {
      cache: "no-store",
      credentials: "same-origin",
      headers: { "Cache-Control": "no-cache" },
    });
    if (!response.ok) throw new Error("HTTP " + response.status);
    return response.text();
  }

  async function checkForUpdate() {
    if (checking) return;
    checking = true;
    if (checkButton) {
      checkButton.disabled = true;
      checkButton.setAttribute("aria-busy", "true");
    }
    if (status) status.textContent = "Consultando a página e os controles…";

    try {
      if (location.protocol === "file:") throw new Error("pré-visualização local");
      const latestHtml = await fetchText(pageUrl);
      const latestScript = await fetchText(scriptUrl);

      if (baselineHtml === null || baselineScript === null) {
        baselineHtml = latestHtml;
        baselineScript = latestScript;
      } else if (latestHtml !== baselineHtml || latestScript !== baselineScript) {
        if (status) status.textContent = "Nova versão encontrada · atualizando…";
        location.reload();
        return;
      }

      if (dot) dot.className = "dot ok";
      if (connectionLabel) connectionLabel.textContent = "PÁGINA CONECTADA";
      secondsUntilCheck = 20;
      if (status) {
        status.textContent =
          "Página e controles conferidos às " +
          new Date().toLocaleTimeString("pt-BR") +
          " · próxima consulta em 20 s";
      }
    } catch (error) {
      secondsUntilCheck = 20;
      if (dot) dot.className = "dot";
      if (connectionLabel) {
        connectionLabel.textContent =
          location.protocol === "file:" ? "PRÉ-VISUALIZAÇÃO" : "SEM CONEXÃO";
      }
      if (status) {
        status.textContent =
          "Atualização automática indisponível nesta pré-visualização · conferido às " +
          new Date().toLocaleTimeString("pt-BR");
      }
    } finally {
      checking = false;
      if (checkButton) {
        checkButton.disabled = false;
        checkButton.removeAttribute("aria-busy");
      }
    }
  }

  if (checkButton) checkButton.addEventListener("click", checkForUpdate);
  setInterval(() => {
    secondsUntilCheck = Math.max(0, secondsUntilCheck - 1);
    if (
      status &&
      connectionLabel &&
      connectionLabel.textContent === "PÁGINA CONECTADA" &&
      !checking
    ) {
      status.textContent =
        "Página e controles conferidos · próxima consulta em " + secondsUntilCheck + " s";
    }
  }, 1000);

  checkForUpdate();
})();
