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
const parseMode = document.getElementById("parse-mode");
const modelName = document.getElementById("model-name");
const apiKey = document.getElementById("api-key");
const accentColor = document.getElementById("accent-color");
const density = document.getElementById("density");
const showHighlights = document.getElementById("show-highlights");
const contentCard = document.getElementById("content-card");
const quickActions = document.querySelectorAll(".quick-actions button");

const sampleUrls = {
  youtube: "https://www.youtube.com/watch?v=NjYt_7R-1Dk",
  twitter: "https://twitter.com/OpenAI/status/1700000000000000000",
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
  if (!trimmed) {
    return null;
  }

  let url;
  try {
    url = new URL(trimmed);
  } catch (error) {
    return null;
  }
  if (url.hostname.includes("youtube.com") || url.hostname.includes("youtu.be")) {
    const id = url.hostname.includes("youtu.be")
      ? url.pathname.replace("/", "")
      : url.searchParams.get("v");
    return { platform: "YouTube", id };
  }

  if (url.hostname.includes("twitter.com") || url.hostname.includes("x.com")) {
    const segments = url.pathname.split("/").filter(Boolean);
    const id = segments[segments.length - 1];
    return { platform: "Twitter", id };
  }

  return null;
};

const updateCard = ({ platform, id }, detailOverride) => {
  const insights = {
    YouTube: {
      title: "3 个要点快速掌握视频核心",
      summary:
        "我们识别出视频主线与转折点，生成浓缩摘要，帮助你快速理解内容价值。",
      length: "约 4 分钟",
      highlights: [
        { label: "核心观点", text: "视频强调结构化表达能提高信息留存。" },
        { label: "关键数据", text: "平均每 45 秒提出一个关键结论。" },
        { label: "行动建议", text: "用 3 个问题引导观众理解重点。" },
      ],
    },
    Twitter: {
      title: "高互动推文的核心摘要",
      summary:
        "我们提取推文主题、情绪倾向与高频关键词，生成可复用的内容洞察。",
      length: "阅读耗时 12 秒",
      highlights: [
        { label: "主要话题", text: "讨论 AI 产品发布后的用户反馈。" },
        { label: "情绪倾向", text: "积极与期待占比超过 70%。" },
        { label: "高频词", text: "“更新”、“可用性”、“效率”。" },
      ],
    },
  };

  const detail = detailOverride || insights[platform];
  platformChip.textContent = platform;
  platformName.textContent = platform;
  contentLength.textContent = detail.length;
  cardTitle.textContent = detail.title;
  cardSummary.textContent = detail.summary;
  sourceId.textContent = `来源 ID：${id || "--"}`;
  confidence.textContent = `置信度：${detail.confidence || "92%"}`;
  buildHighlights(detail.highlights || []);
};

const requestAiSummary = async ({ url, platform, id, model, key }) => {
  const response = await fetch("/api/parse", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(key ? { Authorization: `Bearer ${key}` } : {}),
    },
    body: JSON.stringify({
      url,
      platform,
      id,
      model,
    }),
  });

  if (!response.ok) {
    throw new Error("api-request-failed");
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

const handleSubmit = async (event) => {
  event.preventDefault();
  const data = parseUrl(urlInput.value);
  if (!data || !data.id) {
    status.textContent = "暂不支持的链接，请输入有效的 YouTube 或 Twitter 链接。";
    status.style.color = "#d14343";
    return;
  }

  status.textContent = "正在解析内容...";
  status.style.color = "#4c6fff";

  if (parseMode.value === "api") {
    try {
      const result = await requestAiSummary({
        url: urlInput.value,
        platform: data.platform,
        id: data.id,
        model: modelName.value,
        key: apiKey.value,
      });
      updateCard(data, result);
      status.textContent = "AI 解析完成，已生成卡片。";
      return;
    } catch (error) {
      status.textContent =
        "AI API 暂未连接，已回退为示例解析。请配置后端服务。";
      status.style.color = "#d98324";
    }
  }

  updateCard(data);
  status.textContent = "解析完成，已生成卡片。";
};

form.addEventListener("submit", handleSubmit);
accentColor.addEventListener("input", applyCardStyles);
density.addEventListener("change", applyCardStyles);
showHighlights.addEventListener("change", applyCardStyles);

quickActions.forEach((button) => {
  button.addEventListener("click", () => {
    const sampleType = button.dataset.sample;
    urlInput.value = sampleUrls[sampleType];
    status.textContent = "示例链接已填入，可直接生成卡片。";
    status.style.color = "#4c6fff";
  });
});

applyCardStyles();
