const API_BASE = "http://127.0.0.1:8000";

const STYLE_PROFILES = [
  { name: "通勤裸感", tags: ["通勤", "短甲", "低饱和"], price: 168, role: "引流款" },
  { name: "法式轻奢", tags: ["法式", "显白", "约会"], price: 198, role: "主推款" },
  { name: "猫眼高级感", tags: ["猫眼", "高级感", "低饱和"], price: 238, role: "高客单款" },
  { name: "亮片派对", tags: ["亮片", "派对", "长甲"], price: 268, role: "节日款" },
  { name: "粉色甜美", tags: ["粉色", "甜美", "短甲"], price: 188, role: "新客款" },
  { name: "渐变通勤", tags: ["渐变", "通勤", "简约"], price: 188, role: "日常款" },
  { name: "节日红调", tags: ["红色", "节日", "显白"], price: 218, role: "活动款" },
  { name: "黑金酷感", tags: ["黑色", "酷感", "长甲"], price: 258, role: "个性款" },
];

const state = {
  merchantId: "merchant_001",
  windowDays: 7,
  activeView: "command",
  catalog: [],
  catalogByStyleId: new Map(),
  selectedTag: "",
  featuredStyleId: "",
  dashboard: null,
  platform: null,
  strategy: null,
  campaign: null,
};

const els = {
  merchantSelect: document.querySelector("#merchantSelect"),
  windowSelect: document.querySelector("#windowSelect"),
  refreshButton: document.querySelector("#refreshButton"),
  seedButton: document.querySelector("#seedButton"),
  strategyButton: document.querySelector("#strategyButton"),
  generateCampaignButton: document.querySelector("#generateCampaignButton"),
  copyContentButton: document.querySelector("#copyContentButton"),
  assistantWidget: document.querySelector("#assistantWidget"),
  assistantFab: document.querySelector("#assistantFab"),
  assistantCloseButton: document.querySelector("#assistantCloseButton"),
  assistantQuickQuestions: document.querySelector("#assistantQuickQuestions"),
  assistantConversation: document.querySelector("#assistantConversation"),
  tabButtons: document.querySelectorAll(".tab-button"),
  pageViews: document.querySelectorAll(".page-view"),
  briefTitle: document.querySelector("#briefTitle"),
  briefCopy: document.querySelector("#briefCopy"),
  briefActions: document.querySelector("#briefActions"),
  featuredStyle: document.querySelector("#featuredStyle"),
  featuredReason: document.querySelector("#featuredReason"),
  promoteFeaturedButton: document.querySelector("#promoteFeaturedButton"),
  clickCount: document.querySelector("#clickCount"),
  clickGrowth: document.querySelector("#clickGrowth"),
  clickDetail: document.querySelector("#clickDetail"),
  tryonCount: document.querySelector("#tryonCount"),
  tryonRate: document.querySelector("#tryonRate"),
  tryonDetail: document.querySelector("#tryonDetail"),
  favoriteCount: document.querySelector("#favoriteCount"),
  favoriteRate: document.querySelector("#favoriteRate"),
  favoriteDetail: document.querySelector("#favoriteDetail"),
  conversionCount: document.querySelector("#conversionCount"),
  conversionRate: document.querySelector("#conversionRate"),
  conversionDetail: document.querySelector("#conversionDetail"),
  recordsCount: document.querySelector("#recordsCount"),
  privacyLabel: document.querySelector("#privacyLabel"),
  platformSummary: document.querySelector("#platformSummary"),
  platformInsightGrid: document.querySelector("#platformInsightGrid"),
  platformOpportunityPool: document.querySelector("#platformOpportunityPool"),
  supplyGapList: document.querySelector("#supplyGapList"),
  platformActionList: document.querySelector("#platformActionList"),
  assistantStatus: document.querySelector("#assistantStatus"),
  styleChart: document.querySelector("#styleChart"),
  tagChart: document.querySelector("#tagChart"),
  trendChart: document.querySelector("#trendChart"),
  styleOpsSummary: document.querySelector("#styleOpsSummary"),
  styleOpsList: document.querySelector("#styleOpsList"),
  campaignPlan: document.querySelector("#campaignPlan"),
  contentCopies: document.querySelector("#contentCopies"),
  platformTagTrends: document.querySelector("#platformTagTrends"),
  platformScenarioTrends: document.querySelector("#platformScenarioTrends"),
  strategyList: document.querySelector("#strategyList"),
};

async function init() {
  await loadCatalog();
  bindEvents();
  await refreshDashboard();
  renderCampaign();
}

async function loadCatalog() {
  try {
    const catalog = await fetchJson("./assets/catalog.json");
    state.catalog = (catalog.styles || []).map(enrichStyle);
    state.catalogByStyleId = new Map(state.catalog.map((style) => [style.styleId, style]));
  } catch {
    state.catalog = [];
    state.catalogByStyleId = new Map();
  }
}

function enrichStyle(style, index) {
  const profile = STYLE_PROFILES[index % STYLE_PROFILES.length];
  return {
    ...style,
    displayName: profile.name,
    tags: profile.tags,
    price: profile.price,
    role: profile.role,
    status: index % 5 === 0 ? "观察中" : "已上架",
  };
}

function bindEvents() {
  els.merchantSelect.addEventListener("change", () => {
    state.merchantId = els.merchantSelect.value;
    refreshDashboard();
  });
  els.windowSelect.addEventListener("change", () => {
    state.windowDays = Number(els.windowSelect.value);
    refreshDashboard();
  });
  els.refreshButton.addEventListener("click", refreshDashboard);
  els.seedButton.addEventListener("click", seedDemoData);
  els.strategyButton.addEventListener("click", generateStrategy);
  els.generateCampaignButton.addEventListener("click", () => {
    state.campaign = buildCampaignPlan();
    renderCampaign();
  });
  els.copyContentButton.addEventListener("click", copyContent);
  els.promoteFeaturedButton.addEventListener("click", promoteFeaturedStyle);
  els.tabButtons.forEach((button) => {
    button.addEventListener("click", () => setActiveView(button.dataset.view));
  });
  bindAssistantWidget();
}

function bindAssistantWidget() {
  let startX = 0;
  let startY = 0;
  let startLeft = 0;
  let startTop = 0;
  let pointerId = null;
  let dragged = false;

  els.assistantFab.addEventListener("pointerdown", (event) => {
    pointerId = event.pointerId;
    dragged = false;
    const rect = els.assistantWidget.getBoundingClientRect();
    startX = event.clientX;
    startY = event.clientY;
    startLeft = rect.left;
    startTop = rect.top;
    els.assistantFab.setPointerCapture(pointerId);
    els.assistantWidget.classList.add("is-dragging");
  });

  els.assistantFab.addEventListener("pointermove", (event) => {
    if (pointerId !== event.pointerId) return;
    const dx = event.clientX - startX;
    const dy = event.clientY - startY;
    dragged = dragged || Math.abs(dx) + Math.abs(dy) > 4;
    if (!dragged) return;
    const widgetRect = els.assistantWidget.getBoundingClientRect();
    els.assistantWidget.style.left = `${clamp(startLeft + dx, 12, window.innerWidth - widgetRect.width - 12)}px`;
    els.assistantWidget.style.top = `${clamp(startTop + dy, 82, window.innerHeight - 72)}px`;
  });

  els.assistantFab.addEventListener("pointerup", (event) => {
    if (pointerId !== event.pointerId) return;
    els.assistantWidget.classList.remove("is-dragging");
    els.assistantFab.releasePointerCapture(pointerId);
    pointerId = null;
    if (!dragged) els.assistantWidget.classList.toggle("is-open");
  });

  els.assistantFab.addEventListener("pointercancel", () => {
    els.assistantWidget.classList.remove("is-dragging");
    pointerId = null;
  });
  els.assistantCloseButton.addEventListener("click", () => {
    els.assistantWidget.classList.remove("is-open");
  });
  els.assistantQuickQuestions.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-question]");
    if (button) handleAssistantQuestion(button.dataset.question);
  });
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function setActiveView(view) {
  state.activeView = view || "command";
  els.tabButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === state.activeView);
  });
  els.pageViews.forEach((page) => {
    page.classList.toggle("is-active", page.id === `${state.activeView}View`);
  });
  if (state.dashboard && state.platform) {
    renderDashboard();
  }
}

async function refreshDashboard() {
  setBusy(true);
  try {
    const [dashboard, platform] = await Promise.all([
      fetchJson(
        `${API_BASE}/api/ops/merchant-dashboard?merchantId=${encodeURIComponent(
          state.merchantId
        )}&windowDays=${state.windowDays}`
      ),
      fetchJson(`${API_BASE}/api/ops/platform-trends?windowDays=${state.windowDays}`),
    ]);
    state.dashboard = dashboard;
    state.platform = platform;
    renderDashboard();
  } catch {
    renderOfflineState();
  } finally {
    setBusy(false);
  }
}

async function seedDemoData() {
  setBusy(true);
  try {
    await fetchJson(`${API_BASE}/api/ops/demo-data`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    await refreshDashboard();
  } finally {
    setBusy(false);
  }
}

async function generateStrategy() {
  setBusy(true);
  try {
    state.strategy = await fetchJson(`${API_BASE}/api/ops/strategy/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        merchantId: state.merchantId,
        windowDays: state.windowDays,
      }),
    });
    renderStrategy();
    els.assistantWidget.classList.add("is-open");
  } finally {
    setBusy(false);
  }
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok || data.ok === false) {
    throw new Error(data.message || `HTTP ${response.status}`);
  }
  return data;
}

function renderDashboard() {
  const summary = state.dashboard.summary || {};
  const styles = state.dashboard.stylePerformance || [];
  const tags = state.dashboard.tagPerformance || [];
  const trend = state.dashboard.eventTrend || [];

  setMetric(els.clickCount, summary.clickCount);
  setMetric(els.tryonCount, summary.tryonCount);
  setMetric(els.favoriteCount, summary.favoriteCount);
  setMetric(els.conversionCount, summary.conversionCount);
  setRate(els.clickGrowth, summary.clickGrowthRate, "增长");
  setRate(els.tryonRate, summary.tryonRate, "试戴率");
  setRate(els.favoriteRate, summary.favoriteRate, "收藏率");
  setRate(els.conversionRate, summary.conversionRate, "转化率");
  renderMetricDetails(summary);
  els.recordsCount.textContent = `${state.dashboard.recordsCount || 0} 条记录`;

  renderBrief(summary, styles, tags);
  renderFeaturedStyle(styles[0]);
  renderStyleOps(styles);
  renderBarChart(els.styleChart, styles, {
    labelKey: "styleId",
    valueKey: "clickCount",
    secondaryKey: "tryonCount",
    emptyText: "暂无款式数据",
  });
  renderBarChart(els.tagChart, tags, {
    labelKey: "tag",
    valueKey: "clickCount",
    secondaryKey: "tryonCount",
    emptyText: "暂无标签数据",
  });
  renderLineChart(els.trendChart, trend);
  renderPlatformTrends();
  if (!state.campaign) {
    state.campaign = buildCampaignPlan();
  }
  renderCampaign();
}

function renderBrief(summary, styles, tags) {
  const topStyle = styles[0];
  const topTag = tags[0];
  if (!topStyle) {
    els.briefTitle.textContent = "暂无足够经营样本";
    els.briefCopy.textContent = "先生成演示数据，或从用户端完成几次试戴、收藏、预约意向。";
    els.briefActions.innerHTML = `<span>建议：点击“生成演示数据”体验完整链路</span>`;
    return;
  }

  const tryonRate = formatPercent(summary.tryonRate);
  els.briefTitle.textContent = `${getStyleName(topStyle.styleId)} 适合做今日主推`;
  els.briefCopy.textContent = `近 ${state.windowDays} 天试戴率 ${tryonRate}，热门标签是 ${
    topTag?.tag || topStyle.styleTags?.[0] || "高意向款"
  }。建议把主推位、套餐入口和内容文案集中到这组风格上。`;
  els.briefActions.innerHTML = `
    <span>主推 ${getStyleName(topStyle.styleId)}</span>
    <span>放大 ${topTag?.tag || "热门"} 标签</span>
    <span>观察收藏到预约转化</span>
  `;
}

function renderFeaturedStyle(row) {
  if (!row) {
    els.featuredStyle.innerHTML = `<div class="empty-state">暂无可主推款式</div>`;
    els.promoteFeaturedButton.disabled = true;
    return;
  }
  const style = getStyle(row.styleId);
  state.featuredStyleId = state.featuredStyleId || row.styleId;
  els.promoteFeaturedButton.disabled = false;
  els.featuredReason.textContent = `试戴率 ${formatPercent(row.tryonRate)} · 点击增长 ${formatSignedPercent(
    row.clickGrowthRate
  )}`;
  els.featuredStyle.innerHTML = `
    <div class="featured-image-wrap">
      <img src="${style.image}" alt="${style.name}">
    </div>
    <div class="featured-copy">
      <strong>${style.name}</strong>
      <div class="featured-tags">${style.tags.map((tag) => `<span>${tag}</span>`).join("")}</div>
      <p>${style.role} · ¥${style.price} · 适合放在首页主推和套餐入口</p>
    </div>
    <dl class="featured-metrics">
      <div><dt>点击</dt><dd>${formatNumber(row.clickCount)}</dd></div>
      <div><dt>试戴</dt><dd>${formatNumber(row.tryonCount)}</dd></div>
      <div><dt>转化</dt><dd>${formatNumber(row.conversionCount)}</dd></div>
    </dl>
  `;
}

function promoteFeaturedStyle() {
  const row = state.dashboard?.stylePerformance?.[0];
  if (!row) return;
  state.featuredStyleId = row.styleId;
  els.featuredReason.textContent = `${getStyleName(row.styleId)} 已设为今日主推，建议同步更新店铺首屏和活动文案`;
  renderStyleOps(state.dashboard.stylePerformance || []);
  appendAssistantMessage(`已将 ${getStyleName(row.styleId)} 标记为今日主推。`, "bot");
}

function renderMetricDetails(summary) {
  renderMetricDetail(els.clickDetail, "本期点击", summary.clickCount, "上期点击", summary.previousClickCount);
  renderMetricDetail(els.tryonDetail, "本期试戴", summary.tryonCount, "试戴率", summary.tryonRate, true);
  renderMetricDetail(els.favoriteDetail, "本期收藏", summary.favoriteCount, "收藏率", summary.favoriteRate, true);
  renderMetricDetail(els.conversionDetail, "本期转化", summary.conversionCount, "转化率", summary.conversionRate, true);
}

function renderMetricDetail(element, aLabel, aValue, bLabel, bValue, isRate = false) {
  element.innerHTML = `
    <div><span>${aLabel}</span><strong>${formatNumber(aValue)}</strong></div>
    <div><span>${bLabel}</span><strong>${isRate ? formatPercent(bValue) : formatNumber(bValue)}</strong></div>
  `;
}

function renderStyleOps(styles) {
  const rows = styles.length ? styles : state.catalog.slice(0, 8).map((style) => ({ styleId: style.styleId }));
  els.styleOpsSummary.textContent = `${rows.length} 个运营款`;
  els.styleOpsList.innerHTML = rows
    .slice(0, 12)
    .map((row, index) => {
      const style = getStyle(row.styleId);
      const status = row.styleId === state.featuredStyleId ? "今日主推" : style.status;
      const score = calcOpsScore(row);
      return `
        <article class="style-ops-card">
          <img src="${style.image}" alt="${style.name}">
          <div class="style-ops-copy">
            <strong>${style.name}</strong>
            <span>${style.tags.join(" · ")}</span>
            <div class="status-row">
              <em>${status}</em>
              <em>${style.role}</em>
              <em>运营分 ${score}</em>
            </div>
          </div>
          <div class="style-ops-actions">
            <button type="button" data-action="feature" data-style-id="${row.styleId}">主推</button>
            <button type="button" data-action="campaign" data-style-id="${row.styleId}">做活动</button>
            <button type="button" data-action="observe" data-style-id="${row.styleId}">观察</button>
          </div>
        </article>
      `;
    })
    .join("");

  els.styleOpsList.querySelectorAll("button[data-action]").forEach((button) => {
    button.addEventListener("click", () => handleStyleAction(button.dataset.action, button.dataset.styleId));
  });
}

function handleStyleAction(action, styleId) {
  const styleName = getStyleName(styleId);
  if (action === "feature") {
    state.featuredStyleId = styleId;
    appendAssistantMessage(`${styleName} 已加入今日主推位。`, "bot");
  }
  if (action === "campaign") {
    state.featuredStyleId = styleId;
    state.campaign = buildCampaignPlan(styleId);
    setActiveView("content");
  }
  if (action === "observe") {
    appendAssistantMessage(`${styleName} 已标记为观察款，建议看 3 天试戴率和收藏率变化。`, "bot");
  }
  renderStyleOps(state.dashboard?.stylePerformance || []);
  renderCampaign();
}

function buildCampaignPlan(styleId = state.featuredStyleId) {
  const topStyleId = styleId || state.dashboard?.stylePerformance?.[0]?.styleId || state.catalog[0]?.styleId;
  const style = getStyle(topStyleId);
  const topTag = state.dashboard?.tagPerformance?.[0]?.tag || style.tags[0] || "显白";
  return {
    title: `${topTag}美甲试戴专场`,
    styleId: topStyleId,
    offer: `${style.name} 到店立减 20 元，双人同行第二款 8 折`,
    placement: ["店铺首页主推", "团购套餐首位", "用户端试戴推荐位"],
    target: `${topTag}偏好用户、近 7 天收藏但未预约用户`,
    copies: [
      `今天主推 ${style.name}，先 AI 试戴再决定，到店不踩雷。`,
      `${topTag}风格最近热度上升，适合拍照、约会和周末出行。`,
      `收藏 ${style.name} 的用户可领取限时试戴优惠，到店确认甲型后再开做。`,
    ],
  };
}

function renderCampaign() {
  const campaign = state.campaign || buildCampaignPlan();
  els.campaignPlan.innerHTML = `
    <article class="campaign-card">
      <strong>${campaign.title}</strong>
      <p>${campaign.offer}</p>
      <dl>
        <div><dt>主推款</dt><dd>${getStyleName(campaign.styleId)}</dd></div>
        <div><dt>目标人群</dt><dd>${campaign.target}</dd></div>
        <div><dt>投放位置</dt><dd>${campaign.placement.join("、")}</dd></div>
      </dl>
    </article>
  `;
  els.contentCopies.innerHTML = campaign.copies
    .map(
      (copy, index) => `
        <article class="copy-card">
          <span>文案 ${index + 1}</span>
          <p>${copy}</p>
        </article>
      `
    )
    .join("");
}

async function copyContent() {
  const text = (state.campaign?.copies || []).join("\n");
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    els.copyContentButton.textContent = "已复制";
    window.setTimeout(() => {
      els.copyContentButton.textContent = "复制文案";
    }, 1200);
  } catch {
    appendAssistantMessage("当前浏览器不允许直接复制，可以手动选中文案使用。", "bot");
  }
}

function renderPlatformTrends() {
  const tagTrends = (state.platform?.risingTags || []).slice(0, 8);
  const scenarioTrends = (state.platform?.risingScenarios || []).slice(0, 8);
  const policy = state.platform?.privacy || {};
  const opportunities = buildPlatformOpportunities(tagTrends, scenarioTrends);
  const gaps = buildSupplyGaps(tagTrends);
  const actions = buildPlatformActions(opportunities, gaps);
  els.privacyLabel.textContent = `至少 ${policy.minMerchantCount || 2} 个商家 / ${
    policy.minEventCount || 4
  } 次点击后展示`;
  els.platformSummary.innerHTML = `
    <div><strong>${state.platform?.recordsCount || 0}</strong><span>平台样本</span></div>
    <div><strong>${tagTrends.length}</strong><span>款式标签</span></div>
    <div><strong>${scenarioTrends.length}</strong><span>场景标签</span></div>
  `;
  renderPlatformInsights(tagTrends, scenarioTrends, opportunities, gaps);
  renderOpportunityPool(opportunities);
  renderSupplyGaps(gaps);
  renderPlatformActions(actions);
  renderTrendList(els.platformTagTrends, tagTrends, "款式标签");
  renderTrendList(els.platformScenarioTrends, scenarioTrends, "场景标签");
}

function renderPlatformInsights(tagTrends, scenarioTrends, opportunities, gaps) {
  const topTag = tagTrends[0]?.tag || "暂无";
  const topScenario = scenarioTrends[0]?.tag || "暂无";
  const hotMerchants = Math.max(...tagTrends.map((item) => item.merchantCount || 0), 0);
  const cards = [
    {
      label: "上升最快风格",
      value: topTag,
      copy: tagTrends[0] ? `点击增长 ${formatSignedPercent(tagTrends[0].clickGrowthRate)}` : "等待更多样本",
    },
    {
      label: "高潜场景",
      value: topScenario,
      copy: scenarioTrends[0] ? `${scenarioTrends[0].merchantCount} 个商家覆盖` : "等待更多样本",
    },
    {
      label: "可触达商家",
      value: hotMerchants,
      copy: "适合进入本周主推池",
    },
    {
      label: "供给缺口",
      value: gaps.length,
      copy: gaps[0] ? `优先补 ${gaps[0].tag}` : "暂未发现明显缺口",
    },
  ];
  els.platformInsightGrid.innerHTML = cards
    .map(
      (card) => `
        <article class="platform-insight-card">
          <span>${card.label}</span>
          <strong>${card.value}</strong>
          <p>${card.copy}</p>
        </article>
      `
    )
    .join("");
}

function buildPlatformOpportunities(tagTrends, scenarioTrends) {
  const scenarioNames = scenarioTrends.map((item) => item.tag).slice(0, 3);
  return tagTrends.slice(0, 6).map((item, index) => ({
    tag: item.tag,
    signal: `点击 ${formatNumber(item.clickCount)} · 增长 ${formatSignedPercent(item.clickGrowthRate)}`,
    audience: inferAudience(item.tag, scenarioNames),
    action: index < 2 ? "加入首页推荐与搜索加权" : "推送给匹配商家做上新/主推",
    risk: inferTrendRisk(item),
    merchantCount: item.merchantCount,
  }));
}

function renderOpportunityPool(opportunities) {
  if (!opportunities.length) {
    els.platformOpportunityPool.innerHTML = `<div class="empty-state">暂无可形成机会池的平台趋势</div>`;
    return;
  }
  els.platformOpportunityPool.innerHTML = opportunities
    .map(
      (item) => `
        <article class="opportunity-card">
          <div>
            <span>机会</span>
            <strong>${item.tag}</strong>
          </div>
          <p>${item.signal}</p>
          <dl>
            <div><dt>适合人群</dt><dd>${item.audience}</dd></div>
            <div><dt>平台动作</dt><dd>${item.action}</dd></div>
            <div><dt>风险提示</dt><dd>${item.risk}</dd></div>
          </dl>
        </article>
      `
    )
    .join("");
}

function buildSupplyGaps(tagTrends) {
  return tagTrends
    .filter((item) => item.clickGrowthRate >= 0.4 || item.merchantCount <= 2)
    .slice(0, 5)
    .map((item) => ({
      tag: item.tag,
      demand: item.clickGrowthRate >= 0.6 ? "高" : "中高",
      supply: item.merchantCount <= 2 ? "不足" : "偏集中",
      action: `向 ${Math.max(4, item.merchantCount * 3)} 家相似商家推送上新建议`,
    }));
}

function renderSupplyGaps(gaps) {
  if (!gaps.length) {
    els.supplyGapList.innerHTML = `<div class="empty-state">暂无明显供给缺口</div>`;
    return;
  }
  els.supplyGapList.innerHTML = gaps
    .map(
      (gap) => `
        <article class="supply-gap-card">
          <strong>${gap.tag}</strong>
          <div><span>需求热度</span><em>${gap.demand}</em></div>
          <div><span>当前供给</span><em>${gap.supply}</em></div>
          <p>${gap.action}</p>
        </article>
      `
    )
    .join("");
}

function buildPlatformActions(opportunities, gaps) {
  const top = opportunities[0];
  const gap = gaps[0];
  return [
    {
      title: "首页主推标签",
      copy: top ? `本周首页试戴入口优先露出「${top.tag}」相关款式。` : "等待趋势样本后自动生成。",
    },
    {
      title: "搜索推荐加权",
      copy: top ? `搜索“美甲试戴/显白/约会”等词时提升「${top.tag}」权重。` : "暂无可加权标签。",
    },
    {
      title: "商家上新触达",
      copy: gap ? `向商家推送「${gap.tag}」供给缺口和参考款式。` : "当前供需相对均衡。",
    },
    {
      title: "专题活动",
      copy: top ? `生成「${top.tag} AI 试戴专场」，联动用户端对比和预约。` : "等待高置信趋势。",
    },
  ];
}

function renderPlatformActions(actions) {
  els.platformActionList.innerHTML = actions
    .map(
      (action) => `
        <article class="platform-action-card">
          <strong>${action.title}</strong>
          <p>${action.copy}</p>
        </article>
      `
    )
    .join("");
}

function inferAudience(tag, scenarios) {
  if (["通勤", "低饱和", "短甲", "裸色"].includes(tag)) return "白领、新客、日常低风险用户";
  if (["法式", "显白", "约会"].includes(tag)) return "约会、拍照、周末社交用户";
  if (["亮片", "派对", "红色", "节日"].includes(tag)) return "节日、派对、活动前预约用户";
  if (["猫眼", "高级感", "黑色", "酷感"].includes(tag)) return "高客单、个性化和老客升级用户";
  return scenarios.length ? `${scenarios.join("、")} 场景用户` : "泛兴趣试戴用户";
}

function inferTrendRisk(item) {
  if ((item.merchantCount || 0) <= 2) return "供给样本偏少，建议先做小流量验证。";
  if ((item.clickGrowthRate || 0) >= 1) return "增长很快，需防止短期热点误判。";
  return "注意款式同质化，推荐差异化标题和价格带。";
}

function renderTrendList(container, trends, type) {
  if (!trends.length) {
    container.innerHTML = `<div class="empty-state">暂无满足隐私阈值的平台趋势</div>`;
    return;
  }
  const maxClick = Math.max(...trends.map((item) => item.clickCount || 0), 1);
  container.innerHTML = trends
    .map((item) => {
      const width = Math.max(8, ((item.clickCount || 0) / maxClick) * 100);
      return `
        <div class="trend-item">
          <strong>${item.tag}</strong>
          <div class="trend-meta">${type} · ${item.merchantCount} 个商家 · 增长 ${formatPercent(
        item.clickGrowthRate
      )}</div>
          <div class="trend-bar"><span style="width:${width}%"></span></div>
          <div class="trend-foot"><span>点击 ${formatNumber(item.clickCount)}</span></div>
        </div>
      `;
    })
    .join("");
}

function renderStrategy() {
  const recommendations = state.strategy?.recommendations || [];
  const ai = state.strategy?.ai || {};
  const assistant = state.strategy?.assistant || {};
  els.assistantStatus.textContent = ai.enabled ? `${ai.provider} · ${ai.channel || "dashboard"}` : "OpenClaw 本地解释模式";

  if (!recommendations.length) {
    els.strategyList.innerHTML = `<div class="empty-state">暂无策略建议</div>`;
    return;
  }

  els.strategyList.innerHTML = recommendations
    .map((item) => {
      const reasons = (item.reason || []).map((reason) => `<div>${reason}</div>`).join("");
      const risks = (item.risk || []).map((risk) => `<div>${risk}</div>`).join("");
      const explanation = item.assistantExplanation
        ? `<div class="assistant-explanation"><strong>助手解释</strong><span>${item.assistantExplanation}</span></div>`
        : "";
      const personalization = item.merchantPersonalization?.followUpQuestion
        ? `<div class="assistant-explanation"><strong>个性化追问</strong><span>${item.merchantPersonalization.followUpQuestion}</span></div>`
        : "";
      return `
        <article class="strategy-item">
          <div class="strategy-title">
            <strong>${cleanStrategyTitle(item.title)}</strong>
            <span class="confidence">${confidenceText(item.confidence)}</span>
          </div>
          <div class="strategy-meta">${actionText(item.action)} · 观察 ${
        item.expectedMetric?.primary || "clickRate"
          }</div>
          <div class="reason-list">${reasons}</div>
          <div class="risk-list">${risks}</div>
          ${explanation}
          ${personalization}
        </article>
      `;
    })
    .join("");

  if (assistant.summary) {
    appendAssistantMessage(`<strong>OpenClaw 策略助手</strong><span>${assistant.summary}</span>`, "bot");
  }
}

async function handleAssistantQuestion(type) {
  const labels = {
    compare: "本期对比",
    trend: "近期变化",
    strategy: "生成策略",
  };
  appendAssistantMessage(labels[type] || "帮我分析经营情况", "user");
  if (type === "strategy") {
    appendAssistantMessage("收到，我会基于当前窗口生成策略建议。", "bot");
    await generateStrategy();
    return;
  }
  appendAssistantMessage(type === "trend" ? buildTrendReply() : buildCompareReply(), "bot");
}

function appendAssistantMessage(content, role) {
  const message = document.createElement("div");
  message.className = `assistant-message assistant-message-${role}`;
  message.innerHTML = content;
  els.assistantConversation.appendChild(message);
  message.scrollIntoView({ block: "nearest" });
}

function buildCompareReply() {
  const summary = state.dashboard?.summary || {};
  return `
    <strong>本期 vs 上期</strong>
    <span>点击 ${formatNumber(summary.clickCount)}，环比 ${formatSignedPercent(summary.clickGrowthRate)}。</span>
    <span>试戴 ${formatNumber(summary.tryonCount)}，试戴率 ${formatPercent(summary.tryonRate)}。</span>
    <span>收藏 ${formatNumber(summary.favoriteCount)}，转化 ${formatNumber(summary.conversionCount)}。</span>
  `;
}

function buildTrendReply() {
  const trend = state.dashboard?.eventTrend || [];
  if (!trend.length) return "当前窗口内暂无可分析的每日趋势。";
  const first = trend[0];
  const last = trend[trend.length - 1];
  const clickDelta = Number(last.clickCount || 0) - Number(first.clickCount || 0);
  const tryonDelta = Number(last.tryonCount || 0) - Number(first.tryonCount || 0);
  const topStyle = state.dashboard?.stylePerformance?.[0];
  const topTag = state.dashboard?.tagPerformance?.[0];
  return `
    <strong>近期经营变化</strong>
    <span>${first.date} 到 ${last.date}，点击变化 ${formatSignedNumber(clickDelta)}，试戴变化 ${formatSignedNumber(
    tryonDelta
  )}。</span>
    <span>当前突出款式是 ${getStyleName(topStyle?.styleId)}，热门标签是 ${topTag?.tag || "暂无"}。</span>
    <span>建议优先观察点击增长和试戴率同时上升的款式。</span>
  `;
}

function renderBarChart(canvas, rows, options) {
  const ctx = setupCanvas(canvas);
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  if (!rows.length) {
    drawEmpty(ctx, width, height, options.emptyText);
    return;
  }

  const data = rows.slice(0, 8);
  const maxValue = Math.max(...data.map((item) => item[options.valueKey] || 0), 1);
  const left = 92;
  const top = 28;
  const barHeight = 22;
  const gap = 14;
  const chartWidth = width - left - 52;

  ctx.font = "13px Arial";
  ctx.textBaseline = "middle";
  data.forEach((item, index) => {
    const y = top + index * (barHeight + gap);
    const value = item[options.valueKey] || 0;
    const secondary = item[options.secondaryKey] || 0;
    const barWidth = Math.max(4, (value / maxValue) * chartWidth);
    ctx.fillStyle = "#4a4a4a";
    ctx.fillText(String(item[options.labelKey]), 14, y + barHeight / 2);
    roundRect(ctx, left, y, chartWidth, barHeight, 11, "#ffe9a3");
    roundRect(ctx, left, y, barWidth, barHeight, 11, "#ffd100");
    ctx.fillStyle = "#111";
    ctx.fillText(`${formatNumber(value)} / ${formatNumber(secondary)}`, left + Math.min(barWidth + 8, chartWidth - 84), y + barHeight / 2);
  });
}

function renderLineChart(canvas, rows) {
  const ctx = setupCanvas(canvas);
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  if (!rows.length) {
    drawEmpty(ctx, width, height, "暂无趋势数据");
    return;
  }

  const left = 44;
  const right = 24;
  const top = 26;
  const bottom = 42;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const maxValue = Math.max(...rows.flatMap((item) => [item.clickCount || 0, item.tryonCount || 0]), 1);
  drawAxis(ctx, left, top, plotWidth, plotHeight);
  drawLine(ctx, rows, "clickCount", "#ffd100", left, top, plotWidth, plotHeight, maxValue);
  drawLine(ctx, rows, "tryonCount", "#b75c00", left, top, plotWidth, plotHeight, maxValue);
  ctx.fillStyle = "#4a4a4a";
  ctx.font = "12px Arial";
  ctx.fillText("点击", left, height - 16);
  ctx.fillStyle = "#b75c00";
  ctx.fillText("试戴", left + 48, height - 16);
}

function drawLine(ctx, rows, key, color, left, top, plotWidth, plotHeight, maxValue) {
  ctx.strokeStyle = color;
  ctx.lineWidth = 3;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  rows.forEach((item, index) => {
    const x = left + (rows.length === 1 ? plotWidth / 2 : (index / (rows.length - 1)) * plotWidth);
    const y = top + plotHeight - ((item[key] || 0) / maxValue) * plotHeight;
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function drawAxis(ctx, left, top, width, height) {
  ctx.strokeStyle = "#f0d985";
  ctx.lineWidth = 1;
  ctx.strokeRect(left, top, width, height);
}

function roundRect(ctx, x, y, width, height, radius, color) {
  const safeRadius = Math.min(radius, width / 2, height / 2);
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(x + safeRadius, y);
  ctx.arcTo(x + width, y, x + width, y + height, safeRadius);
  ctx.arcTo(x + width, y + height, x, y + height, safeRadius);
  ctx.arcTo(x, y + height, x, y, safeRadius);
  ctx.arcTo(x, y, x + width, y, safeRadius);
  ctx.closePath();
  ctx.fill();
}

function setupCanvas(canvas) {
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, Math.floor(rect.width));
  canvas.height = Math.max(1, Math.floor(rect.height));
  return canvas.getContext("2d");
}

function clearCanvas(canvas, text) {
  const ctx = setupCanvas(canvas);
  drawEmpty(ctx, canvas.width, canvas.height, text);
}

function drawEmpty(ctx, width, height, text) {
  ctx.fillStyle = "#4a4a4a";
  ctx.font = "14px Arial";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, width / 2, height / 2);
  ctx.textAlign = "left";
}

function getStyle(styleId) {
  const item = state.catalogByStyleId.get(styleId) || state.catalog[0] || {};
  return {
    id: styleId || item.styleId || "",
    name: item.displayName || item.title || styleId || "未知款式",
    tags: item.tags || [],
    price: item.price || 198,
    role: item.role || "运营款",
    status: item.status || "已上架",
    image: item.stylePreviewPath || item.styleOriginalPath || item.styleEnhancedPath || "",
  };
}

function getStyleName(styleId) {
  return getStyle(styleId).name;
}

function calcOpsScore(row) {
  const click = Number(row.clickCount || 0);
  const tryon = Number(row.tryonRate || 0) * 100;
  const conversion = Number(row.conversionRate || 0) * 100;
  return Math.min(99, Math.round(click * 0.7 + tryon * 1.5 + conversion * 2));
}

function cleanStrategyTitle(title) {
  if (!title) return "运营策略建议";
  if (title.includes("主推")) return "设置试戴页主推款式";
  if (title.includes("标签")) return "围绕热门标签组织活动";
  return title;
}

function actionText(action) {
  if (!action) return "待执行";
  if (action.type === "set_featured_style") return `主推 ${getStyleName(action.styleId)} ${action.durationDays} 天`;
  if (action.type === "promote_tag") return `推广标签 ${action.tag}`;
  if (action.type === "collect_more_events") return "继续积累试戴行为";
  return action.type || "待执行";
}

function confidenceText(value) {
  return { high: "高置信", medium: "中置信", low: "低置信" }[value] || "待观察";
}

function setMetric(element, value) {
  element.textContent = formatNumber(value || 0);
}

function setRate(element, value, label) {
  element.textContent = `${label} ${formatPercent(value || 0)}`;
  element.classList.toggle("is-down", value < 0);
}

function setBusy(isBusy) {
  [els.refreshButton, els.seedButton, els.strategyButton, els.generateCampaignButton].forEach((button) => {
    button.disabled = isBusy;
  });
}

function renderOfflineState() {
  els.recordsCount.textContent = "后端未连接";
  els.briefTitle.textContent = "等待后端服务";
  els.briefCopy.textContent = "请确认 python backend\\server.py 已启动。";
  els.featuredStyle.innerHTML = `<div class="empty-state">后端未连接</div>`;
  els.styleOpsList.innerHTML = `<div class="empty-state">后端未连接</div>`;
  els.platformSummary.innerHTML = "";
  els.platformTagTrends.innerHTML = `<div class="empty-state">后端未连接</div>`;
  els.platformScenarioTrends.innerHTML = `<div class="empty-state">后端未连接</div>`;
  els.strategyList.innerHTML = `<div class="empty-state">运营助手等待后端服务</div>`;
  clearCanvas(els.styleChart, "后端未连接");
  clearCanvas(els.tagChart, "后端未连接");
  clearCanvas(els.trendChart, "后端未连接");
}

function formatNumber(value) {
  return Math.round(Number(value || 0)).toLocaleString("zh-CN");
}

function formatPercent(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function formatSignedPercent(value) {
  const number = Number(value || 0);
  return `${number >= 0 ? "+" : ""}${(number * 100).toFixed(1)}%`;
}

function formatSignedNumber(value) {
  const number = Number(value || 0);
  return `${number >= 0 ? "+" : ""}${formatNumber(number)}`;
}

init();
