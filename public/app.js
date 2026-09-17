// Telegram Mini App Application Logic
document.addEventListener("DOMContentLoaded", () => {
  // 1. Initialize Telegram WebApp SDK
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  function triggerHaptic(type = "light") {
    if (tg?.HapticFeedback) {
      if (type === "success") tg.HapticFeedback.notificationOccurred("success");
      else if (type === "warning") tg.HapticFeedback.notificationOccurred("warning");
      else if (type === "error") tg.HapticFeedback.notificationOccurred("error");
      else tg.HapticFeedback.impactOccurred("medium");
    }
  }

  // DOM Elements
  const inputCard = document.getElementById("input-card");
  const loadingCard = document.getElementById("loading-card");
  const errorCard = document.getElementById("error-card");
  const resultsView = document.getElementById("results-view");

  const siteUrlInput = document.getElementById("site-url");
  const btnSubmit = document.getElementById("btn-submit");
  const btnClear = document.getElementById("btn-clear");
  const btnRetry = document.getElementById("btn-retry");
  const btnNewCheck = document.getElementById("btn-new-check");
  const btnDownloadPdf = document.getElementById("btn-download-pdf");
  const btnCopySummary = document.getElementById("btn-copy-summary");
  const toast = document.getElementById("toast");

  let currentAuditData = null;
  let loadingInterval = null;

  // Input events
  siteUrlInput.addEventListener("input", () => {
    btnClear.style.display = siteUrlInput.value ? "block" : "none";
  });

  btnClear.addEventListener("click", () => {
    siteUrlInput.value = "";
    btnClear.style.display = "none";
    siteUrlInput.focus();
  });

  siteUrlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      startAudit();
    }
  });

  document.querySelectorAll(".quick-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      triggerHaptic("light");
      siteUrlInput.value = chip.dataset.url;
      btnClear.style.display = "block";
      startAudit();
    });
  });

  btnSubmit.addEventListener("click", startAudit);
  btnRetry.addEventListener("click", () => {
    errorCard.style.display = "none";
    inputCard.style.display = "block";
  });
  btnNewCheck.addEventListener("click", () => {
    triggerHaptic("light");
    resultsView.style.display = "none";
    inputCard.style.display = "block";
    siteUrlInput.value = "";
    btnClear.style.display = "none";
    siteUrlInput.focus();
  });

  // Start Audit
  async function startAudit() {
    const rawUrl = siteUrlInput.value.trim();
    if (!rawUrl) {
      siteUrlInput.focus();
      return;
    }

    triggerHaptic("medium");

    // Switch to loading
    inputCard.style.display = "none";
    errorCard.style.display = "none";
    resultsView.style.display = "none";
    loadingCard.style.display = "block";
    document.getElementById("loading-domain").textContent = rawUrl;

    animateLoadingSteps();

    try {
      const response = await fetch("/api/audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: rawUrl })
      });

      clearInterval(loadingInterval);

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Ошибка соединения с сайтом");
      }

      currentAuditData = await response.json();
      renderResults(currentAuditData);
      triggerHaptic("success");

    } catch (err) {
      clearInterval(loadingInterval);
      loadingCard.style.display = "none";
      errorCard.style.display = "block";
      document.getElementById("error-message").textContent = err.message || "Не удалось проверить указанный адрес.";
      triggerHaptic("error");
    }
  }

  function animateLoadingSteps() {
    const steps = [
      document.getElementById("step-1"),
      document.getElementById("step-2"),
      document.getElementById("step-3"),
      document.getElementById("step-4"),
      document.getElementById("step-5")
    ];

    steps.forEach((s) => (s.className = "step"));
    steps[0].className = "step active";

    let stepIdx = 0;
    loadingInterval = setInterval(() => {
      if (stepIdx < steps.length - 1) {
        steps[stepIdx].className = "step done";
        stepIdx++;
        steps[stepIdx].className = "step active";
      }
    }, 1200);
  }

  // Render Full Results
  function renderResults(data) {
    loadingCard.style.display = "none";
    resultsView.style.display = "block";

    // Header info
    document.getElementById("res-domain").textContent = data.domain;
    document.getElementById("res-tilda-badge").style.display = data.is_tilda ? "inline-block" : "none";
    document.getElementById("res-ssl-badge").textContent = data.is_https ? "🔒 HTTPS" : "⚠️ Без SSL";
    document.getElementById("res-ssl-badge").style.color = data.is_https ? "#10b981" : "#ef4444";
    document.getElementById("res-speed-badge").textContent = `⚡ ${data.response_time_ms} мс`;

    // Readiness & risk
    const legal = data.legal;
    document.getElementById("res-readiness-val").textContent = `${legal.passed} / ${legal.total} (${legal.percent}%)`;
    document.getElementById("res-progress-bar").style.width = `${legal.percent}%`;

    const riskEl = document.getElementById("res-risk-level");
    riskEl.textContent = legal.overall_risk;
    riskEl.style.color = legal.risk_color;

    document.getElementById("res-fine-form").textContent = legal.fine_form;
    document.getElementById("res-fine-loc").textContent = legal.fine_loc;

    // Filter counts
    document.getElementById("count-failed").textContent = legal.failed;
    document.getElementById("count-warning").textContent = legal.warning;
    document.getElementById("count-passed").textContent = legal.passed;

    // Marketing score
    document.getElementById("res-marketing-score").textContent = data.marketing.score;

    // Render Legal Blocks
    renderLegalBlocks(legal.blocks);

    // Render Marketing Items
    renderMarketingItems(data.marketing.checks);

    // Scroll to top of results
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function renderLegalBlocks(blocks, filter = "all") {
    const container = document.getElementById("legal-blocks-container");
    container.innerHTML = "";

    blocks.forEach((block) => {
      const filteredItems = block.items.filter((item) => {
        if (filter === "all") return true;
        return item.status === filter;
      });

      if (filteredItems.length === 0) return;

      const blockEl = document.createElement("div");
      blockEl.className = "legal-block";

      const headerEl = document.createElement("div");
      headerEl.className = "block-header";
      headerEl.innerHTML = `
        <div class="block-title">${block.block_title}</div>
        <div class="block-fine-tag">${block.items[0]?.fine_info || ""}</div>
      `;

      const listEl = document.createElement("div");
      listEl.className = "block-items-list";

      filteredItems.forEach((item) => {
        const itemEl = document.createElement("div");
        itemEl.className = `audit-item status-${item.status}`;

        let statusIcon = "🟢";
        if (item.status === "failed") statusIcon = "🔴";
        else if (item.status === "warning") statusIcon = "🟡";

        itemEl.innerHTML = `
          <div class="item-head">
            <div class="item-title-row">
              <span class="status-badge">${statusIcon}</span>
              <span class="item-title">${item.title}</span>
            </div>
          </div>
          <div class="item-law">Статья: ${item.law_ref}</div>
          <div class="item-details">${item.details}</div>
          <div class="item-fix-box">
            <strong>Как исправить на Тильде:</strong> ${item.tilda_fix}
          </div>
        `;
        listEl.appendChild(itemEl);
      });

      blockEl.appendChild(headerEl);
      blockEl.appendChild(listEl);
      container.appendChild(blockEl);
    });
  }

  function renderMarketingItems(checks) {
    const container = document.getElementById("marketing-items-container");
    container.innerHTML = "";

    checks.forEach((item) => {
      const itemEl = document.createElement("div");
      itemEl.className = `audit-item status-${item.status}`;

      let statusIcon = "🟢";
      if (item.status === "failed") statusIcon = "🔴";
      else if (item.status === "warning") statusIcon = "🟡";

      itemEl.innerHTML = `
        <div class="item-head">
          <div class="item-title-row">
            <span class="status-badge">${statusIcon}</span>
            <span class="item-title">${item.title}</span>
          </div>
        </div>
        <div class="item-law">${item.category} • ${item.impact}</div>
        <div class="item-details">${item.details}</div>
        <div class="item-fix-box">
          <strong>Совет по продажам:</strong> ${item.tilda_fix}
        </div>
      `;
      container.appendChild(itemEl);
    });
  }

  // Filter chips
  document.querySelectorAll(".filter-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      triggerHaptic("light");
      document.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      const filter = chip.dataset.filter;
      if (currentAuditData) {
        renderLegalBlocks(currentAuditData.legal.blocks, filter);
      }
    });
  });

  // Tab navigation
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      triggerHaptic("light");
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));

      btn.classList.add("active");
      document.getElementById(btn.dataset.tab).classList.add("active");
    });
  });

  // Download PDF Action
  btnDownloadPdf.addEventListener("click", async () => {
    if (!currentAuditData) return;
    triggerHaptic("medium");

    const originalText = btnDownloadPdf.innerHTML;
    btnDownloadPdf.innerHTML = "<span>⏳ Формирование PDF...</span>";
    btnDownloadPdf.disabled = true;

    try {
      const res = await fetch("/api/export-pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: currentAuditData.url })
      });

      if (!res.ok) throw new Error("Не удалось сформировать PDF");

      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = `audit_2026_${currentAuditData.domain.replace(/\./g, "_")}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);

      showToast("PDF-отчет успешно сформирован и скачан!");
      triggerHaptic("success");
    } catch (e) {
      showToast("Ошибка при скачивании PDF");
      triggerHaptic("error");
    } finally {
      btnDownloadPdf.innerHTML = originalText;
      btnDownloadPdf.disabled = false;
    }
  });

  // Copy Summary Action
  btnCopySummary.addEventListener("click", () => {
    if (!currentAuditData) return;
    triggerHaptic("light");

    const textToCopy = currentAuditData.telegram_summary;
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(textToCopy).then(() => {
        showToast("Краткая выжимка скопирована в буфер!");
        triggerHaptic("success");
      });
    } else {
      const textarea = document.createElement("textarea");
      textarea.value = textToCopy;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      textarea.remove();
      showToast("Краткая выжимка скопирована в буфер!");
      triggerHaptic("success");
    }
  });

  function showToast(msg) {
    toast.textContent = msg;
    toast.classList.add("show");
    setTimeout(() => {
      toast.classList.remove("show");
    }, 3000);
  }
});
