import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

class ClassList {
  constructor(element) {
    this.element = element;
    this.values = new Set();
  }

  add(...names) {
    for (const name of names) {
      if (name) this.values.add(name);
    }
    this._sync();
  }

  remove(...names) {
    for (const name of names) {
      this.values.delete(name);
    }
    this._sync();
  }

  contains(name) {
    return this.values.has(name);
  }

  _sync() {
    this.element._className = [...this.values].join(" ");
  }
}

class FakeElement {
  constructor(tagName, id = "") {
    this.tagName = tagName.toUpperCase();
    this.id = id;
    this.children = [];
    this.parentNode = null;
    this.events = {};
    this.attributes = {};
    this.dataset = {};
    this._className = "";
    this._innerHTML = "";
    this.textContent = "";
    this.value = "";
    this.checked = false;
    this.disabled = false;
    this.files = [];
    this.title = "";
    this.classList = new ClassList(this);
  }

  set className(value) {
    this._className = value;
    this.classList.values = new Set(String(value).split(/\s+/).filter(Boolean));
  }

  get className() {
    return this._className;
  }

  set innerHTML(value) {
    this._innerHTML = String(value);
    this.textContent = "";
    if (value === "") {
      this.children = [];
    }
    if (this.tagName === "LABEL") {
      this._parseLabelInput(this._innerHTML);
    }
  }

  get innerHTML() {
    return this._innerHTML;
  }

  get options() {
    return this.children.filter((child) => child.tagName === "OPTION");
  }

  appendChild(child) {
    child.parentNode = this;
    this.children.push(child);
    return child;
  }

  addEventListener(name, handler) {
    this.events[name] = handler;
  }

  getContext(type) {
    if (type !== "2d") return null;
    if (!this._context2d) {
      this._context2d = {
        canvas: this,
        lineCap: "",
        lineJoin: "",
        lineWidth: 1,
        strokeStyle: "",
        fillStyle: "",
        clearRect() {},
        beginPath() {},
        closePath() {},
        moveTo() {},
        lineTo() {},
        stroke() {},
        arc() {},
        fill() {},
      };
    }
    return this._context2d;
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  querySelectorAll(selector) {
    const matches = [];
    const visit = (element) => {
      for (const child of element.children) {
        if (selector === "input:checked" && child.tagName === "INPUT" && child.checked) {
          matches.push(child);
        }
        if (selector === "[data-action]" && child.dataset.action) {
          matches.push(child);
        }
        visit(child);
      }
    };
    visit(this);
    return matches;
  }

  _parseLabelInput(html) {
    const inputMatch = html.match(/<input[^>]*value="([^"]+)"([^>]*)>/);
    if (!inputMatch) return;
    const input = new FakeElement("input");
    input.value = inputMatch[1];
    input.checked = inputMatch[0].includes("checked");
    this.appendChild(input);
  }
}

class FakeDocument {
  constructor(ids) {
    this.elements = new Map();
    for (const id of ids) {
      this.elements.set(id, new FakeElement("div", id));
    }
    this.elements.get("action").tagName = "SELECT";
    this.elements.get("powerMode").tagName = "SELECT";
    this.elements.get("video").tagName = "INPUT";
    this.elements.get("analyzeBtn").tagName = "BUTTON";
    this.elements.get("sameOriginBtn").tagName = "BUTTON";
    this.elements.get("localBackendBtn").tagName = "BUTTON";
    this.elements.get("healthCheckBtn").tagName = "BUTTON";
    this.elements.get("recordPreview").tagName = "VIDEO";
    this.elements.get("imagePreview").tagName = "IMG";
    this.elements.get("poseOverlay").tagName = "CANVAS";
    this.elements.get("startLiveBtn").tagName = "BUTTON";
    this.elements.get("stopLiveBtn").tagName = "BUTTON";
    this.elements.get("startRecordBtn").tagName = "BUTTON";
    this.elements.get("stopRecordBtn").tagName = "BUTTON";
    this.elements.get("clearRecordBtn").tagName = "BUTTON";
    this.elements.get("modalityList").tagName = "DIV";
    this.elements.get("actionChoices").tagName = "DIV";
    this.elements.get("installAppBtn").tagName = "BUTTON";
    this.elements.get("poseViewToggle").tagName = "DIV";
    this.elements.get("poseCompareActual").tagName = "CANVAS";
    this.elements.get("poseCompareCorrected").tagName = "CANVAS";
    this.elements.get("shareQrBtn").tagName = "BUTTON";
    this.elements.get("qrModal").tagName = "DIV";
    this.elements.get("qrModalClose").tagName = "BUTTON";
    this.elements.get("qrCodeContainer").tagName = "DIV";
    this.elements.get("qrCodeUrl").tagName = "P";
    this.head = new FakeElement("head");
  }

  querySelector(selector) {
    if (!selector.startsWith("#")) return null;
    return this.elements.get(selector.slice(1));
  }

  createElement(tagName) {
    return new FakeElement(tagName);
  }
}

function makeContext() {
  const ids = [
    "serverStatus",
    "analyzeBtn",
    "backendUrl",
    "sameOriginBtn",
    "localBackendBtn",
    "healthCheckBtn",
    "connectionNote",
    "action",
    "actionChoices",
    "powerMode",
    "video",
    "fileName",
    "previewPlaceholder",
    "analysisSummary",
    "installAppBtn",
    "shareQrBtn",
    "qrModal",
    "qrModalClose",
    "qrCodeContainer",
    "qrCodeUrl",
    "summaryTitle",
    "coachSummary",
    "coachPlan",
    "frameCount",
    "issues",
    "poseViewToggle",
    "poseCompareActual",
    "poseCompareCorrected",
    "poseCompareNote",
    "poseErrorSkeleton",
    "poseErrorSkeletonCanvas",
    "dropZone",
    "modalityList",
    "recordPreview",
    "imagePreview",
    "poseOverlay",
    "liveFeedback",
    "liveStatus",
    "liveCue",
    "liveMetrics",
    "recordStatus",
    "startLiveBtn",
    "stopLiveBtn",
    "startRecordBtn",
    "stopRecordBtn",
    "clearRecordBtn",
  ];
  const document = new FakeDocument(ids);
  const calls = [];
  const storage = new Map();
  const context = {
    document,
    calls,
    console,
    setTimeout,
    clearTimeout,
    localStorage: {
      getItem: (key) => storage.get(key) || "",
      setItem: (key, value) => storage.set(key, String(value)),
    },
    location: {
      // The local launcher serves the frontend from 127.0.0.1 with a real
      // same-origin backend, so the capabilities probe is expected to run.
      // (A static host like *.github.io skips the probe — covered separately.)
      href: "http://127.0.0.1:8000/",
      search: "",
      hostname: "127.0.0.1",
    },
    URL,
    URLSearchParams,
    FormData: class FakeFormData {
      constructor() {
        this.fields = [];
      }
      append(name, value) {
        this.fields.push([name, value]);
      }
    },
    fetch: async (url) => {
      calls.push(url);
      if (url === "./runtime-share.json") {
        return {
          ok: true,
          json: async () => ({
            publicUrl: "https://chiuwwyne-cyber.github.io/volleyform-ai-coach/",
            preferredUrl: "https://chiuwwyne-cyber.github.io/volleyform-ai-coach/",
          }),
        };
      }
      return {
        ok: true,
        json: async () => ({
          ok: true,
          capabilities: {
            actions: [
              { id: "receive", label: "Receive" },
              { id: "set", label: "Set" },
            ],
            modalities: [
              {
                id: "pose",
                label: "Pose",
                available: true,
                requested: true,
                state: "active",
                description: "Body pose",
              },
              {
                id: "ball",
                label: "Ball",
                available: false,
                requested: false,
                state: "future",
                description: "Reserved ball tracking",
              },
            ],
          },
        }),
      };
    },
  };
  context.globalThis = context;
  return context;
}

async function main() {
  const appPath = path.join(process.cwd(), "frontend", "app.js");
  const pose3dPath = path.join(process.cwd(), "frontend", "pose-3d.js");
  const source = `${fs.readFileSync(appPath, "utf8")}
globalThis.__appTestApi = { apiUrl, checkHealth, renderResult, selectedModalities, resolveShareUrl };`;
  const poseSource = fs.readFileSync(pose3dPath, "utf8");
  const context = makeContext();
  context.__pose3dLoader = async () => ({
    createPoseViewport: () => ({
      setStaticPose() {},
      playDemo() {},
      setView() {},
      resize() {},
      dispose() {},
    }),
  });
  vm.createContext(context);
  vm.runInContext(source, context, { filename: "frontend/app.js" });
  await new Promise((resolve) => setTimeout(resolve, 0));

  const action = context.document.querySelector("#action");
  assert.deepEqual(action.options.map((option) => option.value), ["receive", "set"]);
  assert.equal(context.document.querySelector("#actionChoices").children.length, 2);
  assert.equal(context.document.querySelector("#serverStatus").textContent, "已連線");
  assert.equal(context.calls[0], "/api/capabilities");
  assert.equal(JSON.stringify(context.__appTestApi.selectedModalities()), JSON.stringify(["pose"]));
  assert.equal(typeof context.document.querySelector("#sameOriginBtn").events.click, "function");
  assert.equal(typeof context.document.querySelector("#localBackendBtn").events.click, "function");
  assert.equal(typeof context.document.querySelector("#healthCheckBtn").events.click, "function");
  assert.equal(typeof context.document.querySelector("#startRecordBtn").events.click, "function");
  assert.equal(typeof context.document.querySelector("#startLiveBtn").events.click, "function");
  assert.equal(typeof context.document.querySelector("#stopLiveBtn").events.click, "function");
  assert.equal(typeof context.document.querySelector("#stopRecordBtn").events.click, "function");
  assert.equal(typeof context.document.querySelector("#clearRecordBtn").events.click, "function");
  assert.equal(typeof context.document.querySelector("#poseViewToggle").events.click, "function");
  assert.match(source, /maxRecordingMs = 12000/);
  assert.match(source, /recordingVideoBitsPerSecond = 1600000/);
  assert.match(source, /process_width: "480"/);
  assert.match(source, /runtimeConfig\.apiBase/);
  assert.match(source, /serviceWorker\.register/);
  assert.match(source, /analyzeMediaLocally/);
  assert.match(source, /startRealtimeAnalysis/);
  assert.match(source, /playbackSeconds:\s*poseSlowmo \? 18 : 6/);
  assert.match(source, /timeLabel:\s*"relative-seconds"/);
  assert.match(poseSource, /relativeSecondCaption/);
  assert.match(poseSource, /第 \$\{second\} 秒/);
  assert.match(poseSource, /constrainHumanProportions\(points\)/);
  for (const phase of [
    "block_press",
    "serve_contact",
    "receive_platform",
    "set_release",
    "spikePhase",
  ]) {
    assert.match(poseSource, new RegExp(phase));
  }
  assert.match(poseSource, /frameBallPoint/);
  assert.match(poseSource, /shapeBlockBiomechanics/);
  assert.match(poseSource, /shapeServeBiomechanics/);
  assert.match(poseSource, /SET_SIDE_ANGLE_DEG/);
  assert.match(poseSource, /turnWholePoseSideways\(points,\s*SET_SIDE_ANGLE_DEG\)/);
  assert.match(poseSource, /setReleaseBallPoint/);
  assert.match(poseSource, /ballAttach:\s*"set_release"/);
  assert.doesNotMatch(poseSource, /actionPhase:\s*"set_(?:ready|catch|cushion|release|recover)"[^}]*root:/);
  assert.match(poseSource, /frameCamera\(bounds,\s*camera\.fov,\s*framePadding,\s*camera\.aspect\)/);
  assert.match(poseSource, /camera\.position\.set\(lookTarget\.x/);
  assert.match(poseSource, /renderer\.domElement\.style\.width/);
  assert.match(poseSource, /renderer\.domElement\.style\.height/);
  assert.doesNotMatch(poseSource, /actualShapeVariant/);
  assert.doesNotMatch(poseSource, /applyActionShape\(points,\s*action,\s*"mistake"/);

  const backendUrl = context.document.querySelector("#backendUrl");
  backendUrl.value = "http://192.168.1.10:8000/";
  assert.equal(context.__appTestApi.apiUrl("/api/analyze"), "http://192.168.1.10:8000/api/analyze");
  await context.__appTestApi.checkHealth();
  assert.equal(context.calls.at(-1), "http://192.168.1.10:8000/api/capabilities");
  const qrShareUrl = await context.__appTestApi.resolveShareUrl();
  assert.match(qrShareUrl, /^https:\/\/chiuwwyne-cyber\.github\.io\/volleyform-ai-coach\//);
  assert.match(qrShareUrl, /backend=http%3A%2F%2F192\.168\.1\.10%3A8000/);
  assert.doesNotMatch(qrShareUrl, /127\.0\.0\.1/);

  // On a static public host (GitHub Pages) with no configured backend, the app
  // must skip both same-origin probes so the console stays free of 404s.
  context.location.hostname = "chiuwwyne-cyber.github.io";
  context.location.href = "https://chiuwwyne-cyber.github.io/volleyform-ai-coach/";
  backendUrl.value = "";
  context.calls.length = 0;
  await context.__appTestApi.checkHealth();
  assert.ok(
    !context.calls.includes("/api/capabilities"),
    "static public host should not probe same-origin /api/capabilities",
  );
  assert.equal(context.document.querySelector("#serverStatus").textContent, "手機本地");
  const staticShareUrl = await context.__appTestApi.resolveShareUrl();
  assert.ok(
    !context.calls.includes("./runtime-share.json"),
    "static public host should not fetch runtime-share.json",
  );
  assert.match(staticShareUrl, /^https:\/\/chiuwwyne-cyber\.github\.io\/volleyform-ai-coach\//);

  context.__appTestApi.renderResult({
    action_label: "Receive",
    processed_frames: 24,
    coach_summary: "Fix the platform first.",
    coach_plan: {
      status: "needs_fix",
      headline: "Fix platform",
      focus: "Forearm platform",
      reason: "Soft platform sends the ball away.",
      next_steps: ["Lock elbows", "Move behind the ball"],
      video_url: "https://example.com/video",
    },
    primary_issues: [
      {
        title: "Platform too soft",
        severity: "high",
        count: 3,
        time_seconds: [1.2, 3.4],
        first_time_seconds: 1.2,
        body_part: "Forearms",
        instant_cue: "Lock elbows",
        message: "The platform is unstable.",
        why_it_matters: "The ball can rebound sideways.",
        practice_drill: "Hold platform shape for 10 reps.",
        fixes: ["Straighten elbows", "Move feet first"],
        video_url: "https://example.com/fix",
      },
    ],
    pose_compare: {
      available: true,
      joint_status: { elbow: "yellow", knee: "green", shoulder: "green", wrist: "green" },
      actual_landmarks: Array.from({ length: 33 }, (_, index) => [index * 0.01, index * 0.02, 0]),
      corrected_landmarks: Array.from({ length: 33 }, (_, index) => [index * 0.01, index * 0.02, 0]),
    },
    modalities: [
      {
        id: "pose",
        label: "Pose",
        state: "active",
        description: "Body pose",
      },
    ],
    modality_results: {
      pose: {
        frames_with_pose: 24,
        average_elbow_angle: 160,
        average_knee_angle: 120,
      },
      reserved: {},
    },
  });

  // The 2D error-frame skeleton must actually be revealed. Its only caller used
  // to sit in a shadowed copy of renderPoseCompare, so the feature shipped,
  // was documented as verified, and never ran for a single user.
  assert.equal(context.document.querySelector("#poseErrorSkeleton").hidden, false,
    "error-frame skeleton must be shown when a pose comparison is available");
  assert.match(context.document.querySelector("#poseCompareNote").textContent, /紅色是高風險/);
  assert.match(context.document.querySelector("#poseCompareNote").textContent, /正確慢動作/);
  assert.match(context.document.querySelector("#coachPlan").innerHTML, /Forearm platform/);
  assert.match(context.document.querySelector("#coachPlan").innerHTML, /Lock elbows/);
  const issueCard = context.document.querySelector("#issues").children[0];
  assert.match(issueCard.innerHTML, /Forearms/);
  assert.match(issueCard.innerHTML, /Hold platform shape/);
  assert.match(issueCard.innerHTML, /第 1\.2-1\.3 秒/);
  assert.doesNotMatch(issueCard.innerHTML, /影格/);

  context.__appTestApi.renderResult({
    action: "spike",
    action_label: "扣球",
    processed_frames: 193,
    coach_summary: "Old frame-by-frame result should be rewritten.",
    coach_plan: {
      status: "needs_fix",
      headline: "Old warning",
      focus: "Old count",
      reason: "Old count",
      next_steps: ["Old count"],
      video_url: "https://example.com/old",
    },
    primary_issues: [
      {
        code: "elbow_bad",
        title: "Old elbow warning",
        severity: "medium",
        count: 144,
        body_part: "Elbow",
        instant_cue: "Old cue",
        message: "Old count should disappear.",
        why_it_matters: "Old count",
        practice_drill: "Old count",
        fixes: ["Old count"],
        video_url: "https://example.com/old",
      },
      {
        code: "knee_bad",
        title: "Old knee warning",
        severity: "medium",
        count: 124,
        body_part: "Knee",
        instant_cue: "Old cue",
        message: "Old count should disappear.",
        why_it_matters: "Old count",
        practice_drill: "Old count",
        fixes: ["Old count"],
        video_url: "https://example.com/old",
      },
    ],
    phase_analysis: {
      mode: "reference",
      issues: ["elbow_bad", "knee_bad"],
      phases: {
        contact: {
          label: "hit",
          time_seconds: 5.7,
          joints: {
            elbow: {
              status: "red",
              value: 118,
              accepted_range: [140, 180],
              tolerance: 22,
              issue_code: "elbow_bad",
              direction: "low",
              source: "reference",
            },
          },
        },
        crouch: {
          label: "load",
          time_seconds: 2.5,
          joints: {
            knee: {
              status: "red",
              value: 176,
              accepted_range: [77, 168],
              tolerance: 20,
              issue_code: "knee_bad",
              direction: "high",
              source: "reference",
            },
          },
        },
      },
    },
    pose_compare: { available: false },
  });
  const phaseIssueCards = context.document.querySelector("#issues").children;
  const phaseIssueCard = phaseIssueCards[0];
  const phaseKneeCard = phaseIssueCards[1];
  assert.equal(phaseIssueCards.length, 2);
  phaseIssueCard.innerHTML += phaseKneeCard.innerHTML;
  assert.match(context.document.querySelector("#coachSummary").textContent, /最需要先調整/);
  assert.match(phaseIssueCard.innerHTML, /擊球瞬間/);
  assert.match(phaseIssueCard.innerHTML, /第 5\.7-5\.8 秒/);
  assert.match(phaseIssueCard.innerHTML, /膝蓋/);
  assert.match(phaseIssueCard.innerHTML, /膝蓋對齊腳尖/);
  // No angle numbers should leak into the user-facing copy anymore.
  assert.doesNotMatch(phaseIssueCard.innerHTML, /144|118|°|Old count|Old cue/);

  context.__appTestApi.renderResult({
    action: "spike",
    action_label: "扣球",
    processed_frames: 193,
    coach_summary: "Old frame-by-frame result should be ignored.",
    coach_plan: {
      status: "needs_fix",
      headline: "Old warning",
      focus: "Old count",
      reason: "Old count",
      next_steps: ["Old count"],
      video_url: "https://example.com/old",
    },
    primary_issues: [
      {
        title: "Elbow warning",
        severity: "medium",
        count: 144,
        body_part: "Elbow",
        instant_cue: "Old cue",
        message: "Old count should disappear.",
        why_it_matters: "Old count",
        practice_drill: "Old count",
        fixes: ["Old count"],
        video_url: "https://example.com/old",
      },
    ],
    phase_analysis: {
      mode: "reference",
      phases: {
        contact: {
          time_seconds: 5.7,
          joints: {
            elbow: { status: "green" },
            shoulder: { status: "green" },
          },
        },
        crouch: {
          time_seconds: 2.5,
          joints: {
            knee: { status: "green" },
          },
        },
      },
    },
    pose_compare: { available: false },
  });
  assert.equal(context.document.querySelector("#issues").children.length, 0);
  assert.doesNotMatch(context.document.querySelector("#issues").textContent, /144/);
  assert.match(context.document.querySelector("#coachSummary").textContent, /沒挑到明顯問題/);

  console.log("frontend behavior ok");
  console.log(`fetch calls: ${context.calls.length}`);
  console.log(`rendered issue cards: ${context.document.querySelector("#issues").children.length}`);
}

await main();
