const form = document.getElementById("parser-form");
const urlInput = document.getElementById("url-input");
const status = document.getElementById("status");
const platformChip = document.getElementById("platform-chip");
const platformName = document.getElementById("platform-name");
const contentLength = document.getElementById("content-length");
const cardTitle = document.getElementById("card-title");
const cardSummary = document.getElementById("card-summary");
const cardHighlights = document.getElementById("card-highlights");
const sourceId = document.getElementById("source-id");
const confidence = document.getElementById("confidence");
const accentColor = document.getElementById("accent-color");
const density = document.getElementById("density");
const showHighlights = document.getElementById("show-highlights");
const contentCard = document.getElementById("content-card");
const outputPanel = document.getElementById("output-panel"); // New
const downloadButton = document.getElementById("download-card");
const quickActions = document.querySelectorAll(".quick-actions button");

const twitterLogoSvg = `
  <svg class="platform-logo" viewBox="0 0 24 24" role="img" aria-label="Twitter">
    <path fill="currentColor" d="M23.954 4.569c-.885.389-1.83.654-2.825.775 1.014-.611 1.794-1.574 2.163-2.723-.951.555-2.005.959-3.127 1.184-.897-.94-2.178-1.528-3.594-1.528-3.179 0-5.515 2.966-4.797 6.045-4.091-.205-7.719-2.165-10.148-5.144-1.29 2.213-.669 5.108 1.523 6.574-.806-.026-1.566-.247-2.229-.616-.054 2.281 1.581 4.415 3.949 4.89-.693.188-1.452.232-2.224.084.626 1.956 2.444 3.379 4.6 3.419-2.07 1.623-4.678 2.348-7.29 2.04 2.179 1.394 4.768 2.209 7.557 2.209 9.142 0 14.307-7.721 13.995-14.646.962-.695 1.797-1.562 2.457-2.549z"/>
  </svg>
`;

const sampleUrls = {
  youtube: "https://www.youtube.com/watch?v=NjYt_7R-1Dk",
  twitter: "https://x.com/OpenAI/status/1790432049117327631",
};

const buildHighlights = (items) => {
  cardHighlights.innerHTML = "";
  const safeItems = Array.isArray(items) ? items : [];
  if (!safeItems.length) {
    cardHighlights.dataset.empty = "true";
    return;
  }
  cardHighlights.dataset.empty = "false";
  safeItems.forEach((item) => {
    const wrapper = document.createElement("div");
    wrapper.className = "highlight";
    const label = document.createElement("span");
    label.textContent = item.label;
    const text = document.createElement("div");
    text.textContent = item.text;
    wrapper.append(label, text);
    cardHighlights.appendChild(wrapper);
  });
};

const parseUrl = (input) => {
  const trimmed = input.trim();
  if (!trimmed) return null;

  try {
    const url = new URL(trimmed);
    const host = url.hostname.toLowerCase();

    // YouTube
    if (host.includes("youtube.com") || host.includes("youtu.be")) {
      let id = "";
      if (host.includes("youtu.be")) {
        id = url.pathname.slice(1);
      } else if (url.pathname.includes("/shorts/")) {
        id = url.pathname.split("/").pop();
      } else {
        id = url.searchParams.get("v");
      }
      return { platform: "YouTube", id };
    }

    // Twitter / X
    if (host.includes("twitter.com") || host.includes("x.com")) {
      const segments = url.pathname.split("/").filter(Boolean);
      const id = segments[segments.length - 1];
      return { platform: "Twitter", id };
    }
  } catch (e) {
    return null;
  }
  return null;
};

const updateCard = ({ platform, id }, detail = {}) => {
  if (!detail) return;

  platformChip.textContent = platform;
  platformName.textContent = platform;
  if (platform === "Twitter") {
    contentLength.innerHTML = twitterLogoSvg;
    contentLength.classList.add("is-logo");
    contentLength.setAttribute("aria-label", "Twitter");
  } else {
    contentLength.textContent = detail.length || "--";
    contentLength.classList.remove("is-logo");
    contentLength.removeAttribute("aria-label");
  }
  cardTitle.textContent = detail.title || "抓取结果";
  cardSummary.textContent = detail.summary || "暂无摘要信息。";
  sourceId.textContent = "Powered by MagicCard";
  confidence.textContent = `置信度：${detail.confidence || "92%"}`;
  buildHighlights(detail.highlights || []);

  // Trigger animation
  contentCard.style.animation = 'none';
  contentCard.offsetHeight; // trigger reflow
  contentCard.style.animation = null;
};

const getApiBase = () => {
  const metaBase = document
    .querySelector('meta[name="magiccard-api-base"]')
    ?.getAttribute("content")
    ?.trim();
  const windowBase = (window.MAGICCARD_API_BASE || "").trim();
  if (windowBase) return windowBase;
  if (metaBase) return metaBase;

  // Check if running locally
  const host = window.location.hostname;
  const protocol = window.location.protocol;
  const isLocal =
    host === "localhost" ||
    host === "127.0.0.1" ||
    protocol === "file:";

  // Use local backend for development, Render for production
  return isLocal ? "http://127.0.0.1:5000" : "https://magic-card-3p5l.onrender.com";
};

const requestAiSummary = async ({ url, platform, id }) => {
  const apiBase = getApiBase();
  const response = await fetch(`${apiBase}/api/parse`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      url,
      platform,
      id,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.message || "api-request-failed");
  }

  return response.json();
};

const applyCardStyles = () => {
  const chosenAccent = accentColor.value;
  const densityValue = density.value;
  const highlightMode = showHighlights.value;

  contentCard.style.setProperty("--accent", chosenAccent);
  contentCard.classList.toggle("compact", densityValue === "compact");
  const isEmpty = cardHighlights.dataset.empty === "true";
  cardHighlights.classList.toggle("hidden", highlightMode === "hide" || isEmpty);
};

const downloadCard = async () => {
  if (!outputPanel.classList.contains("visible")) {
    status.textContent = "请先生成卡片再下载。";
    status.style.color = "#ef4444";
    return;
  }
  if (typeof htmlToImage === "undefined") {
    status.textContent = "下载组件未加载，请刷新页面再试。";
    status.style.color = "#ef4444";
    return;
  }

  downloadButton.disabled = true;
  contentCard.classList.add("is-capturing");
  try {
    if (document.fonts && document.fonts.ready) {
      await document.fonts.ready;
    }
    const pixelRatio = Math.min(4, Math.max(2, window.devicePixelRatio * 2));
    const blob = await htmlToImage.toBlob(contentCard, {
      backgroundColor: null,
      cacheBust: true,
      pixelRatio,
    });
    if (!blob) {
      throw new Error("download-blob-empty");
    }
    const link = document.createElement("a");
    const objectUrl = URL.createObjectURL(blob);
    link.href = objectUrl;
    link.download = "magiccard.png";
    link.click();
    URL.revokeObjectURL(objectUrl);
  } catch (error) {
    console.error(error);
    status.textContent = "⚠️ 下载失败，请重试。";
    status.style.color = "#ef4444";
  } finally {
    contentCard.classList.remove("is-capturing");
    downloadButton.disabled = false;
  }
};

const handleSubmit = async (event) => {
  event.preventDefault();
  const data = parseUrl(urlInput.value);
  if (!data || !data.id) {
    status.textContent = "暂不支持的链接，请输入有效的 YouTube 或 Twitter/X 链接。";
    status.style.color = "#ef4444";
    downloadButton.disabled = true;
    return;
  }

  status.textContent = "正在抓取内容，请稍候...";
  status.style.color = "var(--primary)";

  try {
    const result = await requestAiSummary({
      url: urlInput.value,
      platform: data.platform,
      id: data.id,
    });
    updateCard(data, result);
    applyCardStyles();
    status.textContent = "✨ 抓取成功！卡片已生成。";
    outputPanel.classList.remove("hidden");
    outputPanel.classList.add("visible");
    outputPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    downloadButton.disabled = false;
  } catch (error) {
    console.error(error);
    status.textContent = `⚠️ 抓取失败: ${error.message}。`;
    status.style.color = "#ef4444";
    outputPanel.classList.add("hidden");
    outputPanel.classList.remove("visible");
    downloadButton.disabled = true;
  }
};

form.addEventListener("submit", handleSubmit);
accentColor.addEventListener("input", applyCardStyles);
density.addEventListener("change", applyCardStyles);
showHighlights.addEventListener("change", applyCardStyles);
downloadButton.addEventListener("click", downloadCard);

quickActions.forEach((button) => {
  button.addEventListener("click", () => {
    const sampleType = button.dataset.sample;
    urlInput.value = sampleUrls[sampleType];
    status.textContent = "示例链接已填入，可直接生成卡片。";
    status.style.color = "#4c6fff";
  });
});

applyCardStyles();
downloadButton.disabled = true;
