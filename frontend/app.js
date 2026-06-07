const API_BASE = "http://127.0.0.1:8000";
const MERCHANT_STYLE_TAGS_KEY = "merchantStyleTags";
const TRYON_UPLOAD_MAX_SIDE = 1536;
const TRYON_UPLOAD_JPEG_QUALITY = 0.9;
const TRYON_CROP_PADDING_RATIO = 0.16;

const STYLE_PRESETS = [
  {
    filter: "daily",
    name: "通勤裸感",
    tags: ["通勤", "短甲", "低饱和"],
    price: 168,
    duration: "75 分钟",
    scene: "上班、面试、日常约会",
    reason: "颜色干净耐看，适合第一次尝试 AI 试戴的用户。",
  },
  {
    filter: "french",
    name: "法式轻奢",
    tags: ["法式", "显白", "约会"],
    price: 198,
    duration: "90 分钟",
    scene: "约会、旅行、拍照",
    reason: "边缘线条清爽，试戴后很容易判断手型适配度。",
  },
  {
    filter: "luxury",
    name: "猫眼高级感",
    tags: ["猫眼", "高级感", "低饱和"],
    price: 238,
    duration: "100 分钟",
    scene: "聚会、轻奢套餐、老客升级",
    reason: "光泽变化明显，适合展示 AI 对材质和光感的迁移。",
  },
  {
    filter: "party",
    name: "亮片派对",
    tags: ["亮片", "派对", "长甲"],
    price: 268,
    duration: "110 分钟",
    scene: "节日、派对、演出",
    reason: "视觉冲击强，适合黑客松现场演示前后对比。",
  },
  {
    filter: "sweet",
    name: "粉色甜美",
    tags: ["粉色", "甜美", "短甲"],
    price: 188,
    duration: "80 分钟",
    scene: "学生、约会、日常自拍",
    reason: "风格明确，便于用户快速表达偏好。",
  },
  {
    filter: "daily",
    name: "渐变通勤",
    tags: ["渐变", "通勤", "简约"],
    price: 188,
    duration: "85 分钟",
    scene: "办公室、日常、低调精致",
    reason: "过渡柔和，适合展示自然融合效果。",
  },
  {
    filter: "party",
    name: "节日红调",
    tags: ["红色", "节日", "显白"],
    price: 218,
    duration: "95 分钟",
    scene: "节日、聚会、喜庆场景",
    reason: "高饱和款式更容易形成明确的试戴记忆点。",
  },
  {
    filter: "luxury",
    name: "黑金酷感",
    tags: ["黑色", "酷感", "长甲"],
    price: 258,
    duration: "105 分钟",
    scene: "派对、个性写真、夜间约会",
    reason: "适合强调个性化推荐和商家主推款包装。",
  },
];

const COMPARE_DIMENSIONS = [
  {
    key: "sceneFit",
    label: "场景适配",
    better: "更贴近本次使用场景",
  },
  {
    key: "handEffect",
    label: "显手效果",
    better: "更显手长或显白",
  },
  {
    key: "dailyWear",
    label: "日常耐看",
    better: "更适合长期保留",
  },
  {
    key: "photoImpact",
    label: "拍照吸睛",
    better: "更适合出片和社交展示",
  },
  {
    key: "costEfficiency",
    label: "性价比",
    better: "价格和效果更均衡",
  },
];

const state = {
  catalog: [],
  filteredCatalog: [],
  selectedStyle: null,
  activeFilter: "all",
  handImageUrl: "",
  handImageDataUrl: "",
  currentResult: null,
  lastAiError: "",
  history: [],
  compareItems: [],
  merchantStyleTags: {},
  favorites: loadStorage("tryonFavorites", []),
  progressTimer: null,
  progressValue: 0,
  sessionId:
    window.crypto && crypto.randomUUID
      ? crypto.randomUUID()
      : `local-${Date.now()}-${Math.random().toString(16).slice(2)}`,
};

const els = {
  handUpload: document.querySelector("#handUpload"),
  handPreview: document.querySelector("#handPreview"),
  emptyHand: document.querySelector("#emptyHand"),
  emptyResult: document.querySelector("#emptyResult"),
  resultCanvas: document.querySelector("#resultCanvas"),
  aiResultImage: document.querySelector("#aiResultImage"),
  styleList: document.querySelector("#styleList"),
  styleCount: document.querySelector("#styleCount"),
  statusText: document.querySelector("#statusText"),
  selectedStyleLabel: document.querySelector("#selectedStyleLabel"),
  useDemoButton: document.querySelector("#useDemoButton"),
  exportEventsButton: document.querySelector("#exportEventsButton"),
  progressOverlay: document.querySelector("#progressOverlay"),
  progressLabel: document.querySelector("#progressLabel"),
  progressValue: document.querySelector("#progressValue"),
  progressBar: document.querySelector("#progressBar"),
  historyList: document.querySelector("#historyList"),
  historyCount: document.querySelector("#historyCount"),
  emptyHistory: document.querySelector("#emptyHistory"),
  filterButtons: document.querySelectorAll(".filter-chip"),
  favoriteCount: document.querySelector("#favoriteCount"),
  favoriteButton: document.querySelector("#favoriteButton"),
  compareButton: document.querySelector("#compareButton"),
  appointmentButton: document.querySelector("#appointmentButton"),
  clearCompareButton: document.querySelector("#clearCompareButton"),
  openCompareDialogButton: document.querySelector("#openCompareDialogButton"),
  compareList: document.querySelector("#compareList"),
  emptyCompare: document.querySelector("#emptyCompare"),
  compareInsightHint: document.querySelector("#compareInsightHint"),
  compareInsightBody: document.querySelector("#compareInsightBody"),
  compareDialog: document.querySelector("#compareDialog"),
  compareDialogHint: document.querySelector("#compareDialogHint"),
  compareDialogBody: document.querySelector("#compareDialogBody"),
  compareDialogCloseButton: document.querySelector("#compareDialogCloseButton"),
  styleDetailBody: document.querySelector("#styleDetailBody"),
  detailHint: document.querySelector("#detailHint"),
  appointmentDialog: document.querySelector("#appointmentDialog"),
  appointmentForm: document.querySelector("#appointmentForm"),
  appointmentStyleLabel: document.querySelector("#appointmentStyleLabel"),
  appointmentCloseButton: document.querySelector("#appointmentCloseButton"),
  appointmentCancelButton: document.querySelector("#appointmentCancelButton"),
  shopSelect: document.querySelector("#shopSelect"),
  timeSelect: document.querySelector("#timeSelect"),
  phoneInput: document.querySelector("#phoneInput"),
};

async function init() {
  const payload = window.NAIL_TRYON_CATALOG || (await loadCatalogFromJson());
  state.catalog = (payload.styles || []).map(enrichStyle);
  state.merchantStyleTags = await loadMerchantStyleTags();
  state.filteredCatalog = state.catalog;
  els.styleCount.textContent = `${state.catalog.length} 款`;
  bindEvents();
  renderStyleList();
  renderHistory();
  renderCompareList();
  renderFavoriteState();
  if (state.catalog[0]) {
    setDemoHand(state.catalog[0].handPath);
  }
}

async function loadCatalogFromJson() {
  const response = await fetch("./assets/catalog.json");
  return response.json();
}

function enrichStyle(style, index) {
  const preset = STYLE_PRESETS[index % STYLE_PRESETS.length];
  return {
    ...style,
    title: preset.name,
    subtitle: preset.scene,
    filter: preset.filter,
    tags: preset.tags,
    price: preset.price,
    duration: preset.duration,
    scene: preset.scene,
    reason: preset.reason,
    popularity: 96 - ((index * 7) % 34),
  };
}

function bindEvents() {
  els.handUpload.addEventListener("change", onUpload);
  els.useDemoButton.addEventListener("click", useDemoHand);
  els.exportEventsButton.addEventListener("click", exportEvents);
  els.favoriteButton.addEventListener("click", toggleCurrentFavorite);
  els.compareButton.addEventListener("click", addCurrentToCompare);
  els.appointmentButton.addEventListener("click", openAppointmentDialog);
  els.clearCompareButton.addEventListener("click", clearCompare);
  els.openCompareDialogButton.addEventListener("click", openCompareDialog);
  els.compareDialogCloseButton.addEventListener("click", closeCompareDialog);
  els.appointmentCloseButton.addEventListener("click", closeAppointmentDialog);
  els.appointmentCancelButton.addEventListener("click", closeAppointmentDialog);
  els.appointmentForm.addEventListener("submit", submitAppointment);
  els.filterButtons.forEach((button) => {
    button.addEventListener("click", () => setFilter(button.dataset.filter));
  });
}

function renderStyleList() {
  els.styleList.innerHTML = "";
  state.filteredCatalog.forEach((style) => {
    const userTags = state.merchantStyleTags[style.styleId] || {};
    const visibleTags = [
      userTags.featuredLabel ? `<span class="style-user-tag is-featured">${userTags.featuredLabel}</span>` : "",
      userTags.promotionLabel ? `<span class="style-user-tag is-promotion">${userTags.promotionLabel}</span>` : "",
    ].join("");
    const offer = userTags.promotionOffer ? `<div class="style-offer">${userTags.promotionOffer}</div>` : "";
    const button = document.createElement("button");
    button.className = "style-card";
    button.type = "button";
    button.dataset.styleId = style.styleId;
    const previewPath = style.stylePreviewPath || style.styleOriginalPath || style.styleEnhancedPath;
    button.innerHTML = `
      <img class="style-thumb" src="${previewPath}" alt="${style.title}">
      <div class="style-meta">
        <div>
          <div class="style-title">${style.title}</div>
          <div class="style-subtitle">${style.tags.join(" · ")}</div>
        </div>
        <span class="style-badge">¥${style.price}</span>
      </div>
      ${visibleTags ? `<div class="style-user-tags">${visibleTags}</div>` : ""}
      ${offer}
      <div class="style-card-foot">
        <span>${style.duration}</span>
        <strong>${style.popularity} 热度</strong>
      </div>
    `;
    button.addEventListener("click", () => selectStyle(style));
    els.styleList.appendChild(button);
  });
  highlightSelectedCard();
}

async function loadMerchantStyleTags() {
  try {
    const response = await fetch(`${API_BASE}/api/ops/style-tags?merchantId=merchant_001`);
    const data = await response.json();
    if (response.ok && data.ok !== false) {
      saveLocalMerchantStyleTags(data.styles || {});
      return data.styles || {};
    }
  } catch {
    // Static file usage falls back to localStorage tags set by the merchant page.
  }
  return loadLocalMerchantStyleTags();
}

function loadLocalMerchantStyleTags() {
  try {
    const all = JSON.parse(localStorage.getItem(MERCHANT_STYLE_TAGS_KEY) || "{}");
    return all.merchant_001?.styles || {};
  } catch {
    return {};
  }
}

function saveLocalMerchantStyleTags(styles) {
  try {
    const all = JSON.parse(localStorage.getItem(MERCHANT_STYLE_TAGS_KEY) || "{}");
    all.merchant_001 = {
      styles,
      updatedAt: new Date().toISOString(),
    };
    localStorage.setItem(MERCHANT_STYLE_TAGS_KEY, JSON.stringify(all));
  } catch {
    // localStorage may be unavailable in hardened browser modes.
  }
}

function setFilter(filter) {
  state.activeFilter = filter || "all";
  state.filteredCatalog =
    state.activeFilter === "all"
      ? state.catalog
      : state.catalog.filter((style) => style.filter === state.activeFilter);
  els.filterButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.filter === state.activeFilter);
  });
  els.styleCount.textContent = `${state.filteredCatalog.length} 款`;
  renderStyleList();
  recordEvent("style_filter", { filter: state.activeFilter });
}

function setDemoHand(path) {
  if (!path) return;
  state.handImageUrl = path;
  state.handImageDataUrl = "";
  els.handPreview.src = path;
  els.emptyHand.classList.add("is-hidden");
  els.statusText.textContent = "已载入示例手图，可以直接选择款式生成试戴效果";
}

function useDemoHand() {
  const demo = state.selectedStyle?.handPath
    ? state.selectedStyle
    : state.catalog.find((item) => item.handPath) || state.catalog[0];
  if (demo) {
    setDemoHand(demo.handPath);
    recordEvent("demo_hand_selected", { styleId: demo.styleId });
  }
}

function selectStyle(style) {
  state.selectedStyle = style;
  els.selectedStyleLabel.textContent = `${style.title} · ${style.styleId}`;
  renderStyleDetail(style);
  highlightSelectedCard();
  recordEvent("style_click", pickStyleEvent(style));
  renderFusion(style);
}

function highlightSelectedCard() {
  document.querySelectorAll(".style-card").forEach((card) => {
    card.classList.toggle("is-active", card.dataset.styleId === state.selectedStyle?.styleId);
  });
}

function renderStyleDetail(style) {
  els.detailHint.textContent = style.styleId;
  els.styleDetailBody.innerHTML = `
    <img src="${style.stylePreviewPath || style.styleOriginalPath}" alt="${style.title}">
    <div class="detail-title-row">
      <strong>${style.title}</strong>
      <span>¥${style.price}</span>
    </div>
    <div class="detail-tags">
      ${style.tags.map((tag) => `<span>${tag}</span>`).join("")}
    </div>
    <dl>
      <div><dt>适合场景</dt><dd>${style.scene}</dd></div>
      <div><dt>预计耗时</dt><dd>${style.duration}</dd></div>
      <div><dt>推荐理由</dt><dd>${style.reason}</dd></div>
    </dl>
  `;
}

function onUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  if (state.handImageUrl.startsWith("blob:")) {
    URL.revokeObjectURL(state.handImageUrl);
  }
  state.handImageUrl = URL.createObjectURL(file);
  state.handImageDataUrl = "";
  els.handPreview.src = state.handImageUrl;
  els.emptyHand.classList.add("is-hidden");
  els.statusText.textContent = "手图已上传，选择款式即可生成 AI 试戴效果";
  recordEvent("hand_upload", {
    fileName: file.name,
    fileSize: file.size,
    fileType: file.type,
  });
  if (state.selectedStyle) {
    renderFusion(state.selectedStyle);
  }
}

async function getHandImageDataUrl() {
  if (state.handImageDataUrl) return state.handImageDataUrl;
  if (!els.handUpload.files || !els.handUpload.files[0]) return "";
  state.handImageDataUrl = await fileToOptimizedDataUrl(els.handUpload.files[0]);
  return state.handImageDataUrl;
}

async function fileToOptimizedDataUrl(file) {
  const originalDataUrl = await fileToDataUrl(file);
  const image = await loadImage(originalDataUrl);
  const scale = Math.min(1, TRYON_UPLOAD_MAX_SIDE / Math.max(image.naturalWidth, image.naturalHeight));
  if (scale >= 1 && file.type === "image/jpeg") {
    return originalDataUrl;
  }

  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
  canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
  const ctx = canvas.getContext("2d");
  ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", TRYON_UPLOAD_JPEG_QUALITY);
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function loadImage(src) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = src;
  });
}

async function loadImageForCanvas(src) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = src;
  });
}

async function renderFusion(style) {
  if (!state.handImageUrl) {
    els.statusText.textContent = "请先上传手部照片";
    return;
  }

  setResultActions(false);
  startProgress("正在生成试戴效果");
  els.statusText.textContent = "正在生成试戴效果，请稍等";

  try {
    const aiResult = await requestAiTryon(style);
    if (aiResult) {
      showAiResult(aiResult, style);
      completeProgress("AI 试戴已完成");
      return;
    }

    await renderLocalCanvasPreview(style);
    completeProgress("本地预览已完成");
  } catch {
    await renderLocalCanvasPreview(style);
    completeProgress("本地预览已完成");
  }
}

async function renderLocalCanvasPreview(style) {
  const canvas = els.resultCanvas;
  const ctx = canvas.getContext("2d");
  const [hand, styleImage] = await Promise.all([
    loadImage(state.handImageUrl),
    loadImage(style.stylePreviewPath || style.styleOriginalPath || style.styleEnhancedPath),
  ]);

  canvas.width = 896;
  canvas.height = 1200;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  drawContained(ctx, hand, canvas.width, canvas.height);

  ctx.save();
  ctx.globalAlpha = 0.36;
  ctx.globalCompositeOperation = "soft-light";
  drawContained(ctx, styleImage, canvas.width, canvas.height);
  ctx.restore();

  ctx.save();
  ctx.globalAlpha = 0.18;
  ctx.globalCompositeOperation = "source-over";
  drawContained(ctx, styleImage, canvas.width, canvas.height);
  ctx.restore();

  els.resultCanvas.classList.remove("is-hidden");
  els.aiResultImage.classList.add("is-hidden");
  els.emptyResult.classList.add("is-hidden");
  els.statusText.textContent = state.lastAiError
    ? `AI 试戴未启动：${state.lastAiError}。已使用本地 Canvas 预览`
    : "已使用本地 Canvas 预览";

  const imageSrc = canvas.toDataURL("image/png");
  setCurrentResult({
    imageSrc,
    styleTitle: style.title,
    styleId: style.styleId,
    tags: style.tags,
    price: style.price,
    mode: "local",
    createdAt: new Date().toISOString(),
  });
  recordEvent("local_preview_generated", pickStyleEvent(style));
}

function drawContained(ctx, image, width, height) {
  const scale = Math.min(width / image.naturalWidth, height / image.naturalHeight);
  const drawWidth = image.naturalWidth * scale;
  const drawHeight = image.naturalHeight * scale;
  const x = (width - drawWidth) / 2;
  const y = (height - drawHeight) / 2;
  ctx.drawImage(image, x, y, drawWidth, drawHeight);
}

async function requestAiTryon(style) {
  const handImageDataUrl = await getHandImageDataUrl();
  if (!handImageDataUrl) return null;

  const nailShapePolicy = getNailShapePolicy(style);
  const crop = await createHandCropForTryon(handImageDataUrl, nailShapePolicy);
  if (crop) {
    const highPrecisionResult = await requestAiTryonPayload(style, crop.dataUrl, {
      strategy: "high_precision_crop",
      cropBox: crop.cropBox,
      sourceSize: crop.sourceSize,
      detectionMode: crop.detectionMode,
    });
    if (highPrecisionResult) {
      const composed = await composeCropResult(handImageDataUrl, highPrecisionResult, crop);
      if (composed) {
        highPrecisionResult.resultImageBase64 = composed.split(",", 2)[1];
        highPrecisionResult.resultImageUrl = "";
        highPrecisionResult.composedImageSrc = composed;
        highPrecisionResult.tryonStrategy = "high_precision_crop";
        return highPrecisionResult;
      }
      state.lastAiError = "高精度回贴失败，已切换完整手图融合";
      recordEvent("ai_tryon_strategy_fallback", {
        styleId: style.styleId,
        from: "high_precision_crop",
        to: "full_image_fast",
        reason: "compose_failed",
      });
    }
  }

  const fastResult = await requestAiTryonPayload(style, handImageDataUrl, {
    strategy: "full_image_fast",
  });
  if (fastResult) {
    fastResult.tryonStrategy = "full_image_fast";
  }
  return fastResult;
}

async function requestAiTryonPayload(style, handImageDataUrl, handProcessing) {
  const payload = {
    sessionId: state.sessionId,
    handImageDataUrl,
    handProcessing,
    nailShapePolicy: getNailShapePolicy(style),
    style,
    createdAt: new Date().toISOString(),
  };

  try {
    const response = await fetch(`${API_BASE}/api/tryon`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok || !result.ok) {
      state.lastAiError = result.message || result.errorCode || `HTTP ${response.status}`;
      recordEvent("ai_tryon_failed", {
        styleId: style.styleId,
        strategy: handProcessing.strategy,
        errorCode: result.errorCode,
        message: result.message,
      });
      return null;
    }
    state.lastAiError = "";
    recordEvent("ai_tryon_completed", {
      styleId: style.styleId,
      strategy: handProcessing.strategy,
      taskId: result.taskId,
      hasUrl: Boolean(result.resultImageUrl),
      hasBase64: Boolean(result.resultImageBase64),
    });
    return result;
  } catch {
    state.lastAiError = `无法连接 ${API_BASE}/api/tryon，请确认后端已启动`;
    return null;
  }
}

function getNailShapePolicy(style) {
  const tags = new Set(style.tags || []);
  if (tags.has("长甲")) return "extend_and_reshape";
  if (tags.has("短甲") || tags.has("通勤") || tags.has("简约")) return "preserve_natural";
  return "match_reference_shape";
}

async function createHandCropForTryon(handImageDataUrl, nailShapePolicy = "match_reference_shape") {
  const image = await loadImage(handImageDataUrl);
  const canvas = document.createElement("canvas");
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(image, 0, 0);
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const bounds = detectSkinBounds(imageData.data, canvas.width, canvas.height) || centeredBounds(canvas.width, canvas.height);
  const paddingRatio =
    nailShapePolicy === "extend_and_reshape" ? TRYON_CROP_PADDING_RATIO * 1.8 : TRYON_CROP_PADDING_RATIO;
  const padded = padBounds(bounds, canvas.width, canvas.height, paddingRatio);
  const cropCanvas = document.createElement("canvas");
  cropCanvas.width = padded.width;
  cropCanvas.height = padded.height;
  cropCanvas
    .getContext("2d")
    .drawImage(canvas, padded.x, padded.y, padded.width, padded.height, 0, 0, padded.width, padded.height);
  return {
    dataUrl: cropCanvas.toDataURL("image/jpeg", TRYON_UPLOAD_JPEG_QUALITY),
    cropBox: padded,
    sourceSize: {
      width: canvas.width,
      height: canvas.height,
    },
    detectionMode: bounds ? "skin_bbox" : "center_crop",
  };
}

function detectSkinBounds(data, width, height) {
  let minX = width;
  let minY = height;
  let maxX = -1;
  let maxY = -1;
  let count = 0;
  const step = 4;
  for (let y = 0; y < height; y += step) {
    for (let x = 0; x < width; x += step) {
      const index = (y * width + x) * 4;
      const r = data[index];
      const g = data[index + 1];
      const b = data[index + 2];
      if (isLikelySkinPixel(r, g, b)) {
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
        count += 1;
      }
    }
  }
  const minPixels = Math.max(80, (width * height) / 12000);
  if (count < minPixels || maxX <= minX || maxY <= minY) return null;
  return {
    x: minX,
    y: minY,
    width: maxX - minX + step,
    height: maxY - minY + step,
  };
}

function isLikelySkinPixel(r, g, b) {
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  return (
    r > 70 &&
    g > 35 &&
    b > 20 &&
    max - min > 12 &&
    r > g * 0.95 &&
    r > b * 1.08 &&
    g > b * 0.78
  );
}

function centeredBounds(width, height) {
  const cropWidth = Math.round(width * 0.86);
  const cropHeight = Math.round(height * 0.86);
  return {
    x: Math.round((width - cropWidth) / 2),
    y: Math.round((height - cropHeight) / 2),
    width: cropWidth,
    height: cropHeight,
  };
}

function padBounds(bounds, width, height, ratio) {
  const pad = Math.round(Math.max(bounds.width, bounds.height) * ratio);
  const x = Math.max(0, bounds.x - pad);
  const y = Math.max(0, bounds.y - pad);
  const right = Math.min(width, bounds.x + bounds.width + pad);
  const bottom = Math.min(height, bounds.y + bounds.height + pad);
  return {
    x,
    y,
    width: right - x,
    height: bottom - y,
  };
}

async function composeCropResult(handImageDataUrl, result, crop) {
  const imageSrc = result.resultImageUrl || (result.resultImageBase64 ? `data:image/png;base64,${result.resultImageBase64}` : "");
  if (!imageSrc) return "";
  try {
    const [base, generatedCrop] = await Promise.all([
      loadImage(handImageDataUrl),
      imageSrc.startsWith("data:") ? loadImage(imageSrc) : loadImageForCanvas(imageSrc),
    ]);
    const canvas = document.createElement("canvas");
    canvas.width = crop.sourceSize.width;
    canvas.height = crop.sourceSize.height;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(base, 0, 0, canvas.width, canvas.height);
    ctx.drawImage(
      generatedCrop,
      crop.cropBox.x,
      crop.cropBox.y,
      crop.cropBox.width,
      crop.cropBox.height
    );
    return canvas.toDataURL("image/jpeg", TRYON_UPLOAD_JPEG_QUALITY);
  } catch {
    return "";
  }
}

function showAiResult(result, style) {
  let imageSrc = "";
  if (result.composedImageSrc) {
    imageSrc = result.composedImageSrc;
  } else if (result.resultImageUrl) {
    imageSrc = result.resultImageUrl;
  } else if (result.resultImageBase64) {
    imageSrc = `data:image/png;base64,${result.resultImageBase64}`;
  }
  if (!imageSrc) return;

  els.aiResultImage.src = imageSrc;
  els.resultCanvas.classList.add("is-hidden");
  els.aiResultImage.classList.remove("is-hidden");
  els.emptyResult.classList.add("is-hidden");
  els.statusText.textContent = "AI 试戴效果已生成，可以收藏、加入对比或预约";

  setCurrentResult({
    imageSrc,
    styleTitle: style.title,
    styleId: style.styleId,
    tags: style.tags,
    price: style.price,
    mode: result.tryonStrategy === "high_precision_crop" ? "ai_high_precision" : "ai",
    createdAt: new Date().toISOString(),
  });
}

function setCurrentResult(item) {
  state.currentResult = item;
  addHistoryItem(item);
  setResultActions(true);
  renderFavoriteState();
}

function setResultActions(enabled) {
  [els.favoriteButton, els.compareButton, els.appointmentButton].forEach((button) => {
    button.disabled = !enabled;
  });
}

function toggleCurrentFavorite() {
  if (!state.currentResult) return;
  const exists = state.favorites.some((item) => item.styleId === state.currentResult.styleId);
  state.favorites = exists
    ? state.favorites.filter((item) => item.styleId !== state.currentResult.styleId)
    : [state.currentResult, ...state.favorites].slice(0, 24);
  localStorage.setItem("tryonFavorites", JSON.stringify(state.favorites));
  renderFavoriteState();
  recordEvent(exists ? "style_unfavorite" : "style_favorite", state.currentResult);
}

function renderFavoriteState() {
  const count = state.favorites.length;
  els.favoriteCount.textContent = `${count} 收藏`;
  const active =
    state.currentResult && state.favorites.some((item) => item.styleId === state.currentResult.styleId);
  els.favoriteButton.classList.toggle("is-active", Boolean(active));
  els.favoriteButton.textContent = active ? "已收藏" : "收藏";
}

function addCurrentToCompare() {
  if (!state.currentResult) return;
  state.compareItems = [
    state.currentResult,
    ...state.compareItems.filter((item) => item.styleId !== state.currentResult.styleId),
  ].slice(0, 4);
  renderCompareList();
  recordEvent("compare_added", state.currentResult);
}

function renderCompareList() {
  els.emptyCompare.classList.toggle("is-hidden", state.compareItems.length > 0);
  els.compareList.querySelectorAll(".compare-item").forEach((node) => node.remove());
  state.compareItems.forEach((item) => {
    const card = document.createElement("article");
    card.className = "compare-item";
    card.innerHTML = `
      <img src="${item.imageSrc}" alt="${item.styleTitle} 对比图">
      <div>
        <strong>${item.styleTitle}</strong>
        <span>${item.tags.join(" · ")}</span>
        <em>¥${item.price}</em>
      </div>
      <button type="button" aria-label="移除 ${item.styleTitle}">×</button>
    `;
    card.querySelector("button").addEventListener("click", () => removeCompareItem(item.styleId));
    card.addEventListener("click", (event) => {
      if (event.target.tagName !== "BUTTON") showHistoryItem(item);
    });
    els.compareList.appendChild(card);
  });
  renderCompareInsights();
}

function removeCompareItem(styleId) {
  state.compareItems = state.compareItems.filter((item) => item.styleId !== styleId);
  renderCompareList();
}

function clearCompare() {
  state.compareItems = [];
  renderCompareList();
}

function renderCompareInsights() {
  const enabled = state.compareItems.length >= 2;
  els.openCompareDialogButton.disabled = !enabled;
  if (state.compareItems.length < 2) {
    els.compareInsightHint.textContent = "选择至少 2 个候选款后生成对比建议";
    const emptyHtml = `<div class="compare-insight-empty">先把 2 个以上试戴结果加入候选款池</div>`;
    els.compareInsightBody.innerHTML = emptyHtml;
    els.compareDialogHint.textContent = "选择至少 2 个候选款后生成对比建议";
    els.compareDialogBody.innerHTML = emptyHtml;
    return;
  }

  const recommendation = buildFinalRecommendation(state.compareItems);
  const pairs = buildPairComparisons(state.compareItems);
  els.compareInsightHint.textContent = `${state.compareItems.length} 个候选款 · ${pairs.length} 组两两对比`;
  els.compareDialogHint.textContent = els.compareInsightHint.textContent;
  const insightHtml = `
    <article class="recommendation-card">
      <div>
        <span>综合推荐</span>
        <strong>${recommendation.best.styleTitle}</strong>
        <p>${recommendation.reason}</p>
      </div>
      <button type="button" data-appoint-style="${recommendation.best.styleId}">预约推荐款</button>
    </article>
    <div class="pair-compare-grid">
      ${pairs.map(renderPairComparisonCard).join("")}
    </div>
  `;
  els.compareInsightBody.innerHTML = insightHtml;
  els.compareDialogBody.innerHTML = insightHtml;

  [els.compareInsightBody, els.compareDialogBody].forEach((container) => {
    container.querySelectorAll("button[data-appoint-style]").forEach((button) => {
      button.addEventListener("click", () => {
        const item = state.compareItems.find((candidate) => candidate.styleId === button.dataset.appointStyle);
        if (!item) return;
        showHistoryItem(item);
        closeCompareDialog();
        openAppointmentDialog();
        recordEvent("comparison_appointment_clicked", item);
      });
    });
  });
}

function openCompareDialog() {
  renderCompareInsights();
  if (state.compareItems.length < 2) return;
  if (typeof els.compareDialog.showModal === "function") {
    els.compareDialog.showModal();
  } else {
    els.compareDialog.setAttribute("open", "");
  }
}

function closeCompareDialog() {
  if (els.compareDialog.open) {
    els.compareDialog.close();
  }
}

async function requestAiCompareInsights(items) {
  const prompt = buildComparePrompt(items);
  const response = await fetch(`${API_BASE}/api/compare-insights`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sessionId: state.sessionId,
      items,
      prompt,
      createdAt: new Date().toISOString(),
    }),
  });
  if (!response.ok) {
    throw new Error(`AI compare request failed: HTTP ${response.status}`);
  }
  return response.json();
}

function buildComparePrompt(items) {
  const candidates = items
    .map((item, index) => {
      const scores = scoreStyleForComparison(item);
      return `
候选款 ${index + 1}
- 款式名：${item.styleTitle}
- 款式 ID：${item.styleId}
- 标签：${(item.tags || []).join("、")}
- 价格：${item.price}
- 生成模式：${item.mode}
- 维度评分：场景适配 ${scores.sceneFit}，显手效果 ${scores.handEffect}，日常耐看 ${scores.dailyWear}，拍照吸睛 ${scores.photoImpact}，性价比 ${scores.costEfficiency}，综合 ${scores.total}
`.trim()
    })
    .join("\n\n");
  return `
你是用户端美甲试戴推荐助手，目标是在用户已经试戴并加入候选池的款式中，帮她快速选出更值得预约的一款。

推荐原则：
- 优先结合标签、价格、试戴生成模式和维度评分，不要只看单一分数。
- 说人话，像门店顾问给用户选款；避免商家运营口吻。
- 结论要明确，但保留审美差异：使用“更适合、可以优先考虑、如果更想要...则选...”。
- 不要承诺医疗、美容或绝对效果；不要说“一定显白、一定显手长、适合所有手型”。
- 只能基于候选款信息判断，不要编造用户肤色、职业、年龄、预算或未提供的图像细节。

候选款如下：
${candidates}

请只输出 JSON，不要 Markdown，不要解释 JSON 外的内容。字段固定如下：
{
  "bestRecommendation": {
    "styleId": "推荐款式 ID",
    "styleTitle": "推荐款式名",
    "reason": "30 字以内，说明最关键的 1-2 个理由",
    "bestFor": "最适合的用户场景，如通勤日常/约会拍照/派对出片",
    "confidence": "high|medium|low"
  },
  "pairComparisons": [
    {
      "leftStyleId": "候选 A ID",
      "rightStyleId": "候选 B ID",
      "winnerStyleId": "更推荐的 ID，接近时填 tie",
      "dimensionSummary": {
        "sceneFit": "哪款更适合场景，20 字以内",
        "handEffect": "哪款更强调手部观感，20 字以内",
        "dailyWear": "哪款更日常耐看，20 字以内",
        "photoImpact": "哪款更适合拍照，20 字以内",
        "costEfficiency": "哪款价格效果更均衡，20 字以内"
      },
      "chooseAdvice": "用如果...选...；如果...选...的句式给出取舍"
    }
  ],
  "finalAdvice": "给用户的一句话收口建议，40 字以内"
}
`.trim();
}

function buildFinalRecommendation(items) {
  const ranked = items
    .map((item) => ({
      item,
      scores: scoreStyleForComparison(item),
    }))
    .sort((a, b) => b.scores.total - a.scores.total);
  const best = ranked[0];
  const second = ranked[1];
  const bestTags = best.item.tags.join("、");
  const secondText = second ? `备选可以保留 ${second.item.styleTitle}，它在 ${bestContrastLabel(second.scores)} 上也有优势。` : "";
  return {
    best: best.item,
    reason: `${best.item.styleTitle} 综合分最高，优势集中在 ${bestContrastLabel(best.scores)}，标签为 ${bestTags}。${secondText}`,
  };
}

function buildPairComparisons(items) {
  const pairs = [];
  for (let i = 0; i < items.length; i += 1) {
    for (let j = i + 1; j < items.length; j += 1) {
      pairs.push(buildPairComparison(items[i], items[j]));
    }
  }
  return pairs.sort((a, b) => b.gap - a.gap);
}

function buildPairComparison(a, b) {
  const aScores = scoreStyleForComparison(a);
  const bScores = scoreStyleForComparison(b);
  const rows = COMPARE_DIMENSIONS.map((dimension) => {
    const aValue = aScores[dimension.key];
    const bValue = bScores[dimension.key];
    return {
      ...dimension,
      aValue,
      bValue,
      winner: Math.abs(aValue - bValue) < 4 ? "tie" : aValue > bValue ? "a" : "b",
      note: buildDimensionNote(dimension.key, a, b, aValue, bValue),
    };
  });
  const winner = aScores.total >= bScores.total ? a : b;
  const loser = winner.styleId === a.styleId ? b : a;
  const winnerSide = winner.styleId === a.styleId ? "a" : "b";
  return {
    a,
    b,
    rows,
    winner,
    gap: Math.abs(aScores.total - bScores.total),
    conclusion: buildPairConclusion(winner, loser, rows, winnerSide),
  };
}

function renderPairComparisonCard(pair) {
  const rows = pair.rows
    .map(
      (row) => `
        <div class="dimension-row">
          <span>${row.label}</span>
          <div class="score-track" aria-label="${row.label}">
            <i style="width:${row.aValue}%"></i>
            <b style="width:${row.bValue}%"></b>
          </div>
          <strong>${winnerText(row, pair.a, pair.b)}</strong>
          <em>${row.note}</em>
        </div>
      `
    )
    .join("");
  return `
    <article class="pair-compare-card">
      <div class="pair-head">
        <div>
          <span>A</span>
          <strong>${pair.a.styleTitle}</strong>
        </div>
        <small>vs</small>
        <div>
          <span>B</span>
          <strong>${pair.b.styleTitle}</strong>
        </div>
      </div>
      <div class="pair-images">
        <img src="${pair.a.imageSrc}" alt="${pair.a.styleTitle}">
        <img src="${pair.b.imageSrc}" alt="${pair.b.styleTitle}">
      </div>
      <div class="dimension-list">${rows}</div>
      <p class="pair-conclusion">${pair.conclusion}</p>
    </article>
  `;
}

function scoreStyleForComparison(item) {
  const tags = new Set(item.tags || []);
  const price = Number(item.price || 198);
  const score = {
    sceneFit: 55,
    handEffect: 55,
    dailyWear: 55,
    photoImpact: 55,
    costEfficiency: Math.max(45, Math.min(92, 105 - price / 4)),
  };

  if (hasAny(tags, ["通勤", "短甲", "低饱和", "简约", "裸色"])) {
    score.sceneFit += 16;
    score.dailyWear += 24;
    score.costEfficiency += 8;
  }
  if (hasAny(tags, ["法式", "显白", "约会", "白色"])) {
    score.sceneFit += 18;
    score.handEffect += 24;
    score.photoImpact += 12;
  }
  if (hasAny(tags, ["猫眼", "高级感", "低饱和"])) {
    score.handEffect += 15;
    score.photoImpact += 18;
    score.dailyWear += 6;
  }
  if (hasAny(tags, ["亮片", "派对", "长甲", "黑色", "酷感", "红色", "节日"])) {
    score.sceneFit += 10;
    score.photoImpact += 28;
    score.dailyWear -= 12;
    score.costEfficiency -= 6;
  }
  if (hasAny(tags, ["粉色", "甜美", "学生"])) {
    score.sceneFit += 12;
    score.dailyWear += 10;
    score.handEffect += 8;
  }
  if (item.mode === "ai") {
    score.handEffect += 4;
    score.photoImpact += 4;
  }

  Object.keys(score).forEach((key) => {
    score[key] = Math.max(0, Math.min(100, Math.round(score[key])));
  });
  score.total = Math.round(
    score.sceneFit * 0.22 +
      score.handEffect * 0.24 +
      score.dailyWear * 0.18 +
      score.photoImpact * 0.2 +
      score.costEfficiency * 0.16
  );
  return score;
}

function hasAny(tags, candidates) {
  return candidates.some((tag) => tags.has(tag));
}

function bestContrastLabel(scores) {
  const best = COMPARE_DIMENSIONS.slice()
    .sort((a, b) => scores[b.key] - scores[a.key])
    .slice(0, 2)
    .map((dimension) => dimension.label);
  return best.join("、");
}

function winnerText(row, a, b) {
  if (row.winner === "tie") return "接近";
  return row.winner === "a" ? a.styleTitle : b.styleTitle;
}

function buildDimensionNote(key, a, b, aValue, bValue) {
  if (Math.abs(aValue - bValue) < 4) return "两款表现接近，更多取决于个人审美。";
  const winner = aValue > bValue ? a : b;
  const loser = aValue > bValue ? b : a;
  const tagText = (winner.tags || []).slice(0, 2).join("、");
  const notes = {
    sceneFit: `${winner.styleTitle} 的 ${tagText} 更贴近明确场景。`,
    handEffect: `${winner.styleTitle} 更适合强调手型和肤色表现。`,
    dailyWear: `${winner.styleTitle} 比 ${loser.styleTitle} 更耐看、低风险。`,
    photoImpact: `${winner.styleTitle} 更容易在拍照或社交场景里出效果。`,
    costEfficiency: `${winner.styleTitle} 在价格和效果之间更均衡。`,
  };
  return notes[key] || `${winner.styleTitle} 略占优势。`;
}

function buildPairConclusion(winner, loser, rows, winnerSide) {
  const bestRows = rows
    .filter((row) => row.winner === winnerSide)
    .slice(0, 2)
    .map((row) => row.label)
    .join("、");
  if (!bestRows) {
    return `${winner.styleTitle} 和 ${loser.styleTitle} 表现接近，可以根据当天穿搭和心情选择。`;
  }
  return `综合看更推荐 ${winner.styleTitle}，它在 ${bestRows} 上更有优势；${loser.styleTitle} 更适合作为备选或收藏观望。`;
}

function openAppointmentDialog() {
  if (!state.currentResult) return;
  els.appointmentStyleLabel.textContent = `${state.currentResult.styleTitle} · ¥${state.currentResult.price}`;
  if (typeof els.appointmentDialog.showModal === "function") {
    els.appointmentDialog.showModal();
  } else {
    els.appointmentDialog.setAttribute("open", "");
  }
  recordEvent("appointment_open", state.currentResult);
}

function closeAppointmentDialog() {
  if (els.appointmentDialog.open) {
    els.appointmentDialog.close();
  }
}

function submitAppointment(event) {
  event.preventDefault();
  if (!state.currentResult) return;
  const payload = {
    ...state.currentResult,
    shop: els.shopSelect.value,
    time: els.timeSelect.value,
    phoneProvided: Boolean(els.phoneInput.value.trim()),
  };
  recordEvent("appointment_intent", payload);
  closeAppointmentDialog();
  els.statusText.textContent = `已提交 ${state.currentResult.styleTitle} 的预约意向，商家端可继续生成运营方案`;
}

function startProgress(label) {
  stopProgressTimer();
  state.progressValue = 6;
  els.progressLabel.textContent = label;
  setProgress(6);
  els.progressOverlay.classList.remove("is-hidden");
  state.progressTimer = window.setInterval(() => {
    const next = Math.min(92, state.progressValue + Math.max(1, Math.round((96 - state.progressValue) * 0.08)));
    setProgress(next);
  }, 420);
}

function completeProgress(label) {
  els.progressLabel.textContent = label;
  setProgress(100);
  stopProgressTimer();
  window.setTimeout(() => {
    els.progressOverlay.classList.add("is-hidden");
  }, 420);
}

function setProgress(value) {
  state.progressValue = value;
  els.progressValue.textContent = `${value}%`;
  els.progressBar.style.width = `${value}%`;
}

function stopProgressTimer() {
  if (state.progressTimer) {
    window.clearInterval(state.progressTimer);
    state.progressTimer = null;
  }
}

function addHistoryItem(item) {
  state.history.unshift(item);
  state.history = state.history.slice(0, 12);
  renderHistory();
}

function renderHistory() {
  els.historyCount.textContent = `${state.history.length} 张`;
  els.emptyHistory.classList.toggle("is-hidden", state.history.length > 0);
  els.historyList.querySelectorAll(".history-item").forEach((node) => node.remove());

  state.history.forEach((item) => {
    const button = document.createElement("button");
    button.className = "history-item";
    button.type = "button";
    button.innerHTML = `
      <img src="${item.imageSrc}" alt="${item.styleTitle} 试戴历史">
      <span>${item.mode === "ai" ? "AI" : "本地"} · ${item.styleTitle}</span>
    `;
    button.addEventListener("click", () => showHistoryItem(item));
    els.historyList.appendChild(button);
  });
}

function showHistoryItem(item) {
  state.currentResult = item;
  els.aiResultImage.src = item.imageSrc;
  els.resultCanvas.classList.add("is-hidden");
  els.aiResultImage.classList.remove("is-hidden");
  els.emptyResult.classList.add("is-hidden");
  els.selectedStyleLabel.textContent = `${item.styleTitle} · ${item.styleId}`;
  els.statusText.textContent = "已从本次试戴历史中恢复效果图";
  setResultActions(true);
  renderFavoriteState();
}

async function recordEvent(eventType, detail) {
  const payload = {
    eventType,
    detail,
    sessionId: state.sessionId,
    page: "nail_tryon_mvp",
    createdAt: new Date().toISOString(),
  };

  try {
    await fetch(`${API_BASE}/api/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    storeLocalEvent(payload);
  }
}

function pickStyleEvent(style) {
  return {
    styleId: style.styleId,
    title: style.title,
    tags: style.tags,
    price: style.price,
    filter: style.filter,
  };
}

function storeLocalEvent(payload) {
  const events = loadStorage("tryonEvents", []);
  events.push(payload);
  localStorage.setItem("tryonEvents", JSON.stringify(events.slice(-500)));
}

function exportEvents() {
  const events = loadStorage("tryonEvents", []);
  const blob = new Blob([JSON.stringify(events, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `tryon-events-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
  els.statusText.textContent = `已导出 ${events.length} 条本地交互记录`;
}

function loadStorage(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key) || JSON.stringify(fallback));
  } catch {
    return fallback;
  }
}

init().catch(() => {
  els.statusText.textContent = "款式清单加载失败";
  els.styleCount.textContent = "0 款";
});
