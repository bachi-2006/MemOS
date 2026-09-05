export const EMBED_DEFAULT = "nomic-embed-text";
export const STATE_KEY = "qwen-state-v1";
export const THEME_KEY = "qwen-theme";

export function defaultSettings() {
  return {
    sessions: [],
    currentId: null,
    activeModel: "",
    temp: 0.7,
    numPredict: 512,
    windowN: 12,
    systemPrompt: "",
    compute: "cpu",
    thinking: false,
  };
}

export function loadSettings() {
  const s = defaultSettings();
  try {
    const raw = sessionStorage.getItem(STATE_KEY);
    if (raw) Object.assign(s, JSON.parse(raw));
  } catch {}
  return s;
}

export function saveSettings(s) {
  try {
    sessionStorage.setItem(
      STATE_KEY,
      JSON.stringify({
        sessions: s.sessions,
        currentId: s.currentId,
        activeModel: s.activeModel,
        temp: s.temp,
        numPredict: s.numPredict,
        windowN: s.windowN,
        systemPrompt: s.systemPrompt,
        compute: s.compute,
        thinking: s.thinking,
      })
    );
  } catch {}
}

export const memCfg = {
  get recall() { return localStorage.getItem("memos-recall") !== "off"; },
  get autoExtract() { return localStorage.getItem("memos-extract") !== "off"; },
  get conflictCheck() { return localStorage.getItem("memos-conflict") !== "off"; },
  get embedModel() { return localStorage.getItem("memos-embed") || EMBED_DEFAULT; },
  get extractModel() { return (localStorage.getItem("memos-extract-model") || "").trim(); },
  get topK() { return parseInt(localStorage.getItem("memos-topk") || "4", 10) || 4; },
  get recallThreshold() { return 0.32; },
  get compressDays() { return parseInt(localStorage.getItem("memos-compress-days") || "30", 10) || 30; },
};

export function themeCurrent() {
  return localStorage.getItem(THEME_KEY) || "light";
}