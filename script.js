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

  const url = new URL(trimmed);
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

const updateCard = ({ platform, id }) => {
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

  const detail = insights[platform];
  platformChip.textContent = platform;
  platformName.textContent = platform;
  contentLength.textContent = detail.length;
  cardTitle.textContent = detail.title;
  cardSummary.textContent = detail.summary;
  sourceId.textContent = `来源 ID：${id || "--"}`;
  confidence.textContent = "置信度：92%";
  buildHighlights(detail.highlights);
};

const handleSubmit = (event) => {
  event.preventDefault();
  try {
    const data = parseUrl(urlInput.value);
    if (!data || !data.id) {
      status.textContent = "暂不支持的链接，请输入有效的 YouTube 或 Twitter 链接。";
      status.style.color = "#d14343";
      return;
    }

    status.textContent = "解析完成，已生成卡片。";
    status.style.color = "#4c6fff";
    updateCard(data);
  } catch (error) {
    status.textContent = "链接格式有误，请检查后重试。";
    status.style.color = "#d14343";
  }
};

form.addEventListener("submit", handleSubmit);

quickActions.forEach((button) => {
  button.addEventListener("click", () => {
    const sampleType = button.dataset.sample;
    urlInput.value = sampleUrls[sampleType];
    status.textContent = "示例链接已填入，可直接生成卡片。";
    status.style.color = "#4c6fff";
  });
});
