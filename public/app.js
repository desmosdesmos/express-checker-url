// Executive Mini App Application Logic
document.addEventListener("DOMContentLoaded", () => {
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

  // Icons SVG definitions
  const ICONS = {
    pass: `<svg class="status-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
    warn: `<svg class="status-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    fail: `<svg class="status-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`
  };

  // DOM Elements
  const inputCard = document.getElementById("input-card");
  const loadingCard = document.getElementById("loading-card");
  const errorCard = document.getElementById("error-card");
  const resultsView = document.getElementById("results-view");

  const btnBackHome = document.getElementById("btn-back-home");
  const headerBrand = document.getElementById("header-brand");
  const siteUrlInput = document.getElementById("site-url");
  const btnSubmit = document.getElementById("btn-submit");
  const btnClear = document.getElementById("btn-clear");
  const btnRetry = document.getElementById("btn-retry");
  const btnDownloadPdf = document.getElementById("btn-download-pdf");
  const btnCopySummary = document.getElementById("btn-copy-summary");
  const btnScrollDetails = document.getElementById("btn-scroll-details");
  const toast = document.getElementById("toast");

  // Subscription Modal Elements
  const subModal = document.getElementById("sub-modal");
  const btnModalChannel = document.getElementById("btn-modal-channel");
  const btnModalVerify = document.getElementById("btn-modal-verify");

  let currentAuditData = null;
  let loadingInterval = null;
  let pendingAuditUrl = "";

  // Check URL query parameters for auto-audit
  const urlParams = new URLSearchParams(window.location.search);
  const querySite = urlParams.get("site");
  if (querySite) {
    siteUrlInput.value = querySite;
    handleAuditRequest();
  }

  // Input events
  siteUrlInput.addEventListener("input", () => {
    btnClear.style.display = siteUrlInput.value ? "flex" : "none";
  });

  btnClear.addEventListener("click", () => {
    siteUrlInput.value = "";
    btnClear.style.display = "none";
    siteUrlInput.focus();
  });

  siteUrlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleAuditRequest();
  });

  document.querySelectorAll(".quick-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      triggerHaptic("light");
      siteUrlInput.value = chip.dataset.url;
      btnClear.style.display = "flex";
      handleAuditRequest();
    });
  });

  btnSubmit.addEventListener("click", handleAuditRequest);
  btnRetry.addEventListener("click", resetToHome);

  // Return to Home handler (Single unified button)
  btnBackHome.addEventListener("click", resetToHome);

  function resetToHome() {
    triggerHaptic("light");
    resultsView.style.display = "none";
    loadingCard.style.display = "none";
    errorCard.style.display = "none";
    inputCard.style.display = "block";

    btnBackHome.style.display = "none";
    headerBrand.style.display = "flex";

    siteUrlInput.value = "";
    btnClear.style.display = "none";
    siteUrlInput.focus();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // Scroll to deep-dive details
  btnScrollDetails.addEventListener("click", () => {
    triggerHaptic("light");
    const target = document.getElementById("deep-dive-section");
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  // Mandatory Subscription Flow
  async function handleAuditRequest() {
    const rawUrl = siteUrlInput.value.trim();
    if (!rawUrl) {
      siteUrlInput.focus();
      return;
    }

    pendingAuditUrl = rawUrl;

    // Check if user already confirmed subscription
    const isSubscribedCached = localStorage.getItem("yanv_sub_ok") === "1";
    if (isSubscribedCached) {
      startAudit(rawUrl);
      return;
    }

    // Attempt live check via Telegram user ID if in WebApp
    const telegramUserId = tg?.initDataUnsafe?.user?.id;
    if (telegramUserId) {
      try {
        const subRes = await fetch("/api/check-sub", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: telegramUserId })
        });
        const subData = await subRes.json();
        if (subData.subscribed) {
          localStorage.setItem("yanv_sub_ok", "1");
          startAudit(rawUrl);
          return;
        }
      } catch (e) {
        // Fallback to modal
      }
    }

    // Show subscription gate modal
    triggerHaptic("warning");
    subModal.style.display = "flex";
  }

  btnModalVerify.addEventListener("click", () => {
    triggerHaptic("success");
    localStorage.setItem("yanv_sub_ok", "1");
    subModal.style.display = "none";
    showToast("Подписка подтверждена! Запуск аудита...");
    if (pendingAuditUrl) {
      startAudit(pendingAuditUrl);
    }
  });

  // Start Audit
  async function startAudit(rawUrl) {
    triggerHaptic("medium");

    inputCard.style.display = "none";
    errorCard.style.display = "none";
    resultsView.style.display = "none";
    loadingCard.style.display = "block";

    document.getElementById("loading-domain").textContent = rawUrl;
    btnBackHome.style.display = "none";

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
        throw new Error(errData.detail || "Ошибка соединения с указанным сайтом");
      }

      currentAuditData = await response.json();
      renderResults(currentAuditData);
      triggerHaptic("success");

    } catch (err) {
      clearInterval(loadingInterval);
      loadingCard.style.display = "none";
      errorCard.style.display = "block";
      document.getElementById("error-message").textContent = err.message || "Не удалось проверить сайт. Убедитесь, что адрес указан верно.";
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

    steps.forEach((s) => (s.className = "step-line"));
    steps[0].className = "step-line active";

    let stepIdx = 0;
    loadingInterval = setInterval(() => {
      if (stepIdx < steps.length - 1) {
        steps[stepIdx].className = "step-line done";
        stepIdx++;
        steps[stepIdx].className = "step-line active";
      }
    }, 1100);
  }

  // Render Full Results
  function renderResults(data) {
    loadingCard.style.display = "none";
    resultsView.style.display = "block";

    // Show single header back button
    btnBackHome.style.display = "inline-flex";

    // Header Chips
    document.getElementById("res-domain").textContent = data.domain;
    document.getElementById("res-cms-chip").textContent = data.cms_platform;
    document.getElementById("res-ssl-chip").textContent = data.is_https ? "HTTPS" : "Без SSL";
    document.getElementById("res-ssl-chip").className = data.is_https ? "chip chip-ssl" : "chip chip-neutral";

    // 1. Executive Summary Snapshot
    const exec = data.executive_summary;
    const badgeEl = document.getElementById("exec-badge");
    badgeEl.textContent = exec.verdict_badge;

    if (exec.overall_risk === "Критический риск") {
      badgeEl.className = "verdict-pill badge-critical";
    } else if (exec.overall_risk === "Высокий риск") {
      badgeEl.className = "verdict-pill badge-high";
    } else {
      badgeEl.className = "verdict-pill badge-safe";
    }

    document.getElementById("exec-title").textContent = exec.verdict_title;
    document.getElementById("exec-site-type").textContent = data.site_type;

    // Render Takeaways
    const takeawaysContainer = document.getElementById("exec-takeaways");
    takeawaysContainer.innerHTML = "";
    (exec.takeaways || []).forEach((t) => {
      const itemEl = document.createElement("div");
      itemEl.className = "takeaway-item";
      itemEl.innerHTML = `
        <span class="takeaway-dot ${t.type === 'positive' ? 'pos' : 'neg'}"></span>
        <span>${t.text}</span>
      `;
      takeawaysContainer.appendChild(itemEl);
    });

    // Snapshot numbers (Zero overflow)
    document.getElementById("snap-legal").textContent = `${data.legal.passed} / ${data.legal.total}`;
    document.getElementById("snap-fine-form").textContent = data.legal.fine_form;
    document.getElementById("snap-hosting").textContent = `${data.hosting_provider_guess || data.hosting_provider} (${data.is_ru_hosting ? 'РФ' : 'Зарубеж'})`;

    // Filter counts
    document.getElementById("count-failed").textContent = data.legal.failed;
    document.getElementById("count-warning").textContent = data.legal.warning;
    document.getElementById("count-passed").textContent = data.legal.passed;

    // Marketing score
    document.getElementById("res-marketing-score").textContent = data.marketing.score;

    // 2. Render In-depth Legal Blocks
    renderLegalBlocks(data.legal.blocks);

    // 3. Render Marketing Factors
    renderMarketingItems(data.marketing.checks);

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
      blockEl.className = "audit-block-card";

      const topEl = document.createElement("div");
      topEl.className = "block-top";
      topEl.innerHTML = `
        <span>${block.block_title}</span>
        <span class="block-fine-badge">${block.items[0]?.fine_info || ""}</span>
      `;

      const listEl = document.createElement("div");
      listEl.className = "block-items-stack";

      filteredItems.forEach((item) => {
        const itemEl = document.createElement("div");
        itemEl.className = `check-item status-${item.status}`;

        let iconSvg = ICONS.pass;
        if (item.status === "failed") iconSvg = ICONS.fail;
        else if (item.status === "warning") iconSvg = ICONS.warn;

        itemEl.innerHTML = `
          <div class="item-top-row">
            ${iconSvg}
            <span class="item-title-text">${item.title}</span>
          </div>
          <div class="item-law-ref">Статья: ${item.law_ref}</div>
          <div class="item-text-body">${item.details}</div>
          <div class="item-fix-panel">
            <strong>Действие:</strong> ${item.tilda_fix}
          </div>
        `;
        listEl.appendChild(itemEl);
      });

      blockEl.appendChild(topEl);
      blockEl.appendChild(listEl);
      container.appendChild(blockEl);
    });
  }

  function renderMarketingItems(checks) {
    const container = document.getElementById("marketing-items-container");
    container.innerHTML = "";

    checks.forEach((item) => {
      const itemEl = document.createElement("div");
      itemEl.className = `check-item status-${item.status}`;

      let iconSvg = ICONS.pass;
      if (item.status === "failed") iconSvg = ICONS.fail;
      else if (item.status === "warning") iconSvg = ICONS.warn;

      itemEl.innerHTML = `
        <div class="item-top-row">
          ${iconSvg}
          <span class="item-title-text">${item.title}</span>
        </div>
        <div class="item-law-ref">${item.category} • ${item.impact}</div>
        <div class="item-text-body">${item.details}</div>
        <div class="item-fix-panel">
          <strong>Совет:</strong> ${item.tilda_fix}
        </div>
      `;
      container.appendChild(itemEl);
    });
  }

  // Filter pills
  document.querySelectorAll(".filter-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      triggerHaptic("light");
      document.querySelectorAll(".filter-pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      const filter = pill.dataset.filter;
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
    btnDownloadPdf.innerHTML = "<span>Формирование PDF...</span>";
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
