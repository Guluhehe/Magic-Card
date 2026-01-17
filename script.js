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

const sampleUrls = {
  youtube: "https://www.youtube.com/watch?v=NjYt_7R-1Dk",
  twitter: "https://x.com/OpenAI/status/1790432049117327631",
};

const buildHighlights = (items) => {
  cardHighlights.innerHTML = "";
  items.forEach((item) => {
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
  contentLength.textContent = detail.length || "--";
  cardTitle.textContent = detail.title || "抓取结果";
  cardSummary.textContent = detail.summary || "暂无摘要信息。";
  sourceId.textContent = `来源 ID：${id || "--"}`;
  confidence.textContent = `置信度：${detail.confidence || "92%"}`;
  buildHighlights(detail.highlights || []);

  // Trigger animation
  contentCard.style.animation = 'none';
  contentCard.offsetHeight; // trigger reflow
  contentCard.style.animation = null;
};

const getApiBase = () => {
  const host = window.location.hostname;
  const protocol = window.location.protocol;
  const isLocal =
    host === "localhost" ||
    host === "127.0.0.1" ||
    protocol === "file:";
  return isLocal ? "http://127.0.0.1:5000" : "";
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
  cardHighlights.classList.toggle("hidden", highlightMode === "hide");
};

const downloadCard = async () => {
  if (!outputPanel.classList.contains("visible")) {
    status.textContent = "请先生成卡片再下载。";
    status.style.color = "#ef4444";
    return;
  }
  if (typeof html2canvas === "undefined") {
    status.textContent = "下载组件未加载，请刷新页面再试。";
    status.style.color = "#ef4444";
    return;
  }

  downloadButton.disabled = true;
  contentCard.classList.add("is-capturing");
  try {
    const canvas = await html2canvas(contentCard, { backgroundColor: null, scale: 2 });
    const link = document.createElement("a");
    link.href = canvas.toDataURL("image/png");
    link.download = "magiccard.png";
    link.click();
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
