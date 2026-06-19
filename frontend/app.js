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
const score = document.querySelector("#score");
const summaryTitle = document.querySelector("#summaryTitle");
const coachSummary = document.querySelector("#coachSummary");
const coachPlan = document.querySelector("#coachPlan");
const frameCount = document.querySelector("#frameCount");
const issues = document.querySelector("#issues");
const timeline = document.querySelector("#timeline");
const dropZone = document.querySelector("#dropZone");
const modalityList = document.querySelector("#modalityList");
const modalityResults = document.querySelector("#modalityResults");
const recordPreview = document.querySelector("#recordPreview");
const recordStatus = document.querySelector("#recordStatus");
const startRecordBtn = document.querySelector("#startRecordBtn");
const stopRecordBtn = document.querySelector("#stopRecordBtn");
const clearRecordBtn = document.querySelector("#clearRecordBtn");

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

async function checkHealth() {
  persistBackendUrl();
  serverStatus.textContent = "檢查中";
  serverStatus.classList.remove("ok", "bad");
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
  fileName.textContent = file ? file.name : "支援 mp4、mov、webm，最大 180MB";
  if (file) {
    showVideoPreview(file);
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
    : `${actionLabel} · 尚未選擇影片`;
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
  showVideoPreview(file);
  updateAnalysisSummary();
});

startRecordBtn.addEventListener("click", startRecording);
stopRecordBtn.addEventListener("click", stopRecording);
clearRecordBtn.addEventListener("click", clearRecording);

async function startRecording() {
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    recordStatus.textContent = "這個瀏覽器不支援直接錄影，請改用上傳影片分析。";
    return;
  }

  try {
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
  showVideoPreview(file);
  stopMediaStream();
  mediaRecorder = null;
  startRecordBtn.disabled = false;
  stopRecordBtn.disabled = true;
  clearRecordBtn.disabled = false;
  recordStatus.textContent = "錄影完成，可以先回放確認，再按開始分析。";
}

function clearRecording() {
  clearRecordingTimer();
  recordedChunks = [];
  clearRecordedUrl();
  stopMediaStream();
  videoInput.value = "";
  recordPreview.removeAttribute("src");
  recordPreview.srcObject = null;
  recordPreview.controls = false;
  previewPlaceholder?.classList.remove("hidden");
  fileName.textContent = "支援 mp4、mov、webm，最大 180MB";
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

function showVideoPreview(file) {
  clearRecordedUrl();
  recordedVideoUrl = URL.createObjectURL(file);
  recordPreview.srcObject = null;
  recordPreview.src = recordedVideoUrl;
  recordPreview.controls = true;
  recordPreview.muted = false;
  previewPlaceholder?.classList.add("hidden");
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
    coachSummary.textContent = "請先錄影或上傳一段影片。";
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
  timeline.textContent = "分析完成後會顯示時間軸";
  modalityResults.textContent = "正在整理模組結果";

  try {
    if (backendAvailable) {
      const response = await fetch(apiUrl("/api/analyze"), {
        method: "POST",
        body: form,
      });
      const payload = await response.json();
      if (!payload.ok) throw new Error(payload.error || "分析失敗");
      renderResult(payload.result);
    } else {
      const { analyzeVideoLocally } = await import("./local-analyzer.js");
      const result = await analyzeVideoLocally({
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
    timeline.textContent = "";
    modalityResults.textContent = "";
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "開始 AI 分析";
  }
});

function renderResult(result) {
  score.textContent = `${result.score}`;
  summaryTitle.textContent = `${result.action_label} 分析完成`;
  coachSummary.textContent = result.coach_summary;
  frameCount.textContent = `${result.processed_frames} 影格已分析`;
  renderCoachPlan(result.coach_plan);
  renderIssues(result.primary_issues);
  renderTimeline(result.timeline);
  renderModalityResults(result);
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

function renderTimeline(items) {
  timeline.innerHTML = "";
  timeline.classList.remove("empty");

  if (!items || items.length === 0) {
    timeline.classList.add("empty");
    timeline.textContent = "沒有足夠影格可以建立時間軸。";
    return;
  }

  for (const item of items) {
    const box = document.createElement("div");
    box.className = "time-item";
    const text = item.ok ? "動作穩定" : item.issues.map((issue) => issue.title).join("、");
    box.innerHTML = `<strong>第 ${item.frame} 影格</strong><span>${escapeHtml(text)}</span>`;
    timeline.appendChild(box);
  }
}

function renderModalityResults(result) {
  const statuses = result.modalities || [];
  const values = result.modality_results || {};
  modalityResults.innerHTML = "";
  modalityResults.classList.remove("empty");

  for (const item of statuses) {
    const card = document.createElement("div");
    card.className = `modality-result ${item.state}`;
    const metric = metricText(item.id, values[item.id], values.reserved);
    card.innerHTML = `
      <strong>${escapeHtml(item.label)}</strong>
      <span>${stateLabel(item.state)}</span>
      <p>${escapeHtml(metric || item.description)}</p>
    `;
    modalityResults.appendChild(card);
  }
}

function metricText(id, value, reserved) {
  if (id === "pose" && value) {
    return `骨架影格 ${value.frames_with_pose}，平均手肘角 ${value.average_elbow_angle ?? "--"} 度，平均膝蓋角 ${value.average_knee_angle ?? "--"} 度。`;
  }
  if (id === "hands" && value) {
    return `手部影格 ${value.frames_with_hands}，平均手指伸展 ${value.average_finger_extension ?? "--"}，平均雙手距離 ${value.average_hand_gap ?? "--"}。`;
  }
  if (reserved && reserved[id]) return reserved[id];
  return "";
}

function stateLabel(state) {
  if (state === "active") return "已啟用";
  if (state === "reserved") return "已預留";
  if (state === "future") return "未來模組";
  return "可用";
}

function severityLabel(severity) {
  if (severity === "high") return "高優先";
  if (severity === "medium") return "中優先";
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
}

installAppBtn?.addEventListener("click", async () => {
  if (!deferredInstallPrompt) return;
  deferredInstallPrompt.prompt();
  await deferredInstallPrompt.userChoice;
  deferredInstallPrompt = null;
  installAppBtn.hidden = true;
});

if (typeof navigator !== "undefined" && "serviceWorker" in navigator) {
  navigator.serviceWorker.register("./service-worker.js").catch(() => {
    // The app still works online when service worker registration is unavailable.
  });
}

renderActionOptions(fallbackActions);
renderModalityOptions(fallbackModalities);
updateAnalysisSummary();
checkHealth();
