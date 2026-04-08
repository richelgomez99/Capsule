const API_BASE = "http://localhost:8000";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  getHealth: () => fetchAPI<any>("/api/health"),
  getFeed: () => fetchAPI<any[]>("/api/feed"),
  feedAction: (cardId: string, actionId: string, data?: any) =>
    fetchAPI<any>(`/api/feed/${cardId}/action`, {
      method: "POST",
      body: JSON.stringify({ action_id: actionId, data }),
    }),
  getCaptures: () => fetchAPI<any[]>("/api/captures"),
  search: (query: string) =>
    fetchAPI<any>("/api/search", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),
  chat: (message: string) =>
    fetchAPI<any>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  correct: (captureId: string, field: string, oldValue: string, newValue: string) =>
    fetchAPI<any>("/api/correct", {
      method: "POST",
      body: JSON.stringify({ capture_id: captureId, field, old_value: oldValue, new_value: newValue }),
    }),
  feedback: (captureId: string, thumbs: "up" | "down") =>
    fetchAPI<any>("/api/feedback", {
      method: "POST",
      body: JSON.stringify({ capture_id: captureId, thumbs }),
    }),
  getUserModel: () => fetchAPI<any>("/api/user-model"),
  getMetrics: () => fetchAPI<any>("/api/metrics"),
  getJudgePanel: () => fetchAPI<any>("/api/judge-panel"),
  streamEvents: () => new EventSource(`${API_BASE}/api/agent/stream`),

  // ── Capture endpoints (new for web app) ──
  uploadScreenshot: async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/api/captures/screenshot`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    return res.json();
  },
  submitText: (content: string, source: string = "clipboard") =>
    fetchAPI<any>("/api/captures/text", {
      method: "POST",
      body: JSON.stringify({ content, source }),
    }),
  submitUrl: (url: string) =>
    fetchAPI<any>("/api/captures/url", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),
  importHistory: (entries: Array<{ url: string; title?: string; visit_time?: string }>) =>
    fetchAPI<any>("/api/captures/history", {
      method: "POST",
      body: JSON.stringify({ entries }),
    }),
};

// Category config
export const CATEGORIES: Record<string, { emoji: string; colorVar: string }> = {
  code: { emoji: "💻", colorVar: "cat-code" },
  recipe: { emoji: "🍳", colorVar: "cat-recipe" },
  error: { emoji: "🐛", colorVar: "cat-error" },
  documentation: { emoji: "📄", colorVar: "cat-docs" },
  reference: { emoji: "🔖", colorVar: "cat-reference" },
  research: { emoji: "🔬", colorVar: "cat-research" },
  communication: { emoji: "💬", colorVar: "cat-communication" },
  shopping: { emoji: "🛒", colorVar: "cat-shopping" },
  personal: { emoji: "👤", colorVar: "cat-personal" },
};

export const FEED_TYPES: Record<string, { emoji: string; colorVar: string; label: string }> = {
  protection: { emoji: "🛡️", colorVar: "feed-protection", label: "I Protected You" },
  insight: { emoji: "💡", colorVar: "feed-insight", label: "I Noticed" },
  learning: { emoji: "❓", colorVar: "feed-learning", label: "Quick Question" },
  captured: { emoji: "📥", colorVar: "feed-captured", label: "I've Been Busy" },
  forgotten: { emoji: "🕰️", colorVar: "feed-forgotten", label: "Remember This?" },
  synthesis: { emoji: "🔮", colorVar: "feed-synthesis", label: "I Connected Dots" },
};

export const STREAM_TYPES: Record<string, string> = {
  CLASSIFY: "🧠",
  AIRIA: "🧠",
  CAPTURE: "📥",
  DLP: "🛡️",
  SCORING: "📊",
  BRAINTRUST: "📊",
  REFLECTION: "🔄",
  SYNTHESIS: "💡",
  QUESTION: "❓",
  CONNECTED: "🟢",
};
