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
const outputPanel = document.getElementById("output-panel"); // New
const quickActions = document.querySelectorAll(".quick-actions button");

const sampleUrls = {
  youtube: "https://www.youtube.com/watch?v=NjYt_7R-1Dk",
  twitter: "https://x.com/OpenAI/status/1790432049117327631",
};

const insightsDatabase = {
  YouTube: [
    {
      title: "GPT-4o 交互演示：AI 的未来已来",
      summary: "OpenAI 发布的 GPT-4o 展示了极低延迟的语音交互和视觉情感识别能力，标志着实时多模态 AI 进入新纪元。",
      length: "14:28",
      confidence: "98%",
      highlights: [
        { label: "核心技术", text: "模型实现了端到端的语音处理，延迟降低至 232 毫秒。" },
        { label: "交互突破", text: "AI 现在能实时感知识别用户的呼吸、语调变化及面部表情。" },
        { label: "应用场景", text: "展示了作为实时翻译官、数学助教及视障人士助手的巨大潜力。" },
      ],
    },
    {
      title: "如何利用 AI 工具实现 10 倍生产力",
      summary: "本视频深入探讨了如何整合 Cursor, Perplexity 和 Gamma 等工具，构建自动化工作流。重点在于提示词工程的实战应用。",
      length: "08:45",
      confidence: "95%",
      highlights: [
        { label: "工具链", text: "推荐使用 Cursor 进行代码补全，Perplexity 进行深度搜索。" },
        { label: "核心策略", text: "‘AI-First’ 思维，先让 AI 搭框架，人再填肉。" },
        { label: "避坑指南", text: "警惕 AI 幻觉，所有关键结论必须由人类二次验证。" },
      ],
    }
  ],
  Twitter: [
    {
      title: "OpenAI 发布 GPT-4o 总览",
      summary: "推文介绍了 GPT-4o 的全能性，它是 OpenAI 首个原生支持音频、视觉和文本实时输入的模型。",
      length: "阅读耗时 20s",
      confidence: "99%",
      highlights: [
        { label: "关键更新", text: "所有用户（包括免费版）均可获得 GPT-4 级智能。" },
        { label: "性能指标", text: "在非英语语言的处理速度和效率上有了显著提升。" },
        { label: "高频词", text: "“Omni”, “Real-time”, “Free users”。" },
      ],
    },
    {
      title: "开发者对新一代 AI 架构的讨论",
      summary: "技术社区对 Transformer 架构的最新变体展开热议，重点讨论了推理效率与长上下文窗口的平衡。",
      length: "阅读耗时 45s",
      confidence: "92%",
      highlights: [
        { label: "讨论焦点", text: "如何将上下文长度扩展到 1M 词元以上而不损失精度。" },
        { label: "技术趋势", text: "架构正从稠密模型向稀疏模型 (MoE) 全面转型。" },
        { label: "社区情绪", text: "普遍持乐观态度，但对算力成本表示担忧。" },
      ],
    }
  ],
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

const updateCard = ({ platform, id }, detailOverride) => {
  const pool = insightsDatabase[platform] || [];
  const randomSample = pool[Math.floor(Math.random() * pool.length)];
  const detail = detailOverride || randomSample;

  platformChip.textContent = platform;
  platformName.textContent = platform;
  contentLength.textContent = detail.length || "--";
  cardTitle.textContent = detail.title;
  cardSummary.textContent = detail.summary;
  sourceId.textContent = `来源 ID：${id || "--"}`;
  confidence.textContent = `置信度：${detail.confidence || "92%"}`;
  buildHighlights(detail.highlights || []);

  // Trigger animation
  contentCard.style.animation = 'none';
  contentCard.offsetHeight; // trigger reflow
  contentCard.style.animation = null;
};

const requestAiSummary = async ({ url, platform, id, model, key }) => {
  // Point to our local Phase 2 Python Backend
  const response = await fetch("http://127.0.0.1:5000/api/parse", {
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

const handleSubmit = async (event) => {
  event.preventDefault();
  const data = parseUrl(urlInput.value);
  if (!data || !data.id) {
    status.textContent = "暂不支持的链接，请输入有效的 YouTube 或 Twitter/X 链接。";
    status.style.color = "#ef4444";
    return;
  }

  status.textContent = "正在通过后端引擎提取内容 (Phase 2 Real Extract)...";
  status.style.color = "var(--primary)";

  const targetMode = parseMode.value;

  if (targetMode === "api") {
    try {
      const result = await requestAiSummary({
        url: urlInput.value,
        platform: data.platform,
        id: data.id,
      });
      updateCard(data, result);
      status.textContent = "✨ 原始内容抓取成功！AI 已就绪（已连接真实后端）。";
      outputPanel.classList.remove("hidden");
      outputPanel.classList.add("visible");
      outputPanel.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    } catch (error) {
      console.error(error);
      status.textContent = `⚠️ 内容提取失败: ${error.message}。已回退至演示模式。`;
      status.style.color = "#f59e0b";
      await new Promise(r => setTimeout(r, 2000));
    }
  }

  updateCard(data);
  status.textContent = "✨ 解析成功！卡片已魔法生成 (展示模式)。";
  outputPanel.classList.remove("hidden");
  outputPanel.classList.add("visible");
  outputPanel.scrollIntoView({ behavior: "smooth", block: "start" });
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
