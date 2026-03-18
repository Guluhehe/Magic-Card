const form = document.getElementById("parser-form");
const urlInput = document.getElementById("url-input");
const statusDOM = document.getElementById("status");
const platformChip = document.getElementById("platform-chip");
const outputPanel = document.getElementById("output-panel");
const galleryContainer = document.getElementById("card-gallery");
const submitBtn = form.querySelector(".primary-btn");

// Controls
const colorSwatches = document.querySelectorAll(".color-swatch");
const densitySelect = document.getElementById("density");
const highlightsSelect = document.getElementById("show-highlights");
const layoutSelect = document.getElementById("layout-mode");

// State
let appState = {
  data: null,
  loading: false,
  abortController: null,
  config: {
    accent: "#0fbfba",
    density: "normal",
    highlights: "show",
    layout: "standard",
    themes: ["nebula", "circuit", "prism"]
  }
};

const REQUEST_TIMEOUT_MS = 30000; // 30s 前端超时

const twitterLogoSvg = `
  <svg class="platform-logo" viewBox="0 0 24 24" role="img" aria-label="Twitter" style="width:16px;height:16px;display:inline-block;vertical-align:middle;">
    <path fill="currentColor" d="M23.954 4.569c-.885.389-1.83.654-2.825.775 1.014-.611 1.794-1.574 2.163-2.723-.951.555-2.005.959-3.127 1.184-.897-.94-2.178-1.528-3.594-1.528-3.179 0-5.515 2.966-4.797 6.045-4.091-.205-7.719-2.165-10.148-5.144-1.29 2.213-.669 5.108 1.523 6.574-.806-.026-1.566-.247-2.229-.616-.054 2.281 1.581 4.415 3.949 4.89-.693.188-1.452.232-2.224.084.626 1.956 2.444 3.379 4.6 3.419-2.07 1.623-4.678 2.348-7.29 2.04 2.179 1.394 4.768 2.209 7.557 2.209 9.142 0 14.307-7.721 13.995-14.646.962-.695 1.797-1.562 2.457-2.549z"/>
  </svg>
`;

const youtubeLogoSvg = `
  <svg class="platform-logo" viewBox="0 0 24 24" role="img" aria-label="YouTube" style="width:24px;height:24px;display:inline-block;vertical-align:middle;color:#FF0000;">
    <path fill="currentColor" d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
  </svg>
`;

const sampleUrls = {
  youtube: "https://www.youtube.com/watch?v=NjYt_7R-1Dk",
  twitter: "https://x.com/OpenAI/status/1790432049117327631",
};

// --- Utils ---

const setStatus = (message, type = "info") => {
  statusDOM.textContent = message || "";
  statusDOM.className = message ? `status status-${type}` : "status hidden";
};

const getApiBase = () => {
  const metaBase = document.querySelector('meta[name="magiccard-api-base"]')?.getAttribute("content")?.trim();
  const windowBase = (window.MAGICCARD_API_BASE || "").trim();
  if (windowBase) return windowBase;
  if (metaBase) return metaBase;
  const host = window.location.hostname;
  return (host === "localhost" || host === "127.0.0.1") ? "http://127.0.0.1:5000" : "";
};

const setLoading = (loading) => {
  appState.loading = loading;
  submitBtn.disabled = loading;
  submitBtn.classList.toggle("is-loading", loading);
  if (loading) {
    submitBtn.innerHTML = `<span class="spinner"></span><span>解析中...</span>`;
  } else {
    submitBtn.innerHTML = `<span>生成卡片</span>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
        stroke-linecap="round" stroke-linejoin="round">
        <line x1="5" y1="12" x2="19" y2="12"></line>
        <polyline points="12 5 19 12 12 19"></polyline>
      </svg>`;
  }
};

// --- Rendering Logic ---

const createHighlightHTML = (items) => {
  if (!items || items.length === 0) return "";
  return items.map(item => `
    <div class="highlight">
      <span>${item.label}</span>
      <div>${item.text}</div>
    </div>
  `).join("");
};

const renderSkeletonCard = (theme) => {
  const card = document.createElement("article");
  card.className = `content-card variant-${theme} is-skeleton`;
  card.innerHTML = `
    <div class="variant-label">${theme}</div>
    <div class="card-header">
      <span class="skeleton-line" style="width:60px"></span>
      <span class="skeleton-line" style="width:40px"></span>
    </div>
    <div class="skeleton-line" style="width:80%;height:24px"></div>
    <div class="skeleton-block"></div>
    <div class="skeleton-highlights">
      <div class="skeleton-line" style="width:100%;height:48px;border-radius:14px"></div>
      <div class="skeleton-line" style="width:100%;height:48px;border-radius:14px"></div>
    </div>
  `;
  return card;
};

const renderCard = (theme, data) => {
  const { config } = appState;
  const isTwitter = data.platform === "Twitter";
  const lengthDisplay = data.length || "";
  const platformIcon = isTwitter ? twitterLogoSvg : youtubeLogoSvg;

  const card = document.createElement("article");
  card.className = `content-card variant-${theme} layout-${config.layout}`;
  if (config.density === "compact") card.classList.add("compact");
  card.style.setProperty("--accent", config.accent);

  const headerHTML = `
    <div class="card-header">
      <span class="platform" style="display:flex;align-items:center;gap:6px;">
        ${platformIcon}
        <span style="font-size:12px;opacity:0.8;font-weight:600;">${data.platform}</span>
      </span>
      <span class="time">${lengthDisplay}</span>
    </div>
  `;

  const titleHTML = `<h3>${data.title || "生成中..."}</h3>`;
  const summaryHTML = `<p class="summary">${data.summary || "正在解析内容..."}</p>`;

  const highlightsContent = createHighlightHTML(data.highlights);
  const showHighlights = config.highlights === "show" && highlightsContent;
  const highlightsHTML = showHighlights
    ? `<div class="highlights">${highlightsContent}</div>`
    : `<div class="highlights hidden"></div>`;

  const metaHTML = `
    <div class="meta">
      <span>Powered by MagicCard</span>
      <span>置信度：${data.confidence || "--"}</span>
    </div>
  `;

  const downloadBtnHTML = `<button class="download-btn" type="button">下载</button>`;

  card.innerHTML = `
    <div class="variant-label">${theme}</div>
    ${headerHTML}
    ${titleHTML}
    ${summaryHTML}
    ${highlightsHTML}
    ${metaHTML}
    ${downloadBtnHTML}
  `;

  const btn = card.querySelector(".download-btn");
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    downloadCard(card, btn);
  });

  card.addEventListener("click", () => {
    document.querySelectorAll(".content-card").forEach(c => c.classList.remove("is-selected"));
    card.classList.add("is-selected");
  });

  return card;
};

const renderGallery = (skeleton = false) => {
  galleryContainer.innerHTML = "";

  if (skeleton) {
    appState.config.themes.forEach(theme => {
      galleryContainer.appendChild(renderSkeletonCard(theme));
    });
    return;
  }

  const dummyData = {
    platform: "Twitter",
    length: null,
    title: "示例：AI 正在重塑软件开发的工作流",
    summary: "在这个新时代，每一个开发者的生产力都将被无限放大。我们不再是代码的搬运工，而是逻辑的编排者。",
    highlights: [
      { label: "观点", text: "AI Copilot 已经成为标配" },
      { label: "趋势", text: "自然语言编程正在兴起" }
    ],
    confidence: "98%"
  };

  const dataToRender = appState.data || dummyData;
  appState.config.themes.forEach(theme => {
    galleryContainer.appendChild(renderCard(theme, dataToRender));
  });
};

// --- Error Display ---

const showError = (message, retryable = false) => {
  const errorContainer = document.getElementById("error-panel") || createErrorPanel();
  errorContainer.classList.remove("hidden");
  errorContainer.innerHTML = `
    <div class="error-content">
      <div class="error-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/>
          <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
      </div>
      <div class="error-text">
        <strong>解析失败</strong>
        <p>${message}</p>
      </div>
      ${retryable ? '<button class="retry-btn" type="button">重试</button>' : ''}
    </div>
  `;
  if (retryable) {
    errorContainer.querySelector(".retry-btn").addEventListener("click", () => {
      errorContainer.classList.add("hidden");
      form.dispatchEvent(new Event("submit", { cancelable: true }));
    });
  }
};

const createErrorPanel = () => {
  const panel = document.createElement("div");
  panel.id = "error-panel";
  panel.className = "error-panel hidden";
  // Insert after status
  statusDOM.parentNode.insertBefore(panel, statusDOM.nextSibling);
  return panel;
};

const hideError = () => {
  const errorContainer = document.getElementById("error-panel");
  if (errorContainer) errorContainer.classList.add("hidden");
};

// --- Actions ---

const requestAiSummary = async ({ url, platform, id }) => {
  // Abort previous request if still pending
  if (appState.abortController) {
    appState.abortController.abort();
  }
  appState.abortController = new AbortController();
  const { signal } = appState.abortController;

  // Timeout
  const timeoutId = setTimeout(() => appState.abortController.abort(), REQUEST_TIMEOUT_MS);

  try {
    const apiBase = getApiBase();
    const res = await fetch(`${apiBase}/api/magic`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, platform, id }),
      signal,
    });

    const body = await res.json();

    if (!res.ok) {
      const err = new Error(body.message || body.error || "api-error");
      err.retryable = body.retryable || false;
      err.errorCode = body.error;
      throw err;
    }

    return body;
  } finally {
    clearTimeout(timeoutId);
  }
};

const parseUrl = (input) => {
  const trimmed = input.trim();
  if (!trimmed) return null;
  try {
    const url = new URL(trimmed);
    const host = url.hostname.toLowerCase();
    if (host.includes("youtube.com") || host.includes("youtu.be")) {
      return { platform: "YouTube", id: "video" };
    }
    if (host.includes("twitter.com") || host.includes("x.com")) {
      return { platform: "Twitter", id: "tweet" };
    }
  } catch (e) { return null; }
  return null;
};

const handleSubmit = async (e) => {
  e.preventDefault();
  if (appState.loading) return;

  const meta = parseUrl(urlInput.value);
  if (!meta) {
    setStatus("不支持的链接，请输入 YouTube 或 Twitter 链接", "error");
    return;
  }

  hideError();
  setLoading(true);
  setStatus("正在解析内容...", "loading");
  platformChip.textContent = meta.platform;

  // Show skeleton immediately
  outputPanel.classList.remove("hidden");
  outputPanel.classList.add("visible");
  renderGallery(true);
  outputPanel.scrollIntoView({ behavior: "smooth" });

  try {
    const result = await requestAiSummary({
      url: urlInput.value,
      platform: meta.platform,
      id: meta.id
    });

    appState.data = { platform: meta.platform, ...result };
    renderGallery();
    setStatus("生成成功", "success");

  } catch (err) {
    console.error(err);
    renderGallery(); // Show dummy data instead of broken skeletons

    if (err.name === "AbortError") {
      setStatus("请求超时，请重试", "error");
      showError("请求超时（30s），可能是网络问题或服务器繁忙。", true);
    } else {
      setStatus("解析失败", "error");
      showError(err.message || "未知错误", err.retryable !== false);
    }
  } finally {
    setLoading(false);
  }
};

const downloadCard = async (card, btn) => {
  if (typeof htmlToImage === "undefined") return;
  btn.disabled = true;
  const originalText = btn.textContent;
  btn.textContent = "导出中...";
  card.classList.add("is-capturing");

  try {
    const scale = 3;
    const blob = await htmlToImage.toBlob(card, {
      pixelRatio: scale,
      width: 520,
      style: {
        margin: '0',
        transform: 'none',
        boxShadow: 'none',
        background: 'white'
      }
    });

    const link = document.createElement("a");
    link.download = `magic-card-${Date.now()}.png`;
    link.href = URL.createObjectURL(blob);
    link.click();
  } catch (e) {
    console.error(e);
    alert("下载失败");
  } finally {
    card.classList.remove("is-capturing");
    btn.disabled = false;
    btn.textContent = originalText;
  }
};

// --- Init Listeners ---

form.addEventListener("submit", handleSubmit);

colorSwatches.forEach(swatch => {
  swatch.addEventListener("click", () => {
    colorSwatches.forEach(s => s.classList.remove("active"));
    swatch.classList.add("active");
    appState.config.accent = swatch.dataset.color;
    renderGallery();
  });
});

densitySelect.addEventListener("change", (e) => {
  appState.config.density = e.target.value;
  renderGallery();
});

highlightsSelect.addEventListener("change", (e) => {
  appState.config.highlights = e.target.value;
  renderGallery();
});

layoutSelect.addEventListener("change", (e) => {
  appState.config.layout = e.target.value;
  renderGallery();
});

document.querySelectorAll(".sample-link").forEach(btn => {
  btn.addEventListener("click", () => {
    urlInput.value = sampleUrls[btn.dataset.sample];
    setStatus("示例已填入", "info");
  });
});

// Init
renderGallery();
setStatus("", "info");
