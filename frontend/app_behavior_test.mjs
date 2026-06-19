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
    this.elements.get("startRecordBtn").tagName = "BUTTON";
    this.elements.get("stopRecordBtn").tagName = "BUTTON";
    this.elements.get("clearRecordBtn").tagName = "BUTTON";
    this.elements.get("modalityList").tagName = "DIV";
    this.elements.get("actionChoices").tagName = "DIV";
    this.elements.get("installAppBtn").tagName = "BUTTON";
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
    "score",
    "summaryTitle",
    "coachSummary",
    "coachPlan",
    "frameCount",
    "issues",
    "timeline",
    "dropZone",
    "modalityList",
    "modalityResults",
    "recordPreview",
    "recordStatus",
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
  const source = `${fs.readFileSync(appPath, "utf8")}
globalThis.__appTestApi = { apiUrl, checkHealth, renderResult, selectedModalities };`;
  const context = makeContext();
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
  assert.equal(typeof context.document.querySelector("#stopRecordBtn").events.click, "function");
  assert.equal(typeof context.document.querySelector("#clearRecordBtn").events.click, "function");
  assert.match(source, /maxRecordingMs = 12000/);
  assert.match(source, /recordingVideoBitsPerSecond = 1600000/);
  assert.match(source, /process_width: "480"/);
  assert.match(source, /runtimeConfig\.apiBase/);
  assert.match(source, /serviceWorker\.register/);

  const backendUrl = context.document.querySelector("#backendUrl");
  backendUrl.value = "http://192.168.1.10:8000/";
  assert.equal(context.__appTestApi.apiUrl("/api/analyze"), "http://192.168.1.10:8000/api/analyze");
  await context.__appTestApi.checkHealth();
  assert.equal(context.calls.at(-1), "http://192.168.1.10:8000/api/capabilities");

  context.__appTestApi.renderResult({
    action_label: "Receive",
    score: 42,
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
        body_part: "Forearms",
        instant_cue: "Lock elbows",
        message: "The platform is unstable.",
        why_it_matters: "The ball can rebound sideways.",
        practice_drill: "Hold platform shape for 10 reps.",
        fixes: ["Straighten elbows", "Move feet first"],
        video_url: "https://example.com/fix",
      },
    ],
    timeline: [
      {
        frame: 8,
        ok: false,
        issues: [{ title: "Platform too soft" }],
      },
    ],
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

  assert.equal(context.document.querySelector("#score").textContent, "42");
  assert.match(context.document.querySelector("#coachPlan").innerHTML, /Forearm platform/);
  assert.match(context.document.querySelector("#coachPlan").innerHTML, /Lock elbows/);
  const issueCard = context.document.querySelector("#issues").children[0];
  assert.match(issueCard.innerHTML, /Forearms/);
  assert.match(issueCard.innerHTML, /Hold platform shape/);
  const modalityCard = context.document.querySelector("#modalityResults").children[0];
  assert.match(modalityCard.innerHTML, /Pose/);

  console.log("frontend behavior ok");
  console.log(`fetch calls: ${context.calls.length}`);
  console.log(`rendered issue cards: ${context.document.querySelector("#issues").children.length}`);
}

await main();
