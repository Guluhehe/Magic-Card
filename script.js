const form = document.getElementById("parser-form");
const urlInput = document.getElementById("url-input");
const statusDOM = document.getElementById("status");
const platformChip = document.getElementById("platform-chip");
const outputPanel = document.getElementById("output-panel");
const galleryContainer = document.getElementById("card-gallery");

// Controls
const colorSwatches = document.querySelectorAll(".color-swatch");
const densitySelect = document.getElementById("density");
const highlightsSelect = document.getElementById("show-highlights");
const layoutSelect = document.getElementById("layout-mode");
const downloadButtons = []; // Will be populated dynamically

// State
let appState = {
  data: null,
  config: {
    accent: "#0fbfba",
    density: "normal",
    highlights: "show", // show | hide
    layout: "standard", // standard | quote | minimal
    themes: ["nebula", "circuit", "prism"]
  }
};

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

const setStatus = (message, color, visible = true) => {
  statusDOM.textContent = message || "";
  if (color) {
    statusDOM.style.color = color;
  }
  statusDOM.classList.toggle("hidden", !visible);
};

const getApiBase = () => {
  const metaBase = document.querySelector('meta[name="magiccard-api-base"]')?.getAttribute("content")?.trim();
  const windowBase = (window.MAGICCARD_API_BASE || "").trim();
  if (windowBase) return windowBase;
  if (metaBase) return metaBase;
  const host = window.location.hostname;
  return (host === "localhost" || host === "127.0.0.1") ? "http://127.0.0.1:5000" : "";
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

const renderCard = (theme, data) => {
  const { config } = appState;
  const isTwitter = data.platform === "Twitter";
  const lengthDisplay = data.length || ""; // Just text

  // Choose Icon
  const platformIcon = isTwitter ? twitterLogoSvg : youtubeLogoSvg;

  const card = document.createElement("article");
  card.className = `content-card variant-${theme} layout-${config.layout}`;
  if (config.density === "compact") card.classList.add("compact");

  // Set accent color
  card.style.setProperty("--accent", config.accent);

  // Conditionally render parts based on Layout
  let contentHTML = "";

  // Common Elements
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

  // Assemble based on Layout
  // Currently, we use CSS to reorder, so DOM order can stay mostly consistent.
  // However, for "Quote" layout, we might want to swap summary and title if we were doing it purely in DOM,
  // but CSS Flexbox `order` is often enough. 
  // Let's stick to a standard DOM and let CSS handle the display variations.

  contentHTML = `
    <div class="variant-label">${theme}</div>
    ${headerHTML}
    ${titleHTML}
    ${summaryHTML}
    ${highlightsHTML}
    ${metaHTML}
    ${downloadBtnHTML}
  `;

  card.innerHTML = contentHTML;

  // Attach Event Listeners
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

const renderGallery = () => {
  galleryContainer.innerHTML = "";

  // If no data, render placeholder state (optional, or just keep the empty state handled by initial HTML if we hadn't cleared it)
  // But here we want to render specifically *with* the current configuration.

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
    const cardNode = renderCard(theme, dataToRender);
    galleryContainer.appendChild(cardNode);
  });
};

// --- Actions ---

const requestAiSummary = async ({ url, platform, id }) => {
  const apiBase = getApiBase();
  const res = await fetch(`${apiBase}/api/magic`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, platform, id }),
  });
  if (!res.ok) throw new Error((await res.json()).message || "api-error");
  return res.json();
};

const parseUrl = (input) => {
  const trimmed = input.trim();
  if (!trimmed) return null;
  try {
    const url = new URL(trimmed);
    const host = url.hostname.toLowerCase();
    if (host.includes("youtube.com") || host.includes("youtu.be")) {
      return { platform: "YouTube", id: "video" }; // ID logic simplified for checking
    }
    if (host.includes("twitter.com") || host.includes("x.com")) {
      return { platform: "Twitter", id: "tweet" };
    }
  } catch (e) { return null; }
  return null;
};

const handleSubmit = async (e) => {
  e.preventDefault();
  const meta = parseUrl(urlInput.value);
  if (!meta) {
    setStatus("不支持的链接", "#ef4444");
    return;
  }

  setStatus("正在解析...", "var(--primary)");

  // Show gallery immediately with loading state (or dummy data)
  // For now we keep using dummy data or previous data? 
  // Let's reset data to null to show "loading" effect if we had a skeleton.
  // appState.data = null; 
  // renderGallery();

  try {
    const result = await requestAiSummary({
      url: urlInput.value,
      platform: meta.platform,
      id: meta.id
    });

    appState.data = {
      platform: meta.platform,
      ...result
    };

    renderGallery();
    setStatus("生成成功", "#087c78");
    outputPanel.classList.remove("hidden");
    outputPanel.classList.add("visible");
    outputPanel.scrollIntoView({ behavior: "smooth" });

  } catch (err) {
    console.error(err);
    setStatus("生成失败", "#ef4444");
  }
};

const downloadCard = async (card, btn) => {
  if (typeof htmlToImage === "undefined") return;
  btn.disabled = true;
  card.classList.add("is-capturing");

  try {
    // Enforce specific width for capture to prevent layout shifts on mobile/narrow screens
    const scale = 3;
    const blob = await htmlToImage.toBlob(card, {
      pixelRatio: scale,
      width: 520, // Enforce desktop-like width for the image
      style: {
        margin: '0',
        transform: 'none', // Reset any hover transforms
        boxShadow: 'none', // Optional: clean up shadow if desired in image
        background: 'white' // Ensure background is opaque if transparent
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
  }
};

// --- Init Listeners ---

form.addEventListener("submit", handleSubmit);

// Color Swatches
colorSwatches.forEach(swatch => {
  swatch.addEventListener("click", () => {
    colorSwatches.forEach(s => s.classList.remove("active"));
    swatch.classList.add("active");
    appState.config.accent = swatch.dataset.color;
    renderGallery();
  });
});

// Selects
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

// Quick Actions
document.querySelectorAll(".sample-link").forEach(btn => {
  btn.addEventListener("click", () => {
    urlInput.value = sampleUrls[btn.dataset.sample];
    setStatus("示例已填入", "#087c78");
  });
});

// Init
renderGallery();
setStatus("", "", false);
