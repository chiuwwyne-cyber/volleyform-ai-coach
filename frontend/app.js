const APP_BUILD = encodeURIComponent(
  String(globalThis.VOLLEYFORM_BUILD || "20260815-frontend-sync-v66"),
);

const serverStatus = document.querySelector("#serverStatus");
const analyzeBtn = document.querySelector("#analyzeBtn");
const backendUrlInput = document.querySelector("#backendUrl");
const sameOriginBtn = document.querySelector("#sameOriginBtn");
const localBackendBtn = document.querySelector("#localBackendBtn");
const healthCheckBtn = document.querySelector("#healthCheckBtn");
const connectionNote = document.querySelector("#connectionNote");
const actionInput = document.querySelector("#action");
const actionChoices = document.querySelector("#actionChoices");
const powerModeInput = document.querySelector("#powerMode");
const videoInput = document.querySelector("#video");
const fileName = document.querySelector("#fileName");
const previewPlaceholder = document.querySelector("#previewPlaceholder");
const analysisSummary = document.querySelector("#analysisSummary");
const installAppBtn = document.querySelector("#installAppBtn");
const shareQrBtn = document.querySelector("#shareQrBtn");
const qrModal = document.querySelector("#qrModal");
const qrModalClose = document.querySelector("#qrModalClose");
const qrCodeContainer = document.querySelector("#qrCodeContainer");
const qrCodeUrl = document.querySelector("#qrCodeUrl");
const summaryTitle = document.querySelector("#summaryTitle");
const coachSummary = document.querySelector("#coachSummary");
const coachPlan = document.querySelector("#coachPlan");
const frameCount = document.querySelector("#frameCount");
const issues = document.querySelector("#issues");
const poseViewToggle = document.querySelector("#poseViewToggle");
const poseCompareActual = document.querySelector("#poseCompareActual");
const poseCompareCorrected = document.querySelector("#poseCompareCorrected");
const poseCompareNote = document.querySelector("#poseCompareNote");
const poseErrorSkeleton = document.querySelector("#poseErrorSkeleton");
const poseErrorSkeletonCanvas = document.querySelector("#poseErrorSkeletonCanvas");
const slowmoBtn = document.querySelector("#slowmoBtn");
const practiceBtn = document.querySelector("#practiceBtn");
const qualityHint = document.querySelector("#qualityHint");
const dropZone = document.querySelector("#dropZone");
const modalityList = document.querySelector("#modalityList");
const recordPreview = document.querySelector("#recordPreview");
const imagePreview = document.querySelector("#imagePreview");
const poseOverlay = document.querySelector("#poseOverlay");
const liveFeedback = document.querySelector("#liveFeedback");
const liveStatus = document.querySelector("#liveStatus");
const liveCue = document.querySelector("#liveCue");
const liveMetrics = document.querySelector("#liveMetrics");
const recordStatus = document.querySelector("#recordStatus");
const startLiveBtn = document.querySelector("#startLiveBtn");
const stopLiveBtn = document.querySelector("#stopLiveBtn");
const startRecordBtn = document.querySelector("#startRecordBtn");
const stopRecordBtn = document.querySelector("#stopRecordBtn");
const clearRecordBtn = document.querySelector("#clearRecordBtn");

// QR sharing is wired first, via delegation on document, so it keeps working
// even if anything later in this file fails to execute.
let qrLibraryPromise = null;

function loadQrLibrary() {
  if (typeof window !== "undefined" && window.qrcode) return Promise.resolve();
  if (!qrLibraryPromise) {
    qrLibraryPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "./vendor/qrcode/qrcode.js";
      script.onload = () => resolve();
      script.onerror = () => reject(new Error("QR code 產生器載入失敗"));
      document.head.appendChild(script);
    });
  }
  return qrLibraryPromise;
}

function currentPageUrl() {
  return globalThis.location?.href || openSourceFrontendUrl;
}

function isStaticPublicHost() {
  // GitHub Pages (and other static hosts) can't serve a same-origin API, and
  // the launcher's runtime-share.json is git-ignored so it never ships there
  // either. Probing them would only print guaranteed 404s to the console, so
  // we skip the probes and go straight to the on-device / page-url fallbacks.
  const host = globalThis.location?.hostname || "";
  return host === "github.io" || host.endsWith(".github.io");
}

function normalizeShareUrl(url) {
  try {
    const parsed = new URL(url, currentPageUrl());
    parsed.hash = "";
    return parsed.toString();
  } catch {
    return currentPageUrl();
  }
}

function shouldAttachBackendQuery(shareUrl) {
  const backend = backendUrlInput?.value?.trim();
  if (!backend) return false;
  try {
    return new URL(shareUrl).origin !== new URL(backend).origin;
  } catch {
    return true;
  }
}

function shareUrlWithBackend(shareUrl) {
  const normalized = normalizeShareUrl(shareUrl);
  if (!shouldAttachBackendQuery(normalized)) return normalized;
  try {
    const parsed = new URL(normalized);
    parsed.searchParams.set("backend", backendUrlInput.value.trim());
    return parsed.toString();
  } catch {
    return normalized;
  }
}

function bestRuntimeShareUrl(payload) {
  if (!payload || typeof payload !== "object") return "";
  if (payload.publicUrl) return payload.publicUrl;

  const host = globalThis.location?.hostname || "";
  const isLoopback = host === "127.0.0.1" || host === "localhost" || host === "::1";
  if (isLoopback && payload.lanUrl) return payload.lanUrl;

  return payload.preferredUrl || payload.lanUrl || payload.localUrl || "";
}

async function resolveShareUrl() {
  // runtime-share.json is only written by the local launcher (and is
  // git-ignored), so on a static public host it can never exist — skip the
  // guaranteed-404 fetch and share the page's own URL instead.
  if (!isStaticPublicHost()) {
    try {
      const response = await fetch("./runtime-share.json", { cache: "no-store" });
      if (response.ok) {
        const payload = await response.json();
        const runtimeUrl = bestRuntimeShareUrl(payload);
        if (runtimeUrl) return shareUrlWithBackend(runtimeUrl);
      }
    } catch {
      // The file only exists when the local launcher writes it.
    }
  }
  return shareUrlWithBackend(currentPageUrl());
}

async function showShareQr() {
  const url = await resolveShareUrl();
  qrCodeUrl.textContent = url;
  qrCodeContainer.textContent = "產生中…";
  qrModal.hidden = false;
  try {
    await loadQrLibrary();
    const qr = window.qrcode(0, "M");
    qr.addData(url);
    qr.make();
    qrCodeContainer.innerHTML = qr.createSvgTag({ cellSize: 5, margin: 4 });
  } catch (error) {
    qrCodeContainer.textContent = error.message || "QR code 產生失敗";
  }
}

document.addEventListener?.("click", (event) => {
  const target = event.target;
  if (!target || typeof target.closest !== "function") return;
  if (target.closest("#shareQrBtn")) {
    showShareQr();
    return;
  }
  if (target.closest("#qrModalClose") || target === qrModal) {
    qrModal.hidden = true;
  }
});

document.addEventListener?.("keydown", (event) => {
  if (event.key === "Escape" && qrModal && !qrModal.hidden) qrModal.hidden = true;
});

const powerSettings = {
  mobile: { frame_stride: "4", process_width: "480", max_frames: "150" },
  balanced: { frame_stride: "2", process_width: "640", max_frames: "210" },
  quality: { frame_stride: "1", process_width: "800", max_frames: "300" },
};

const backendUrlStorageKey = "volleyballCoachBackendUrl";
const maxFrontendUploadBytes = 180 * 1024 * 1024;
const maxRecordingMs = 12000;
const recordingTimesliceMs = 1000;
const recordingVideoBitsPerSecond = 1600000;
const runtimeConfig = globalThis.VOLLEYBALL_COACH_CONFIG || {};
const openSourceFrontendUrl =
  runtimeConfig.publicFrontendUrl || "https://chiuwwyne-cyber.github.io/volleyform-ai-coach/";
const queryBackend = backendFromQuery();
backendUrlInput.value =
  queryBackend || safeLocalStorageGet(backendUrlStorageKey) || runtimeConfig.apiBase || "";
let mediaStream = null;
let mediaRecorder = null;
let recordedChunks = [];
let recordedVideoUrl = "";
let recordingStopTimer = null;
let deferredInstallPrompt = null;
let backendAvailable = false;
let realtimeController = null;
let liveAnalysisActive = false;

const actionMeta = {
  spike: { symbol: "扣", description: "起跳、揮臂、落地" },
  block: { symbol: "攔", description: "起跳時機、手型、落地" },
  serve: { symbol: "發", description: "拋球、擊球、重心" },
  receive: { symbol: "接", description: "平台、膝蓋、移動" },
  set: { symbol: "舉", description: "手型、手腕、出球" },
};

const fallbackActions = [
  { id: "spike", label: "扣球" },
  { id: "block", label: "攔網" },
  { id: "serve", label: "發球" },
  { id: "receive", label: "接球" },
  { id: "set", label: "舉球" },
];

const fallbackModalities = [
  {
    id: "pose",
    label: "3D 身體骨架",
    available: true,
    requested: true,
    description: "分析全身關節、角度與動作順序",
  },
  {
    id: "hands",
    label: "手部關節",
    available: true,
    requested: true,
    description: "分析手指、手腕與雙手距離",
  },
];

Object.assign(actionMeta, {
  spike: { symbol: "扣", description: "左、右、左助跑 / 起跳 / 落地" },
  block: { symbol: "攔", description: "起跳時機 / 手型 / 落地" },
  serve: { symbol: "發", description: "拋球 / 擊球點 / 重心" },
  receive: { symbol: "接", description: "平台 / 膝蓋 / 移動" },
  set: { symbol: "舉", description: "手型 / 手腕 / 出球" },
});

fallbackActions.splice(
  0,
  fallbackActions.length,
  { id: "spike", label: "扣球" },
  { id: "block", label: "攔網" },
  { id: "serve", label: "發球" },
  { id: "receive", label: "接球" },
  { id: "set", label: "舉球" },
);

fallbackModalities.splice(
  0,
  fallbackModalities.length,
  {
    id: "pose",
    label: "3D 身體骨架",
    available: true,
    requested: true,
    description: "分析全身關節、軀幹角度與落地控制",
  },
  {
    id: "hands",
    label: "手部關節",
    available: true,
    requested: true,
    description: "分析手指、手腕、雙手距離與舉球手型",
  },
);

const decodeUiText = (value) => decodeURIComponent(value);
Object.assign(actionMeta, {
  spike: {
    symbol: decodeUiText("%E6%89%A3"),
    description: decodeUiText("%E5%B7%A6%E3%80%81%E5%8F%B3%E3%80%81%E5%B7%A6%E5%8A%A9%E8%B7%91%20%2F%20%E8%B5%B7%E8%B7%B3%20%2F%20%E8%90%BD%E5%9C%B0"),
  },
  block: {
    symbol: decodeUiText("%E6%94%94"),
    description: decodeUiText("%E8%B5%B7%E8%B7%B3%E6%99%82%E6%A9%9F%20%2F%20%E6%89%8B%E5%9E%8B%20%2F%20%E8%90%BD%E5%9C%B0"),
  },
  serve: {
    symbol: decodeUiText("%E7%99%BC"),
    description: decodeUiText("%E6%8B%8B%E7%90%83%20%2F%20%E6%93%8A%E7%90%83%E9%BB%9E%20%2F%20%E9%87%8D%E5%BF%83"),
  },
  receive: {
    symbol: decodeUiText("%E6%8E%A5"),
    description: decodeUiText("%E5%B9%B3%E5%8F%B0%20%2F%20%E8%86%9D%E8%93%8B%20%2F%20%E7%A7%BB%E5%8B%95"),
  },
  set: {
    symbol: decodeUiText("%E8%88%89"),
    description: decodeUiText("%E6%89%8B%E5%9E%8B%20%2F%20%E6%89%8B%E8%85%95%20%2F%20%E5%87%BA%E7%90%83"),
  },
});

fallbackActions.splice(
  0,
  fallbackActions.length,
  { id: "spike", label: decodeUiText("%E6%89%A3%E7%90%83") },
  { id: "block", label: decodeUiText("%E6%94%94%E7%B6%B2") },
  { id: "serve", label: decodeUiText("%E7%99%BC%E7%90%83") },
  { id: "receive", label: decodeUiText("%E6%8E%A5%E7%90%83") },
  { id: "set", label: decodeUiText("%E8%88%89%E7%90%83") },
);

fallbackModalities.splice(
  0,
  fallbackModalities.length,
  {
    id: "pose",
    label: "3D " + decodeUiText("%E8%BA%AB%E9%AB%94%E9%AA%A8%E6%9E%B6"),
    available: true,
    requested: true,
    description: decodeUiText("%E5%88%86%E6%9E%90%E5%85%A8%E8%BA%AB%E9%97%9C%E7%AF%80%E3%80%81%E8%BB%80%E5%B9%B9%E8%A7%92%E5%BA%A6%E8%88%87%E8%90%BD%E5%9C%B0%E6%8E%A7%E5%88%B6"),
  },
  {
    id: "hands",
    label: decodeUiText("%E6%89%8B%E9%83%A8%E9%97%9C%E7%AF%80"),
    available: true,
    requested: true,
    description: decodeUiText("%E5%88%86%E6%9E%90%E6%89%8B%E6%8C%87%E3%80%81%E6%89%8B%E8%85%95%E3%80%81%E9%9B%99%E6%89%8B%E8%B7%9D%E9%9B%A2%E8%88%87%E8%88%89%E7%90%83%E6%89%8B%E5%9E%8B"),
  },
);

function backendFromQuery() {
  if (typeof URLSearchParams === "undefined" || !globalThis.location?.search) return "";
  return new URLSearchParams(globalThis.location.search).get("backend")?.trim() || "";
}

function safeLocalStorageGet(key) {
  try {
    return localStorage.getItem(key) || "";
  } catch {
    return "";
  }
}

function safeLocalStorageSet(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Some mobile browsers can disable storage in private mode.
  }
}

function apiUrl(path) {
  const base = backendUrlInput.value.trim().replace(/\/+$/, "");
  if (!base) return path;
  return `${base}${path}`;
}

function persistBackendUrl() {
  safeLocalStorageSet(backendUrlStorageKey, backendUrlInput.value.trim());
}

function updateConnectionNote(message) {
  if (connectionNote) connectionNote.textContent = message;
}

async function setBackendUrl(value, message) {
  backendUrlInput.value = value;
  updateConnectionNote(message);
  await checkHealth();
}

function useOnDeviceMode() {
  backendAvailable = false;
  serverStatus.textContent = "手機本地";
  serverStatus.classList.remove("bad");
  serverStatus.classList.add("ok");
  renderActionOptions(fallbackActions);
  renderModalityOptions(fallbackModalities);
  updateConnectionNote(
    "目前使用手機本地 MediaPipe 模型分析，影片不會上傳到伺服器。也可以填入固定 API 網址切換到雲端分析。",
  );
}

async function checkHealth() {
  persistBackendUrl();
  serverStatus.textContent = "檢查中";
  serverStatus.classList.remove("ok", "bad");
  // A static public host (GitHub Pages) has no same-origin backend, so unless
  // the user configured a cloud API we skip the probe that would 404 and go
  // straight to on-device analysis — keeping the console clean.
  if (!backendUrlInput.value.trim() && isStaticPublicHost()) {
    useOnDeviceMode();
    return;
  }
  try {
    const response = await fetch(apiUrl("/api/capabilities"));
    if (!response.ok) throw new Error("bad status");
    const payload = await response.json();
    backendAvailable = true;
    serverStatus.textContent = "已連線";
    serverStatus.classList.remove("bad");
    serverStatus.classList.add("ok");
    renderCapabilities(payload.capabilities);
    const target = backendUrlInput.value.trim() || "目前網頁同網域";
    updateConnectionNote(`後端連線正常：${target}`);
  } catch {
    useOnDeviceMode();
  }
}

backendUrlInput.addEventListener("change", checkHealth);
backendUrlInput.addEventListener("blur", checkHealth);
sameOriginBtn.addEventListener("click", () =>
  setBackendUrl("", "使用網站同網域 API；前後端部署在同一個公開網址時使用。"),
);
localBackendBtn.addEventListener("click", () =>
  setBackendUrl("http://127.0.0.1:8000", "只在這台電腦測試時使用本機後端。"),
);
healthCheckBtn.addEventListener("click", checkHealth);

function renderCapabilities(capabilities) {
  if (!capabilities) return;
  renderActionOptions(capabilities.actions);
  renderModalityOptions(capabilities.modalities);
}

function renderActionOptions(actions) {
  if (!Array.isArray(actions) || actions.length === 0) return;

  const currentValue = actionInput.value;
  const normalizedActions = [];
  actionInput.innerHTML = "";
  for (const action of actions) {
    const item = normalizeActionOption(action);
    if (!item.id) continue;
    normalizedActions.push(item);

    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.label || item.id;
    actionInput.appendChild(option);
  }

  if ([...actionInput.options].some((option) => option.value === currentValue)) {
    actionInput.value = currentValue;
  } else if (actionInput.options.length > 0) {
    actionInput.value = actionInput.options[0].value;
  }
  renderActionChoices(normalizedActions);
  updateAnalysisSummary();
  if (actionInput.value) startDemoAnimation(actionInput.value);
}

function normalizeActionOption(action) {
  if (typeof action === "string") {
    return { id: action, label: action };
  }
  return {
    id: action.id || "",
    label: action.label || action.id || "",
  };
}

function renderActionChoices(actions) {
  if (!actionChoices) return;
  actionChoices.innerHTML = "";
  for (const action of actions) {
    const meta = actionMeta[action.id] || {
      symbol: (action.label || action.id).slice(0, 1),
      description: "動作姿勢與關節角度",
    };
    const button = document.createElement("button");
    button.className = "action-choice";
    button.type = "button";
    button.dataset.action = action.id;
    button.setAttribute("role", "option");
    button.innerHTML = `
      <span>${escapeHtml(meta.symbol)}</span>
      <strong>${escapeHtml(action.label || action.id)}</strong>
      <small>${escapeHtml(meta.description)}</small>
    `;
    button.addEventListener("click", () => selectAction(action.id));
    actionChoices.appendChild(button);
  }
  syncActionChoices();
}

function selectAction(actionId) {
  actionInput.value = actionId;
  syncActionChoices();
  updateAnalysisSummary();
  startDemoAnimation(actionId);
}

function syncActionChoices() {
  if (!actionChoices) return;
  for (const button of actionChoices.querySelectorAll("[data-action]")) {
    const selected = button.dataset.action === actionInput.value;
    if (selected) {
      button.classList.add("active");
    } else {
      button.classList.remove("active");
    }
    button.setAttribute("aria-selected", selected ? "true" : "false");
  }
}

function renderModalityOptions(modalities) {
  if (!Array.isArray(modalities)) return;
  modalityList.innerHTML = "";
  for (const item of modalities) {
    const label = document.createElement("label");
    label.className = `modality-option ${item.available ? "" : "future"}`;
    label.title = item.description || "";
    label.innerHTML = `
      <input type="checkbox" value="${item.id}" ${item.requested ? "checked" : ""} />
      <span>${escapeHtml(item.label)}</span>
      <small>${item.available ? "可用" : "預留"}</small>
    `;
    modalityList.appendChild(label);
  }
}

function selectedFile() {
  return videoInput.files && videoInput.files[0] ? videoInput.files[0] : null;
}

function selectedModalities() {
  return [...modalityList.querySelectorAll("input:checked")].map((input) => input.value);
}

videoInput.addEventListener("change", () => {
  const file = selectedFile();
  fileName.textContent = file ? file.name : "支援照片、mp4、mov、webm，最大 180MB";
  if (file) {
    showMediaPreview(file);
  }
  updateAnalysisSummary();
});

actionInput.addEventListener("change", () => {
  syncActionChoices();
  updateAnalysisSummary();
});

powerModeInput.addEventListener("change", updateAnalysisSummary);

function updateAnalysisSummary() {
  if (!analysisSummary) return;
  const selectedOption = [...actionInput.options].find(
    (option) => option.value === actionInput.value,
  );
  const actionLabel = selectedOption?.textContent || "排球動作";
  const file = selectedFile();
  analysisSummary.textContent = file
    ? `${actionLabel} · ${file.name}`
    : `${actionLabel} · 尚未選擇照片或影片`;
}

dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropZone.classList.add("dragging");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragging");
});

dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("dragging");
  const file = event.dataTransfer.files[0];
  if (!file) return;
  const transfer = new DataTransfer();
  transfer.items.add(file);
  videoInput.files = transfer.files;
  fileName.textContent = file.name;
  showMediaPreview(file);
  updateAnalysisSummary();
});

startLiveBtn.addEventListener("click", startLiveAnalysis);
stopLiveBtn.addEventListener("click", () => stopLiveAnalysis());
startRecordBtn.addEventListener("click", startRecording);
stopRecordBtn.addEventListener("click", stopRecording);
clearRecordBtn.addEventListener("click", clearRecording);

async function startRecording() {
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    recordStatus.textContent = "這個瀏覽器不支援直接錄影，請改用上傳影片分析。";
    return;
  }

  try {
    stopLiveAnalysis(false);
    clearRecordedUrl();
    recordedChunks = [];
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: "environment" },
        width: { ideal: 960 },
        height: { ideal: 540 },
        frameRate: { ideal: 24, max: 30 },
      },
      audio: false,
    });

    recordPreview.hidden = false;
    imagePreview.hidden = true;
    recordPreview.srcObject = mediaStream;
    recordPreview.controls = false;
    recordPreview.muted = true;
    previewPlaceholder?.classList.add("hidden");
    await recordPreview.play();

    const mimeType = preferredRecordingMimeType();
    const options = {
      ...(mimeType ? { mimeType } : {}),
      videoBitsPerSecond: recordingVideoBitsPerSecond,
    };
    mediaRecorder = new MediaRecorder(mediaStream, options);
    mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data && event.data.size > 0) {
        recordedChunks.push(event.data);
      }
    });
    mediaRecorder.addEventListener("stop", finishRecording);
    mediaRecorder.start(recordingTimesliceMs);
    recordingStopTimer = setTimeout(stopRecording, maxRecordingMs);

    startRecordBtn.disabled = true;
    stopRecordBtn.disabled = false;
    clearRecordBtn.disabled = true;
    recordStatus.textContent = "錄影中，最多 12 秒。請讓全身、手腕與膝蓋盡量入鏡。";
  } catch (error) {
    clearRecordingTimer();
    stopMediaStream();
    startRecordBtn.disabled = false;
    stopRecordBtn.disabled = true;
    clearRecordBtn.disabled = false;
    recordStatus.textContent = `無法開始錄影：${error.message}`;
  }
}

function stopRecording() {
  clearRecordingTimer();
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
  stopRecordBtn.disabled = true;
  recordStatus.textContent = "正在整理錄影檔案";
}

function finishRecording() {
  clearRecordingTimer();
  const mimeType = mediaRecorder?.mimeType || "video/webm";
  const extension = mimeType.includes("mp4") ? "mp4" : "webm";
  const blob = new Blob(recordedChunks, { type: mimeType });
  const file = new File([blob], `volleyball-recording.${extension}`, { type: mimeType });
  recordedChunks = [];
  setVideoInputFile(file);
  showMediaPreview(file);
  stopMediaStream();
  mediaRecorder = null;
  startRecordBtn.disabled = false;
  stopRecordBtn.disabled = true;
  clearRecordBtn.disabled = false;
  recordStatus.textContent = "錄影完成，可以先回放確認，再按開始分析。";
}

function clearRecording() {
  stopLiveAnalysis(false);
  clearRecordingTimer();
  recordedChunks = [];
  clearRecordedUrl();
  stopMediaStream();
  videoInput.value = "";
  recordPreview.removeAttribute("src");
  recordPreview.srcObject = null;
  recordPreview.hidden = false;
  recordPreview.controls = false;
  imagePreview.removeAttribute("src");
  imagePreview.hidden = true;
  clearPoseOverlay();
  previewPlaceholder?.classList.remove("hidden");
  fileName.textContent = "支援照片、mp4、mov、webm，最大 180MB";
  recordStatus.textContent = "可以直接錄製 12 秒內的動作，錄完後可先回放，再送出分析。";
  updateAnalysisSummary();
}

function setVideoInputFile(file) {
  const transfer = new DataTransfer();
  transfer.items.add(file);
  videoInput.files = transfer.files;
  fileName.textContent = file.name;
  updateAnalysisSummary();
}

function showMediaPreview(file) {
  stopLiveAnalysis(false);
  clearRecordedUrl();
  recordedVideoUrl = URL.createObjectURL(file);
  recordPreview.srcObject = null;
  recordPreview.removeAttribute("src");
  imagePreview.removeAttribute("src");
  clearPoseOverlay();

  if (file.type.startsWith("image/")) {
    recordPreview.hidden = true;
    recordPreview.controls = false;
    imagePreview.hidden = false;
    imagePreview.src = recordedVideoUrl;
  } else {
    imagePreview.hidden = true;
    recordPreview.hidden = false;
    recordPreview.src = recordedVideoUrl;
    recordPreview.controls = true;
    recordPreview.muted = false;
  }
  previewPlaceholder?.classList.add("hidden");
}

function clearPoseOverlay() {
  const context = poseOverlay?.getContext?.("2d");
  if (context) context.clearRect(0, 0, poseOverlay.width, poseOverlay.height);
  if (poseOverlay) {
    poseOverlay.width = 1;
    poseOverlay.height = 1;
  }
}

async function startLiveAnalysis() {
  if (!navigator.mediaDevices?.getUserMedia) {
    liveCue.textContent = "這個瀏覽器無法開啟相機，請改用手機相簿上傳照片或影片。";
    liveFeedback.classList.add("alert");
    return;
  }

  try {
    stopLiveAnalysis(false);
    clearRecordedUrl();
    videoInput.value = "";
    fileName.textContent = "即時分析中，停止後可改選照片或影片";
    updateAnalysisSummary();

    recordPreview.removeAttribute("src");
    recordPreview.hidden = false;
    recordPreview.controls = false;
    recordPreview.muted = true;
    imagePreview.hidden = true;
    imagePreview.removeAttribute("src");
    previewPlaceholder?.classList.add("hidden");
    clearPoseOverlay();

    liveAnalysisActive = true;
    startLiveBtn.disabled = true;
    stopLiveBtn.disabled = false;
    startRecordBtn.disabled = true;
    clearRecordBtn.disabled = true;
    liveFeedback.classList.remove("alert");
    liveFeedback.classList.add("active");
    liveStatus.textContent = "正在開啟相機";
    liveCue.textContent = "把手機放穩，讓全身跟雙手都入鏡，我們就可以開始了。";
    liveMetrics.textContent = "我會一邊看一邊提醒你，手機也不會太耗電，放心。";

    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: "environment" },
        width: { ideal: 960, max: 1280 },
        height: { ideal: 540, max: 720 },
        frameRate: { ideal: 20, max: 24 },
      },
      audio: false,
    });
    if (!liveAnalysisActive) {
      stopMediaStream();
      return;
    }

    recordPreview.srcObject = mediaStream;
    await recordPreview.play();
    liveStatus.textContent = "載入手機端 AI";

    const { startRealtimeAnalysis } = await import("./local-analyzer.js");
    if (!liveAnalysisActive) {
      stopMediaStream();
      return;
    }
    realtimeController = await startRealtimeAnalysis({
      video: recordPreview,
      canvas: poseOverlay,
      getAction: () => actionInput.value,
      getModalities: selectedModalities,
      getPowerMode: () => powerModeInput.value,
      onUpdate: renderLiveUpdate,
    });
    liveStatus.textContent = "即時分析中";
    recordStatus.textContent = "相機畫面只在這台裝置上分析，不會上傳。";
  } catch (error) {
    stopLiveAnalysis();
    liveFeedback.classList.add("alert");
    liveStatus.textContent = "無法啟動即時分析";
    liveCue.textContent = error.message || "請允許相機權限後再試一次。";
  }
}

function renderLiveUpdate(result) {
  if (!liveAnalysisActive) return;
  liveFeedback.classList.remove("active", "alert");
  if (!result.poseDetected) {
    liveFeedback.classList.add("alert");
    liveStatus.textContent = "等待完整人體";
    liveCue.textContent = "退後一點，讓頭、雙手跟雙腳都進到畫面裡，我才看得到你的動作。";
    liveMetrics.textContent = "喬好位置我們就開始，不用急。";
    return;
  }

  const primaryIssue = result.issues?.[0];
  liveFeedback.classList.add(primaryIssue ? "alert" : "active");
  liveStatus.textContent = primaryIssue ? primaryIssue.title : "這球做得不錯！";
  liveCue.textContent = result.cue;
  const hands = result.handsDetected || 0;
  liveMetrics.textContent = primaryIssue
    ? "跟著上面那句話慢慢調，抓到感覺就會穩下來了。"
    : hands >= 2
      ? "很好，就是這個手型，保持住！"
      : "先讓全身跟雙手都進到畫面裡，我才看得清楚喔。";
}

function stopLiveAnalysis(showPlaceholder = true) {
  liveAnalysisActive = false;
  realtimeController?.stop();
  realtimeController = null;
  stopMediaStream();
  recordPreview.srcObject = null;
  recordPreview.controls = false;
  clearPoseOverlay();
  startLiveBtn.disabled = false;
  stopLiveBtn.disabled = true;
  startRecordBtn.disabled = false;
  clearRecordBtn.disabled = false;
  liveFeedback.classList.remove("active", "alert");
  liveStatus.textContent = "即時分析尚未啟動";
  liveCue.textContent = "選好動作、開啟相機，我就會一邊看你做、一邊告訴你哪裡可以更好。";
  liveMetrics.textContent = "先挑一個動作，準備好就開始吧。";
  if (showPlaceholder) {
    previewPlaceholder?.classList.remove("hidden");
    recordStatus.textContent = "即時分析已停止，相機資源已釋放。";
  }
}

function clearRecordedUrl() {
  if (recordedVideoUrl) {
    URL.revokeObjectURL(recordedVideoUrl);
    recordedVideoUrl = "";
  }
}

function stopMediaStream() {
  if (!mediaStream) return;
  for (const track of mediaStream.getTracks()) {
    track.stop();
  }
  mediaStream = null;
}

function clearRecordingTimer() {
  if (!recordingStopTimer) return;
  clearTimeout(recordingStopTimer);
  recordingStopTimer = null;
}

function preferredRecordingMimeType() {
  const candidates = [
    "video/webm;codecs=vp9",
    "video/webm;codecs=vp8",
    "video/webm",
    "video/mp4",
  ];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

analyzeBtn.addEventListener("click", async () => {
  const file = selectedFile();
  if (!file) {
    coachSummary.textContent = "請先拍照、錄影，或從手機相簿選擇檔案。";
    return;
  }
  if (file.size && file.size > maxFrontendUploadBytes) {
    summaryTitle.textContent = "影片太大";
    coachSummary.textContent = "請改用較短影片，或使用內建錄影控制在 12 秒內。";
    coachPlan.textContent = "建議每次分析 5 到 10 秒，動作完整且人要清楚入鏡。";
    return;
  }

  const settings = powerSettings[powerModeInput.value] || powerSettings.balanced;
  const form = new FormData();
  form.append("video", file);
  form.append("action", actionInput.value);
  form.append("frame_stride", settings.frame_stride);
  form.append("process_width", settings.process_width);
  form.append("max_frames", settings.max_frames);
  form.append("modalities", JSON.stringify(selectedModalities()));

  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "分析中";
  summaryTitle.textContent = "AI 分析中";
  coachSummary.textContent = "正在擷取 3D 身體骨架與手部關節，請稍等。";
  coachPlan.textContent = "分析完成後會整理成優先修正建議。";
  issues.textContent = "正在尋找主要動作問題";
  poseCompareNote.textContent = "分析完成後會顯示姿勢比對";

  try {
    if (backendAvailable && !file.type.startsWith("image/")) {
      const response = await fetch(apiUrl("/api/analyze"), {
        method: "POST",
        body: form,
      });
      const payload = await response.json();
      if (!payload.ok) throw new Error(payload.error || "分析失敗");
      renderResult(payload.result);
    } else {
      const { analyzeMediaLocally } = await import("./local-analyzer.js");
      const result = await analyzeMediaLocally({
        file,
        action: actionInput.value,
        powerMode: powerModeInput.value,
        modalities: selectedModalities(),
        onProgress: (message) => {
          coachSummary.textContent = message;
        },
      });
      renderResult(result);
    }
  } catch (error) {
    summaryTitle.textContent = "分析失敗";
    coachSummary.textContent = error.message;
    coachPlan.textContent = "請確認影片格式與檔案大小，並改用手機省電模式重新分析。";
    issues.textContent = "目前沒有可顯示的問題。";
    poseCompareNote.textContent = "";
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "開始 AI 分析";
  }
});

function renderResult(result) {
  summaryTitle.textContent = `${result.action_label} 分析完成`;
  coachSummary.textContent = result.coach_summary;
  frameCount.textContent = `已用 0.1 秒為單位完成分析`;
  renderCoachPlan(result.coach_plan);
  renderIssues(result.primary_issues);
  renderPoseCompare(result.pose_compare, result.action);
}

function renderCoachPlan(plan) {
  coachPlan.innerHTML = "";
  coachPlan.classList.remove("empty", "stable", "needs-fix", "needs-video");

  if (!plan) {
    coachPlan.classList.add("empty");
    coachPlan.textContent = "目前沒有教練建議。";
    return;
  }

  const steps = Array.isArray(plan.next_steps) ? plan.next_steps : [];
  const statusClass = plan.status ? plan.status.replaceAll("_", "-") : "needs-fix";
  coachPlan.classList.add(statusClass);
  coachPlan.innerHTML = `
    <div class="coach-plan-head">
      <span>${escapeHtml(plan.focus || "優先修正")}</span>
      <strong>${escapeHtml(plan.headline || "先修正最影響表現的動作")}</strong>
    </div>
    <p>${escapeHtml(plan.reason || "")}</p>
    <ol>${steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol>
    <a class="video-link" href="${plan.video_url}" target="_blank" rel="noreferrer">觀看建議影片</a>
  `;
}

function renderIssues(items) {
  issues.innerHTML = "";
  issues.classList.remove("empty");

  if (!items || items.length === 0) {
    issues.classList.add("empty");
    issues.textContent = "沒有找到明顯問題，保持動作穩定並再錄一段不同角度的影片。";
    return;
  }

  for (const item of items) {
    const card = document.createElement("article");
    card.className = `issue-card ${item.severity}`;
    card.innerHTML = `
      <div class="issue-title">
        <span>${escapeHtml(item.title)}</span>
        <small>${severityLabel(item.severity)} · ${item.count} 次</small>
      </div>
      <div class="issue-meta">
        <span>${escapeHtml(item.body_part || "需要觀察")}</span>
        <strong>${escapeHtml(item.instant_cue || "先穩住動作")}</strong>
      </div>
      <p>${escapeHtml(item.message)}</p>
      <p class="issue-why">${escapeHtml(item.why_it_matters || "")}</p>
      <div class="drill-box">${escapeHtml(item.practice_drill || "")}</div>
      <ul class="fix-list">${item.fixes.map((fix) => `<li>${escapeHtml(fix)}</li>`).join("")}</ul>
      <a class="video-link" href="${item.video_url}" target="_blank" rel="noreferrer">觀看修正影片</a>
    `;
    issues.appendChild(card);
  }
}

function severityLabel(severity) {
  if (severity === "high") return "高風險";
  if (severity === "medium") return "中風險";
  return "提醒";
}

function renderCoachPlan(plan) {
  coachPlan.innerHTML = "";
  coachPlan.classList.remove("empty", "stable", "needs-fix", "needs-video");

  if (!plan) {
    coachPlan.classList.add("empty");
    coachPlan.textContent = "目前沒有教練建議。";
    return;
  }

  const steps = Array.isArray(plan.next_steps) ? plan.next_steps : [];
  const statusClass = plan.status ? plan.status.replaceAll("_", "-") : "needs-fix";
  coachPlan.classList.add(statusClass);
  coachPlan.innerHTML = `
    <div class="coach-plan-head">
      <span>${escapeHtml(plan.focus || "優先修正")}</span>
      <strong>${escapeHtml(plan.headline || "先修正最明顯的風險點")}</strong>
    </div>
    <p>${escapeHtml(plan.reason || "")}</p>
    <ol>${steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol>
    <a class="video-link" href="${plan.video_url}" target="_blank" rel="noreferrer">觀看建議影片</a>
  `;
}

function renderIssues(items) {
  issues.innerHTML = "";
  issues.classList.remove("empty");

  if (!items || items.length === 0) {
    issues.classList.add("empty");
    issues.textContent = "沒有找到明顯問題。建議再錄一段正面與側面影片，確認手部、腳步和落地都完整入鏡。";
    return;
  }

  for (const item of items) {
    const card = document.createElement("article");
    card.className = `issue-card ${item.severity}`;
    card.innerHTML = `
      <div class="issue-title">
        <span>${escapeHtml(item.title)}</span>
        <small>${severityLabel(item.severity)} / ${item.count} 個 0.1 秒時間點</small>
      </div>
      <div class="issue-meta">
        <span>${escapeHtml(item.body_part || "主要部位")}</span>
        <strong>${escapeHtml(item.instant_cue || "先慢下來修正")}</strong>
      </div>
      <p>${escapeHtml(item.message)}</p>
      <p class="issue-why">${escapeHtml(item.why_it_matters || "")}</p>
      <div class="drill-box">${escapeHtml(item.practice_drill || "")}</div>
      <ul class="fix-list">${(item.fixes || []).map((fix) => `<li>${escapeHtml(fix)}</li>`).join("")}</ul>
      <a class="video-link" href="${item.video_url}" target="_blank" rel="noreferrer">觀看修正影片</a>
    `;
    issues.appendChild(card);
  }
}

let poseCompareView = "front";
let poseSlowmo = false;

function setPoseActionsEnabled(on) {
  if (!slowmoBtn) return;
  slowmoBtn.disabled = !on;
  practiceBtn.disabled = !on;
  if (!on && poseSlowmo) {
    poseSlowmo = false;
    slowmoBtn.classList.remove("active");
    slowmoBtn.textContent = "慢動作";
  }
}

slowmoBtn?.addEventListener("click", () => {
  poseSlowmo = !poseSlowmo;
  slowmoBtn.classList.toggle("active", poseSlowmo);
  slowmoBtn.textContent = poseSlowmo ? "正常速度" : "慢動作";
  renderPoseCompareView();
});

practiceBtn?.addEventListener("click", () => {
  if (!coachPlan) return;
  coachPlan.scrollIntoView({ behavior: "smooth", block: "center" });
  coachPlan.classList.remove("flash");
  void coachPlan.offsetWidth;
  coachPlan.classList.add("flash");
});
let lastPoseCompare = null;
let lastPoseCompareAction = "spike";
let actualViewport = null;
let demoViewport = null;
let pose3dPromise = null;

function loadPose3d() {
  if (!pose3dPromise) {
    pose3dPromise =
      typeof globalThis.__pose3dLoader === "function" ? globalThis.__pose3dLoader() : import(`./pose-3d.js?v=${APP_BUILD}`);
  }
  return pose3dPromise;
}

async function ensureViewports() {
  const mod = await loadPose3d();
  if (!actualViewport) actualViewport = mod.createPoseViewport(poseCompareActual, { cameraDistance: 2.7, framePadding: 1.9 });
  if (!demoViewport) demoViewport = mod.createPoseViewport(poseCompareCorrected, { cameraDistance: 2.7 });
  return mod;
}

function renderPoseCompareView() {
  actualViewport?.setView(poseCompareView);
  demoViewport?.setView(poseCompareView);
  if (lastPoseCompare?.available) {
    const actualSequence = Array.isArray(lastPoseCompare.actual_sequence)
      ? lastPoseCompare.actual_sequence
      : [];
    if (actualSequence.length > 1 && typeof actualViewport?.playPoseSequence === "function") {
      actualViewport.playPoseSequence(actualSequence, {
        caption: "影片分析到的錯誤姿勢",
        loop: true,
        speedFactor: 1,
        action: lastPoseCompareAction,
        playbackSeconds: poseSlowmo ? 18 : 6,
        timeLabel: "relative-seconds",
      });
    } else {
      actualViewport?.setStaticPose(
        lastPoseCompare.actual_landmarks,
        lastPoseCompare.joint_status,
        { caption: "影片分析到的錯誤姿勢" },
      );
    }
  }
}

async function startDemoAnimation(action) {
  const mod = await ensureViewports();
  void mod;
  demoViewport.setView(poseCompareView);
  demoViewport.playDemo(action, { variant: "correct" });
}

// The 2D skeleton of the exact frame the analysis judged as the error, drawn
// below the 3D compare. Action-agnostic: any pose landmarks render the same way,
// with the flagged joints (red/yellow) matching the 3D figure's coloring.
const ERROR_SKELETON_BONES = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [15, 17], [15, 19], [15, 21], [16, 18], [16, 20], [16, 22],
  [11, 23], [12, 24], [23, 24], [23, 25], [24, 26], [25, 27], [26, 28],
  [27, 29], [27, 31], [29, 31], [28, 30], [28, 32], [30, 32],
];
const ERROR_SKELETON_JOINT = {
  11: "shoulder", 12: "shoulder", 13: "elbow", 14: "elbow",
  15: "wrist", 16: "wrist", 17: "wrist", 18: "wrist", 19: "wrist", 20: "wrist", 21: "wrist", 22: "wrist",
  25: "knee", 26: "knee",
};
const ERROR_SKELETON_COLOR = { green: "#c7d0c6", yellow: "#ffd34f", red: "#ff5d5d" };
const ERROR_SKELETON_RANK = { green: 0, yellow: 1, red: 2 };

function drawErrorSkeleton(canvas, landmarks, jointStatus) {
  const ctx = canvas.getContext("2d");
  const W = canvas.width;
  const H = canvas.height;
  const pad = 28;
  ctx.clearRect(0, 0, W, H);

  // World landmarks have no fixed y sign; orient so the shoulders sit above the
  // hips on screen (head up), then scale uniformly to fit the canvas.
  const shoulderY = (landmarks[11][1] + landmarks[12][1]) / 2;
  const hipY = (landmarks[23][1] + landmarks[24][1]) / 2;
  const upSign = shoulderY < hipY ? -1 : 1;
  const body = [];
  for (let i = 11; i < landmarks.length; i += 1) if (landmarks[i]) body.push(i);
  const xs = body.map((i) => landmarks[i][0]);
  const us = body.map((i) => upSign * landmarks[i][1]);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minU = Math.min(...us);
  const maxU = Math.max(...us);
  const spanX = maxX - minX || 1;
  const spanU = maxU - minU || 1;
  const scale = Math.min((W - 2 * pad) / spanX, (H - 2 * pad) / spanU);
  const offX = (W - spanX * scale) / 2;
  const offY = (H - spanU * scale) / 2;
  const project = (i) => [
    offX + (landmarks[i][0] - minX) * scale,
    offY + (maxU - upSign * landmarks[i][1]) * scale,
  ];
  const statusOf = (i) => jointStatus?.[ERROR_SKELETON_JOINT[i]] || "green";
  const colorOf = (s) => ERROR_SKELETON_COLOR[s] || ERROR_SKELETON_COLOR.green;

  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.lineWidth = Math.max(3, W / 150);
  for (const [a, b] of ERROR_SKELETON_BONES) {
    if (!landmarks[a] || !landmarks[b]) continue;
    const sa = statusOf(a);
    const sb = statusOf(b);
    ctx.strokeStyle = colorOf(ERROR_SKELETON_RANK[sa] >= ERROR_SKELETON_RANK[sb] ? sa : sb);
    const [x1, y1] = project(a);
    const [x2, y2] = project(b);
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
  }
  const headR = Math.max(9, spanU * scale * 0.06);
  const [hx, hy] = project(landmarks[0] ? 0 : 11);
  ctx.fillStyle = colorOf("green");
  ctx.beginPath();
  ctx.arc(hx, landmarks[0] ? hy : hy - headR, headR, 0, Math.PI * 2);
  ctx.fill();
  for (const i of body) {
    if (!(i in ERROR_SKELETON_JOINT)) continue;
    const [x, y] = project(i);
    ctx.fillStyle = colorOf(statusOf(i));
    ctx.beginPath();
    ctx.arc(x, y, Math.max(4, W / 130), 0, Math.PI * 2);
    ctx.fill();
  }
}

function renderErrorSkeleton(poseCompare) {
  if (!poseErrorSkeleton || !poseErrorSkeletonCanvas) return;
  let landmarks = poseCompare?.actual_landmarks;
  if ((!Array.isArray(landmarks) || landmarks.length < 33) && Array.isArray(poseCompare?.actual_sequence)) {
    let best = null;
    for (const frame of poseCompare.actual_sequence) {
      if (Array.isArray(frame?.landmarks) && frame.landmarks.length >= 33
        && (!best || (frame.severity || 0) > (best.severity || 0))) best = frame;
    }
    landmarks = best?.landmarks || null;
  }
  const ok = Array.isArray(landmarks) && landmarks.length >= 33 && landmarks[11] && landmarks[23];
  poseErrorSkeleton.hidden = !ok;
  if (ok) drawErrorSkeleton(poseErrorSkeletonCanvas, landmarks, poseCompare.joint_status || {});
}

function renderPoseCompare(poseCompare, action) {
  lastPoseCompare = poseCompare;
  lastPoseCompareAction = action || actionInput?.value || lastPoseCompareAction;
  startDemoAnimation(lastPoseCompareAction);

  if (!poseCompare || !poseCompare.available) {
    poseCompareNote.textContent = "沒有偵測到你的姿勢，右側動畫僅供參考正確姿勢。";
    ensureViewports().then(() => actualViewport.setStaticPose(null, null));
    return;
  }
  poseCompareNote.textContent = "綠色代表正常，黃色代表中間偏不正常，紅色代表需要修正。右側為正確姿勢示範動畫。";
  ensureViewports().then(() => {
    actualViewport.setView(poseCompareView);
    actualViewport.setStaticPose(poseCompare.actual_landmarks, poseCompare.joint_status);
  });
}

function renderPoseCompare(poseCompare, action) {
  lastPoseCompare = poseCompare;
  lastPoseCompareAction = action || actionInput?.value || lastPoseCompareAction;
  startDemoAnimation(lastPoseCompareAction);

  if (!poseCompare || !poseCompare.available) {
    poseCompareNote.textContent = "沒有偵測到可用的 3D 姿勢。請讓全身、雙手與腳步完整入鏡後再分析。";
    if (poseErrorSkeleton) poseErrorSkeleton.hidden = true;
    ensureViewports().then(() => actualViewport.setStaticPose(null, null));
    return;
  }

  const actualSequence = Array.isArray(poseCompare.actual_sequence)
    ? poseCompare.actual_sequence
    : [];
  poseCompareNote.textContent =
    actualSequence.length > 1
      ? "左側正在重播影片分析到的錯誤時間點；紅色是高風險受力點，黃色是需要修正的位置。右側是同動作的正確慢動作示範。"
      : "左側是影片或照片分析到的錯誤姿勢；紅色是高風險受力點，黃色是需要修正的位置。右側是同動作的正確慢動作示範。";

  renderErrorSkeleton(poseCompare);

  ensureViewports().then(() => {
    actualViewport.setView(poseCompareView);
    if (actualSequence.length > 1 && typeof actualViewport.playPoseSequence === "function") {
      actualViewport.playPoseSequence(actualSequence, {
        caption: "影片分析到的錯誤姿勢",
        loop: true,
        speedFactor: 1,
        action: lastPoseCompareAction,
        playbackSeconds: poseSlowmo ? 18 : 6,
        timeLabel: "relative-seconds",
      });
      return;
    }
    actualViewport.setStaticPose(
      poseCompare.actual_landmarks,
      poseCompare.joint_status,
      { caption: "影片分析到的錯誤姿勢" },
    );
  });
}

const actualPoseCaption = decodeUiText("%E5%BD%B1%E7%89%87%E5%88%86%E6%9E%90%E5%88%B0%E7%9A%84%E9%8C%AF%E8%AA%A4%E5%A7%BF%E5%8B%A2");
const noPoseCompareText = decodeUiText("%E6%B2%92%E6%9C%89%E5%81%B5%E6%B8%AC%E5%88%B0%E5%8F%AF%E7%94%A8%E7%9A%84%203D%20%E5%A7%BF%E5%8B%A2%E3%80%82%E8%AB%8B%E8%AE%93%E5%85%A8%E8%BA%AB%E3%80%81%E9%9B%99%E6%89%8B%E8%88%87%E8%85%B3%E6%AD%A5%E5%AE%8C%E6%95%B4%E5%85%A5%E9%8F%A1%E5%BE%8C%E5%86%8D%E5%88%86%E6%9E%90%E3%80%82");
const actualPoseReplayText = decodeUiText("%E5%B7%A6%E5%81%B4%E6%AD%A3%E5%9C%A8%E9%87%8D%E6%92%AD%E5%BD%B1%E7%89%87%E5%88%86%E6%9E%90%E5%88%B0%E7%9A%84%E9%8C%AF%E8%AA%A4%E9%97%9C%E9%8D%B5%E5%BD%B1%E6%A0%BC%EF%BC%9B%E7%B4%85%E8%89%B2%E6%98%AF%E9%AB%98%E9%A2%A8%E9%9A%AA%E5%8F%97%E5%8A%9B%E9%BB%9E%EF%BC%8C%E9%BB%83%E8%89%B2%E6%98%AF%E9%9C%80%E8%A6%81%E4%BF%AE%E6%AD%A3%E7%9A%84%E4%BD%8D%E7%BD%AE%E3%80%82%E5%8F%B3%E5%81%B4%E6%98%AF%E5%90%8C%E5%8B%95%E4%BD%9C%E7%9A%84%E6%AD%A3%E7%A2%BA%E6%85%A2%E5%8B%95%E4%BD%9C%E7%A4%BA%E7%AF%84%E3%80%82");
const actualPoseStillText = decodeUiText("%E5%B7%A6%E5%81%B4%E6%98%AF%E5%BD%B1%E7%89%87%E6%88%96%E7%85%A7%E7%89%87%E5%88%86%E6%9E%90%E5%88%B0%E7%9A%84%E9%8C%AF%E8%AA%A4%E5%A7%BF%E5%8B%A2%EF%BC%9B%E7%B4%85%E8%89%B2%E6%98%AF%E9%AB%98%E9%A2%A8%E9%9A%AA%E5%8F%97%E5%8A%9B%E9%BB%9E%EF%BC%8C%E9%BB%83%E8%89%B2%E6%98%AF%E9%9C%80%E8%A6%81%E4%BF%AE%E6%AD%A3%E7%9A%84%E4%BD%8D%E7%BD%AE%E3%80%82%E5%8F%B3%E5%81%B4%E6%98%AF%E5%90%8C%E5%8B%95%E4%BD%9C%E7%9A%84%E6%AD%A3%E7%A2%BA%E6%85%A2%E5%8B%95%E4%BD%9C%E7%A4%BA%E7%AF%84%E3%80%82");
const poseStatusRank = { green: 0, yellow: 1, red: 2 };

function mergePoseJointStatus(...statuses) {
  const merged = { shoulder: "green", elbow: "green", wrist: "green", knee: "green" };
  for (const status of statuses) {
    for (const joint of Object.keys(merged)) {
      const next = status?.[joint] || "green";
      if ((poseStatusRank[next] || 0) > (poseStatusRank[merged[joint]] || 0)) {
        merged[joint] = next;
      }
    }
  }
  return merged;
}

function playableActualSequence(poseCompare) {
  const actualSequence = Array.isArray(poseCompare?.actual_sequence)
    ? poseCompare.actual_sequence
    : [];
  if (actualSequence.length > 0) {
    const compareStatus = poseCompare?.joint_status || {};
    return actualSequence.map((frame) => {
      const rawStatus = frame.joint_status || frame.jointStatus || {};
      return {
        ...frame,
        joint_status: rawStatus,
        display_joint_status: mergePoseJointStatus(compareStatus, rawStatus),
      };
    });
  }
  if (poseCompare?.actual_landmarks?.length >= 33) {
    return [{
      landmarks: poseCompare.actual_landmarks,
      joint_status: poseCompare.joint_status || {},
      caption: actualPoseCaption,
      hold: 720,
    }];
  }
  return [];
}

function renderPoseCompareView() {
  actualViewport?.setView(poseCompareView);
  demoViewport?.setView(poseCompareView);
  if (!lastPoseCompare?.available) return;

  const actualSequence = playableActualSequence(lastPoseCompare);
  if (actualSequence.length > 0 && typeof actualViewport?.playPoseSequence === "function") {
    actualViewport.playPoseSequence(actualSequence, {
      caption: actualPoseCaption,
      loop: true,
      speedFactor: 1,
      action: lastPoseCompareAction,
      playbackSeconds: poseSlowmo ? 18 : 6,
      timeLabel: "relative-seconds",
    });
    return;
  }
  actualViewport?.setStaticPose(
    lastPoseCompare.actual_landmarks,
    lastPoseCompare.joint_status,
    { caption: actualPoseCaption },
  );
}

function renderPoseCompare(poseCompare, action) {
  lastPoseCompare = poseCompare;
  lastPoseCompareAction = action || actionInput?.value || lastPoseCompareAction;
  startDemoAnimation(lastPoseCompareAction);

  if (!poseCompare || !poseCompare.available) {
    poseCompareNote.textContent = noPoseCompareText;
    ensureViewports().then(() => actualViewport.setStaticPose(null, null, { caption: "沒有可用的 3D 姿勢，請重新分析影片。" }));
    return;
  }

  const actualSequence = playableActualSequence(poseCompare);
  poseCompareNote.textContent = actualSequence.length > 0
    ? actualPoseReplayText
    : actualPoseStillText;

  ensureViewports().then(() => {
    actualViewport.setView(poseCompareView);
    if (actualSequence.length > 0 && typeof actualViewport.playPoseSequence === "function") {
      actualViewport.playPoseSequence(actualSequence, {
        caption: actualPoseCaption,
        loop: true,
        speedFactor: 1,
        action: lastPoseCompareAction,
        playbackSeconds: poseSlowmo ? 18 : 6,
        timeLabel: "relative-seconds",
      });
      return;
    }
    actualViewport.setStaticPose(
      poseCompare.actual_landmarks,
      poseCompare.joint_status,
      { caption: actualPoseCaption },
    );
  });
}

poseViewToggle?.addEventListener("click", (event) => {
  const button = event.target.closest(".view-toggle-btn");
  if (!button) return;
  poseCompareView = button.dataset.view;
  for (const btn of poseViewToggle.querySelectorAll(".view-toggle-btn")) {
    btn.classList.toggle("active", btn === button);
  }
  renderPoseCompareView();
});

if (typeof window !== "undefined") {
  window.addEventListener("resize", () => {
    actualViewport?.resize();
    demoViewport?.resize();
  });
}

function severityLabel(severity) {
  if (severity === "high") return "高優先";
  if (severity === "medium") return "中優先";
  return "提醒";
}

function severityLabel(severity) {
  if (severity === "high") return "高風險";
  if (severity === "medium") return "中風險";
  return "提醒";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function severityLabel(severity) {
  if (severity === "high") return "高風險";
  if (severity === "medium") return "中風險";
  return "提醒";
}

function formatSeconds(value) {
  const seconds = Number(value);
  if (!Number.isFinite(seconds)) return null;
  const start = Number(Math.max(0, seconds).toFixed(1));
  const end = Number((start + 0.1).toFixed(1));
  return `第 ${start.toFixed(1)}-${end.toFixed(1)} 秒`;
}

function issueTimeSummary(item) {
  const times = Array.isArray(item.time_seconds) ? item.time_seconds : [];
  const labels = times.map(formatSeconds).filter(Boolean);
  if (labels.length) return labels.slice(0, 4).join("、");
  const first = formatSeconds(item.first_time_seconds);
  return first || "關鍵動作";
}

function phaseProblemDetails(phaseAnalysis) {
  const details = { hasReference: false, hasProblem: false, times: [] };
  if (!phaseAnalysis || phaseAnalysis.mode !== "reference") return details;
  details.hasReference = true;
  for (const phase of Object.values(phaseAnalysis.phases || {})) {
    const joints = Object.values(phase.joints || {});
    const phaseHasProblem = joints.some((joint) => joint.status && joint.status !== "green");
    if (!phaseHasProblem) continue;
    details.hasProblem = true;
    const seconds = Number(phase.time_seconds);
    if (Number.isFinite(seconds)) details.times.push(seconds);
  }
  return details;
}

function stablePhasePlan(actionLabel) {
  return {
    status: "stable",
    headline: `${actionLabel}關鍵動作通過`,
    focus: "新版角度區間",
    reason: "擊球和蓄力這些關鍵瞬間都在正常範圍內，沒有需要特別修正的地方。",
    next_steps: ["維持完整動作節奏。", "下一球前確認落地與重心穩定。"],
    video_url: "https://www.youtube.com/results?search_query=volleyball+warm+up+injury+prevention",
  };
}

function normalizePhaseAwareResult(result) {
  if (!result || !result.phase_analysis) return result;
  const phase = phaseProblemDetails(result.phase_analysis);
  if (!phase.hasReference) return result;

  const actionLabel = result.action_label || "動作";
  if (!phase.hasProblem) {
    return {
      ...result,
      primary_issues: [],
      coach_summary: `${actionLabel}的關鍵動作都在正常範圍內，沒有明顯要修的地方。`,
      coach_plan: stablePhasePlan(actionLabel),
    };
  }

  return {
    ...result,
    primary_issues: (result.primary_issues || []).map((item) => ({
      ...item,
      count: Math.min(Number(item.count) || 1, 1),
      time_seconds: Array.isArray(item.time_seconds) && item.time_seconds.length
        ? item.time_seconds
        : phase.times,
      first_time_seconds: item.first_time_seconds ?? phase.times[0] ?? null,
    })),
  };
}

function renderResult(result) {
  result = normalizePhaseAwareResult(result);
  summaryTitle.textContent = `${result.action_label} 分析結果`;
  coachSummary.textContent = result.coach_summary;
  frameCount.textContent = `已用 0.1 秒為單位完成分析`;
  renderCoachPlan(result.coach_plan);
  renderIssues(result.primary_issues);
  renderPoseCompare(result.pose_compare, result.action);
  // Low-quality hint: nudge toward 高精度 unless already on it (UC004).
  if (qualityHint) qualityHint.hidden = powerModeInput?.value === "quality";
}

function renderIssues(items) {
  issues.innerHTML = "";
  issues.classList.remove("empty");

  if (!items || items.length === 0) {
    issues.classList.add("empty");
    issues.textContent = "目前沒有偵測到明顯錯誤；請保持全身、手部與腳步完整入鏡。";
    return;
  }

  for (const item of items) {
    const card = document.createElement("article");
    card.className = `issue-card ${item.severity}`;
    card.innerHTML = `
      <div class="issue-title">
        <span>${escapeHtml(item.title)}</span>
        <small>${severityLabel(item.severity)} · ${escapeHtml(issueTimeSummary(item))}</small>
      </div>
      <div class="issue-meta">
        <span>${escapeHtml(item.body_part || "動作位置")}</span>
        <strong>${escapeHtml(item.instant_cue || "先修正主要受力點")}</strong>
      </div>
      <p>${escapeHtml(item.message)}</p>
      <p class="issue-why">${escapeHtml(item.why_it_matters || "")}</p>
      <div class="drill-box">${escapeHtml(item.practice_drill || "")}</div>
      <ul class="fix-list">${(item.fixes || []).map((fix) => `<li>${escapeHtml(fix)}</li>`).join("")}</ul>
      <a class="video-link" href="${item.video_url}" target="_blank" rel="noreferrer">觀看修正影片</a>
    `;
    issues.appendChild(card);
  }
}

function renderPoseCompareView() {
  actualViewport?.setView(poseCompareView);
  demoViewport?.setView(poseCompareView);
  if (!lastPoseCompare?.available) return;

  const actualSequence = playableActualSequence(lastPoseCompare);
  if (actualSequence.length > 0 && typeof actualViewport?.playPoseSequence === "function") {
    actualViewport.playPoseSequence(actualSequence, {
      caption: "影片中的實際動作",
      loop: true,
      speedFactor: 1,
      action: lastPoseCompareAction,
      playbackSeconds: poseSlowmo ? 18 : 6,
      timeLabel: "relative-seconds",
    });
    return;
  }
  actualViewport?.setStaticPose(
    lastPoseCompare.actual_landmarks,
    lastPoseCompare.joint_status,
    { caption: "影片中的實際動作" },
  );
}

function renderPoseCompare(poseCompare, action) {
  lastPoseCompare = poseCompare;
  lastPoseCompareAction = action || actionInput?.value || lastPoseCompareAction;
  startDemoAnimation(lastPoseCompareAction);

  if (!poseCompare || !poseCompare.available) {
    poseCompareNote.textContent = noPoseCompareText;
    setPoseActionsEnabled(false);
    ensureViewports().then(() => actualViewport.setStaticPose(null, null));
    return;
  }

  const actualSequence = playableActualSequence(poseCompare);
  setPoseActionsEnabled(true);
  poseCompareNote.textContent = actualSequence.length > 0
    ? "左側 3D 小人會依照影片時間順序重播你的實際動作一次；錯誤會標示在第幾秒。黃色代表需要修正，紅色是高風險受力點。右側是同動作的正確慢動作示範。"
    : "左側是影片或照片分析到的姿勢；黃色代表需要修正，紅色是高風險受力點。右側是同動作的正確慢動作示範。";

  ensureViewports().then(() => {
    actualViewport.setView(poseCompareView);
    if (actualSequence.length > 0 && typeof actualViewport.playPoseSequence === "function") {
      actualViewport.playPoseSequence(actualSequence, {
        caption: "影片中的實際動作",
        loop: true,
        speedFactor: 1,
        action: lastPoseCompareAction,
        playbackSeconds: poseSlowmo ? 18 : 6,
        timeLabel: "relative-seconds",
      });
      return;
    }
    actualViewport.setStaticPose(
      poseCompare.actual_landmarks,
      poseCompare.joint_status,
      { caption: "影片中的實際動作" },
    );
  });
}

const phaseActionLabels = {
  spike: "扣球",
  serve: "發球",
  block: "攔網",
  receive: "接球",
  set: "舉球",
};

const phaseLabels = {
  contact: "關鍵觸球",
  crouch: "蓄力準備",
  hit: "擊球瞬間",
  load: "下蹲蓄力",
  serve_contact: "發球擊球瞬間",
  max_reach: "攔網最高點",
  pre_jump: "起跳前蓄力",
  platform_contact: "接球平台觸球",
  set_release: "舉球出手瞬間",
};

const phaseJointLabels = {
  elbow: "手肘",
  knee: "膝蓋",
  shoulder: "肩膀",
  wrist: "手腕",
};

const phaseIssueTips = {
  elbow_bad: "先讓上臂帶動前臂，觸球前再完全打開手肘。",
  elbow_not_straight: "最高點時把手臂往上延伸，不要提早彎手肘。",
  elbow_position_bad: "舉球時雙手維持在額頭上方，手肘不要夾太緊也不要完全鎖死。",
  knee_bad: "膝蓋對齊腳尖，落地或接球時讓膝蓋和髖一起吸收力量。",
  knee_too_bent: "蓄力不要坐太深，讓重心能快速往上或往前轉換。",
  shoulder_low: "觸球前先把肩膀和手臂抬到球的路線上。",
  hands_not_high: "攔網時手掌先過網上方，肩膀跟著往上延伸。",
  wrist_low: "舉球出手點要在額頭上方，不要讓球掉到臉前才推出去。",
  receive_platform_unbalanced: "接球平台兩手高度要一致，先移動腳步再固定前臂。",
  receive_hands_apart: "雙手要先扣好再接球，避免球碰到單邊手臂。",
  lobster_receive_risk: "接球時不要用彎手肘去撈球，容易變成羅波球或讓手肘代償。",
  setting_hands_not_detected: "請讓雙手完整入鏡，舉球判斷才會穩。",
  setting_fingers_closed: "手指打開成碗狀，讓球從指腹離手。",
  setting_hand_spacing_bad: "雙手距離維持在額頭前方一顆球左右。",
  setting_hands_unbalanced: "雙手高度一致，避免球被推出側旋。",
};

function severityLabel(severity) {
  if (severity === "high") return "高風險";
  if (severity === "medium") return "中風險";
  return "低風險";
}

function formatSeconds(value) {
  const seconds = Number(value);
  if (!Number.isFinite(seconds)) return null;
  const start = Number(Math.max(0, seconds).toFixed(1));
  const end = Number((start + 0.1).toFixed(1));
  return `第 ${start.toFixed(1)}-${end.toFixed(1)} 秒`;
}

function issueTimeSummary(item) {
  const times = Array.isArray(item.time_seconds) ? item.time_seconds : [];
  const labels = times.map(formatSeconds).filter(Boolean);
  if (labels.length) return labels.slice(0, 4).join("、");
  const first = formatSeconds(item.first_time_seconds);
  return first || "關鍵動作";
}

function formatDegree(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "--";
  return `${number.toFixed(1).replace(/\.0$/, "")}°`;
}

function formatAcceptedRange(range) {
  if (!Array.isArray(range) || range.length < 2) return "資料集允許範圍";
  return `${formatDegree(range[0])}-${formatDegree(range[1])}`;
}

function phaseLabelFor(action, phaseKey, phasePayload) {
  const raw = phasePayload?.label || phaseKey;
  if (phaseLabels[raw]) return phaseLabels[raw];
  if (action === "spike" && phaseKey === "contact") return "擊球瞬間";
  if (action === "serve" && phaseKey === "contact") return "發球擊球瞬間";
  return phaseLabels[phaseKey] || raw || "關鍵動作";
}

function inferPhaseIssueCode(action, phaseKey, jointKey, jointPayload) {
  if (jointPayload?.issue_code) return jointPayload.issue_code;
  const range = jointPayload?.accepted_range || [];
  const value = Number(jointPayload?.value);
  const high = Number.isFinite(value) && Number.isFinite(range[1]) && value > range[1];
  if (jointKey === "elbow") {
    if (action === "block") return "elbow_not_straight";
    if (action === "set") return "elbow_position_bad";
    return "elbow_bad";
  }
  if (jointKey === "knee") return high ? "knee_bad" : "knee_too_bent";
  if (jointKey === "shoulder") return action === "block" ? "hands_not_high" : "shoulder_low";
  if (jointKey === "wrist") return "wrist_low";
  return `${phaseKey}_${jointKey}`;
}

function issueDirectionLabel(problem) {
  if (problem.direction === "high") return "角度偏大";
  if (problem.direction === "low") return "角度偏小";
  return "角度不在區間";
}

// Describe what is off in plain words, with no angle numbers at all — a player
// wants "手臂抬得不夠高", not "肩膀 25°，建議區間 67.8°-180°". Keyed by the
// issue code, with a direction-based fallback.
const phaseProblemPhrases = {
  shoulder_low: "手臂（肩膀）抬得不夠高",
  hands_not_high: "手舉得不夠高",
  elbow_bad: "手肘太彎、沒有打開",
  elbow_not_straight: "手臂沒有完全伸直",
  elbow_position_bad: "手肘位置沒抓好",
  knee_bad: "膝蓋沒有跟著一起彎、吸震不夠",
  knee_too_bent: "膝蓋彎得太多",
  wrist_low: "手腕位置太低",
};

function plainProblemPhrase(problem) {
  const desc = phaseProblemPhrases[problem.code];
  if (desc) return desc;
  const joint = problem.jointLabel || "這個部位";
  if (problem.direction === "high") return `${joint}的幅度偏大`;
  if (problem.direction === "low") return `${joint}的幅度偏小`;
  return `${joint}需要再調整`;
}

function phaseProblemDetails(phaseAnalysis, result = {}) {
  const details = { hasReference: false, hasProblem: false, times: [], problems: [] };
  if (!phaseAnalysis || phaseAnalysis.mode !== "reference") return details;
  details.hasReference = true;

  const action = result.action || actionInput?.value || "spike";
  const handledCodes = new Set();
  for (const [phaseKey, phasePayload] of Object.entries(phaseAnalysis.phases || {})) {
    const phaseLabel = phaseLabelFor(action, phaseKey, phasePayload);
    const seconds = Number(phasePayload?.time_seconds);
    for (const [jointKey, jointPayload] of Object.entries(phasePayload?.joints || {})) {
      if (!jointPayload?.status || jointPayload.status === "green") continue;
      const code = inferPhaseIssueCode(action, phaseKey, jointKey, jointPayload);
      handledCodes.add(code);
      if (Number.isFinite(seconds)) details.times.push(seconds);
      const problem = {
        code,
        action,
        phaseKey,
        phaseLabel,
        jointKey,
        jointLabel: phaseJointLabels[jointKey] || jointKey,
        value: jointPayload.value,
        acceptedRange: jointPayload.accepted_range,
        tolerance: jointPayload.tolerance,
        direction: jointPayload.direction || "outside",
        time_seconds: Number.isFinite(seconds) ? seconds : null,
        source: jointPayload.source || "reference",
        convergence: jointPayload.convergence,
      };
      details.problems.push(problem);
    }
  }

  const primaryByCode = new Map((result.primary_issues || []).map((item) => [item.code, item]));
  for (const code of phaseAnalysis.issues || []) {
    if (handledCodes.has(code)) continue;
    const original = primaryByCode.get(code);
    const originalTimes = Array.isArray(original?.time_seconds) ? original.time_seconds : [];
    const firstTime = originalTimes[0] ?? original?.first_time_seconds ?? details.times[0] ?? null;
    if (Number.isFinite(Number(firstTime))) details.times.push(Number(firstTime));
    details.problems.push({
      code,
      phaseLabel: "關鍵動作",
      jointLabel: original?.body_part || "手部與平台",
      time_seconds: Number.isFinite(Number(firstTime)) ? Number(firstTime) : null,
      title: original?.title,
      message: original?.message,
      original,
    });
  }

  details.hasProblem = details.problems.length > 0;
  return details;
}

function stablePhasePlan(actionLabel) {
  return {
    status: "stable",
    headline: `${actionLabel}做得很不錯！`,
    focus: "保持這個手感",
    reason: "觸球、蓄力、出手這幾個關鍵瞬間，我都沒挑到明顯要修的地方，這球很穩。",
    next_steps: ["繼續保持全身跟雙手都入鏡。", "用同一個角度再錄一段，看看能不能一樣穩。", "下次可以換側面拍，我們一起看落地跟重心。"],
    video_url: "https://www.youtube.com/results?search_query=volleyball+warm+up+injury+prevention",
  };
}

function phaseAwareIssue(problem, original = {}, actionLabel = "排球") {
  const timeText = formatSeconds(problem.time_seconds) || "關鍵動作";
  const hasAngle = Number.isFinite(Number(problem.value));
  const tip = phaseIssueTips[problem.code] || original.fixes?.[0] || "先放慢動作，確認全身、手部與腳步都完整入鏡。";
  const phrase = plainProblemPhrase(problem);
  const title = problem.title || `${problem.phaseLabel}：${phrase}`;
  const instantCue = hasAngle
    ? `${timeText}：${tip}`
    : `${timeText}：${original.instant_cue || problem.message || "先修正這個動作點"}`;
  const message = hasAngle
    ? `在你${actionLabel}${problem.phaseLabel}的那一刻，${phrase}。放心，我只看這個最關鍵的瞬間，不會整段影片一直挑你毛病。`
    : (problem.message || original.message || "這個問題出現在關鍵動作的那一刻，主要是手部或平台的狀態。");
  const drill = hasAngle
    ? `慢慢做 8 次 ${actionLabel}，做到${problem.phaseLabel}時停一秒，照上面的提示把${problem.jointLabel}調好，不用求快，先把動作做對。`
    : (original.practice_drill || `慢慢做 8 次 ${actionLabel}，先把關鍵動作做穩，再慢慢加速。`);
  const fixes = [
    `把影片停在 ${timeText}，對照左邊 3D 小人的${problem.jointLabel}。`,
    tip,
  ];
  return {
    ...original,
    code: problem.code || original.code,
    title,
    severity: original.severity || (problem.code === "lobster_receive_risk" ? "high" : "medium"),
    count: 1,
    time_seconds: Number.isFinite(Number(problem.time_seconds)) ? [Number(problem.time_seconds)] : [],
    first_time_seconds: Number.isFinite(Number(problem.time_seconds)) ? Number(problem.time_seconds) : null,
    body_part: `${problem.phaseLabel}的${problem.jointLabel}`,
    instant_cue: instantCue,
    message,
    why_it_matters: hasAngle
      ? "這個地方跟標準動作差比較多，把它練順了，球會更穩、更省力，長期下來也比較不容易受傷。"
      : "這個地方練順了，球會更穩，身體也比較省力、不容易受傷。",
    practice_drill: drill,
    fixes,
    video_url:
      original.video_url ||
      `https://www.youtube.com/results?search_query=${encodeURIComponent(`volleyball ${actionLabel} form ${problem.jointLabel}`)}`,
  };
}

function phaseAwareCoachSummary(details, actionLabel) {
  const first = details.problems[0];
  const timeText = formatSeconds(first.time_seconds) || "關鍵動作";
  const phrase = plainProblemPhrase(first);
  const tip = phaseIssueTips[first.code];
  const base = `我幫你看完囉！這球最需要先調整的，是${actionLabel}${first.phaseLabel}（大約 ${timeText}）的時候，${phrase}。`;
  const how = tip ? tip : "可以對照左邊的 3D 小人，看它跟你差在哪，跟著調就好。";
  return `${base}${how}先把這一個地方練起來，其他不用急，抓到這個關鍵瞬間，你會進步很多。`;
}

function phaseAwareCoachPlan(details, actionLabel) {
  const first = details.problems[0];
  const timeText = formatSeconds(first.time_seconds) || "關鍵動作";
  const phrase = plainProblemPhrase(first);
  return {
    status: "needs_fix",
    headline: `我們先從這裡開始：${first.phaseLabel}的${first.jointLabel}`,
    focus: "這一次的練習重點",
    reason: first.code
      ? `${timeText}那一下，${phrase}，我們先把這裡調順。`
      : `${timeText}的手部或平台有點不穩，先用慢動作看一下、慢慢喬。`,
    next_steps: [
      `把影片停在 ${timeText}，跟左邊的 3D 小人比一比，看差在哪。`,
      phaseIssueTips[first.code] || "先放慢速度，把關鍵姿勢做對，再慢慢加快。",
      `調好之後，再錄一段 5 到 10 秒，全身跟雙手都入鏡，我們一起看看有沒有變好。`,
    ],
    video_url: `https://www.youtube.com/results?search_query=${encodeURIComponent(`volleyball ${actionLabel} technique slow motion`)}`,
  };
}

function normalizePhaseAwareResult(result) {
  if (!result || !result.phase_analysis) return result;
  const details = phaseProblemDetails(result.phase_analysis, result);
  if (!details.hasReference) return result;

  const actionLabel = result.action_label || phaseActionLabels[result.action] || "排球動作";
  if (!details.hasProblem) {
    return {
      ...result,
      primary_issues: [],
      coach_summary: `這球${actionLabel}做得很不錯！觸球、蓄力、出手這幾個關鍵瞬間我都沒挑到明顯問題，保持下去。`,
      coach_plan: stablePhasePlan(actionLabel),
    };
  }

  const originalByCode = new Map((result.primary_issues || []).map((item) => [item.code, item]));
  const primary_issues = details.problems.map((problem) =>
    phaseAwareIssue(problem, originalByCode.get(problem.code) || problem.original || {}, actionLabel),
  );
  return {
    ...result,
    primary_issues,
    coach_summary: phaseAwareCoachSummary(details, actionLabel),
    coach_plan: phaseAwareCoachPlan(details, actionLabel),
  };
}

function renderResult(result) {
  result = normalizePhaseAwareResult(result);
  summaryTitle.textContent = `${result.action_label} 分析結果`;
  coachSummary.textContent = result.coach_summary;
  frameCount.textContent = `已用 0.1 秒為單位完成分析`;
  renderCoachPlan(result.coach_plan);
  renderIssues(result.primary_issues);
  renderPoseCompare(result.pose_compare, result.action);
  // Low-quality hint: nudge toward 高精度 unless already on it (UC004).
  if (qualityHint) qualityHint.hidden = powerModeInput?.value === "quality";
}

function renderIssues(items) {
  issues.innerHTML = "";
  issues.classList.remove("empty");

  if (!items || items.length === 0) {
    issues.classList.add("empty");
    issues.textContent = "目前沒有偵測到明顯錯誤；請保持全身、手部與腳步完整入鏡。";
    return;
  }

  for (const item of items) {
    const card = document.createElement("article");
    card.className = `issue-card ${item.severity}`;
    card.innerHTML = `
      <div class="issue-title">
        <span>${escapeHtml(item.title)}</span>
        <small>${severityLabel(item.severity)}・${escapeHtml(issueTimeSummary(item))}</small>
      </div>
      <div class="issue-meta">
        <span>${escapeHtml(item.body_part || "關鍵動作")}</span>
        <strong>${escapeHtml(item.instant_cue || "先修正最明顯的一點")}</strong>
      </div>
      <p>${escapeHtml(item.message)}</p>
      <p class="issue-why">${escapeHtml(item.why_it_matters || "")}</p>
      <div class="drill-box">${escapeHtml(item.practice_drill || "")}</div>
      <ul class="fix-list">${(item.fixes || []).map((fix) => `<li>${escapeHtml(fix)}</li>`).join("")}</ul>
      <a class="video-link" href="${item.video_url}" target="_blank" rel="noreferrer">觀看修正影片</a>
    `;
    issues.appendChild(card);
  }
}

if (typeof window !== "undefined") {
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    if (installAppBtn) installAppBtn.hidden = false;
  });

  window.addEventListener("appinstalled", () => {
    deferredInstallPrompt = null;
    if (installAppBtn) installAppBtn.hidden = true;
  });

  window.addEventListener("pagehide", () => {
    stopLiveAnalysis(false);
    stopMediaStream();
    actualViewport?.dispose();
    demoViewport?.dispose();
  });
}

if (typeof document !== "undefined") {
  document.addEventListener?.("visibilitychange", () => {
    if (document.hidden && liveAnalysisActive) stopLiveAnalysis();
  });
}

installAppBtn?.addEventListener("click", async () => {
  if (!deferredInstallPrompt) return;
  deferredInstallPrompt.prompt();
  await deferredInstallPrompt.userChoice;
  deferredInstallPrompt = null;
  installAppBtn.hidden = true;
});

if (typeof navigator !== "undefined" && "serviceWorker" in navigator) {
  let swRefreshing = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (swRefreshing) return;
    swRefreshing = true;
    window.location.reload();
  });
  navigator.serviceWorker.register(`./service-worker.js?v=${APP_BUILD}`, { updateViaCache: "none" }).catch(() => {
    // The app still works online when service worker registration is unavailable.
  });
}

renderActionOptions(fallbackActions);
renderModalityOptions(fallbackModalities);
updateAnalysisSummary();
checkHealth();
