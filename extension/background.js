/**
 * @author Codex
 * @date 2026-11-20
 * @comment Group Douyin CDN tracks by real video id; keep badge synced with list.
 */

const LOCAL_BASE = "http://127.0.0.1:18767";
const LOCAL_INGEST = `${LOCAL_BASE}/ingest`;
const LOCAL_OPEN = `${LOCAL_BASE}/open`;
const MAX_VIDEOS = 20;
const AUTO_PUSH = false;

/** @typedef {{
 *  videoId: string,
 *  pageUrl: string,
 *  tabId: number,
 *  videoUrl?: string,
 *  audioUrl?: string,
 *  videoAt?: number,
 *  audioAt?: number,
 *  updatedAt: number,
 *  pushStatus: 'idle'|'pushing'|'done'|'error',
 *  pushError?: string,
 *  output?: string,
 * }} VideoItem */

/** @type {Record<string, VideoItem>} */
let videos = {};
/** @type {Set<string>} */
const pushedIds = new Set();
/** Latest provisional tracks per tab, before modal_id is known. */
/** @type {Record<number, {videoUrl?: string, audioUrl?: string, pageUrl?: string, updatedAt: number}>} */
let tabDrafts = {};

let storageReady = false;
const pendingHits = [];

chrome.storage.session.get(["videos", "pushedIds"]).then((data) => {
  if (data.videos && typeof data.videos === "object") {
    // Only restore real video ids; drop legacy tab:* junk that inflated badge.
    const restored = {};
    for (const [id, item] of Object.entries(data.videos)) {
      if (/^\d+$/.test(id)) restored[id] = item;
    }
    videos = restored;
  }
  if (Array.isArray(data.pushedIds)) {
    data.pushedIds.forEach((id) => {
      if (/^\d+$/.test(String(id))) pushedIds.add(String(id));
    });
  }
  storageReady = true;
  for (const hit of pendingHits.splice(0)) remember(hit);
  refreshBadge();
});

function isRealVideoId(id) {
  return /^\d+$/.test(String(id || ""));
}

function isComplete(v) {
  return Boolean(v?.videoUrl && v?.audioUrl);
}

function computeStats(list) {
  return {
    total: list.length,
    complete: list.filter((v) => v.complete).length,
    ready: list.filter((v) => v.complete && v.pushStatus !== "done").length,
    done: list.filter((v) => v.pushStatus === "done").length,
  };
}

function persist() {
  const ids = Object.keys(videos)
    .filter(isRealVideoId)
    .sort((a, b) => (videos[b].updatedAt || 0) - (videos[a].updatedAt || 0))
    .slice(0, MAX_VIDEOS);
  const next = {};
  for (const id of ids) next[id] = videos[id];
  videos = next;
  chrome.storage.session.set({
    videos,
    pushedIds: [...pushedIds].slice(-50),
  });
  refreshBadge();
}

function refreshBadge() {
  const list = listVideos();
  const stats = computeStats(list);
  // Badge number = popup「可推」count (same listVideos/stats source).
  chrome.action.setBadgeText({ text: stats.ready > 0 ? String(stats.ready) : "" });
  chrome.action.setBadgeBackgroundColor({ color: "#16a34a" });
  chrome.action.setTitle({
    title: `抖音媒体拦截 v0.3.1 · 可推 ${stats.ready} / 共 ${stats.total}`,
  });
  return stats;
}

function kindOf(url) {
  const u = url.toLowerCase();
  if (u.includes("media-video")) return "video";
  if (u.includes("media-audio")) return "audio";
  return null;
}

function videoIdFromPage(pageUrl) {
  if (!pageUrl) return null;
  try {
    const u = new URL(pageUrl);
    const modal = u.searchParams.get("modal_id");
    if (modal && /^\d+$/.test(modal)) return modal;
    const m = u.pathname.match(/\/video\/(\d+)/);
    if (m) return m[1];
  } catch {
    /* ignore */
  }
  return null;
}

function displayTitle(videoId) {
  return `视频 ${videoId}`;
}

function remember(hit) {
  if (!storageReady) {
    pendingHits.push(hit);
    return;
  }

  const realId = videoIdFromPage(hit.pageUrl);

  // No modal_id yet: keep draft on the tab, do not create list/badge entries.
  if (!realId) {
    if (hit.tabId < 0) return;
    const draft = tabDrafts[hit.tabId] || { updatedAt: 0 };
    if (hit.kind === "video") draft.videoUrl = hit.url;
    if (hit.kind === "audio") draft.audioUrl = hit.url;
    if (hit.pageUrl) draft.pageUrl = hit.pageUrl;
    draft.updatedAt = hit.ts;
    tabDrafts[hit.tabId] = draft;
    return;
  }

  const videoId = realId;
  const cur = videos[videoId] || {
    videoId,
    pageUrl: hit.pageUrl || "",
    tabId: hit.tabId,
    updatedAt: 0,
    pushStatus: "idle",
  };

  // Absorb provisional tab drafts once modal_id appears.
  const draft = tabDrafts[hit.tabId];
  if (draft) {
    if (!cur.videoUrl && draft.videoUrl) {
      cur.videoUrl = draft.videoUrl;
      cur.videoAt = draft.updatedAt;
    }
    if (!cur.audioUrl && draft.audioUrl) {
      cur.audioUrl = draft.audioUrl;
      cur.audioAt = draft.updatedAt;
    }
    delete tabDrafts[hit.tabId];
  }

  const prevVideo = cur.videoUrl;
  const prevAudio = cur.audioUrl;
  if (hit.kind === "video") {
    cur.videoUrl = hit.url;
    cur.videoAt = hit.ts;
  }
  if (hit.kind === "audio") {
    cur.audioUrl = hit.url;
    cur.audioAt = hit.ts;
  }
  if (hit.pageUrl) cur.pageUrl = hit.pageUrl;
  cur.tabId = hit.tabId;
  cur.updatedAt = hit.ts;

  const mediaChanged =
    (hit.kind === "video" && hit.url !== prevVideo) ||
    (hit.kind === "audio" && hit.url !== prevAudio);
  if (cur.pushStatus === "done" && mediaChanged) {
    cur.pushStatus = "idle";
    cur.pushError = undefined;
    cur.output = undefined;
    pushedIds.delete(videoId);
  } else if (cur.pushStatus === "error") {
    cur.pushStatus = "idle";
    cur.pushError = undefined;
  }

  videos[videoId] = cur;
  persist();

  if (AUTO_PUSH && isComplete(cur) && cur.pushStatus !== "done") {
    pushVideo(videoId).catch((err) => console.warn("auto push failed", err));
  }
}

async function pushVideo(videoId, { force = false } = {}) {
  const item = videos[videoId];
  if (!item) return { ok: false, error: "视频不存在" };
  if (!isComplete(item)) {
    return {
      ok: false,
      error: `双轨不齐：视频${item.videoUrl ? "✓" : "✗"} 音频${item.audioUrl ? "✓" : "✗"}`,
    };
  }
  if (!force && item.pushStatus === "done") {
    return { ok: true, skipped: true, output: item.output, status: 200 };
  }

  item.pushStatus = "pushing";
  item.pushError = undefined;
  persist();

  try {
    const resp = await fetch(LOCAL_INGEST, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        key: videoId,
        video_url: item.videoUrl,
        audio_url: item.audioUrl,
        page_url: item.pageUrl || "",
        source: "chrome_extension",
        ts: Date.now(),
      }),
    });
    const text = await resp.text();
    let parsed = null;
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = null;
    }
    const ok = Boolean(resp.ok && parsed?.ok !== false);
    if (ok) {
      item.pushStatus = "done";
      item.output = parsed?.output || "";
      item.pushError = undefined;
      pushedIds.add(videoId);
      persist();
      return { ok: true, status: resp.status, output: item.output, videoId };
    }
    item.pushStatus = "error";
    item.pushError = parsed?.error || text.slice(0, 300) || `HTTP ${resp.status}`;
    persist();
    return { ok: false, status: resp.status, error: item.pushError, videoId };
  } catch (err) {
    item.pushStatus = "error";
    item.pushError = String(err);
    persist();
    return { ok: false, error: item.pushError, videoId };
  }
}

async function openOutput(path) {
  const resp = await fetch(LOCAL_OPEN, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
  const text = await resp.text();
  let parsed = null;
  try {
    parsed = JSON.parse(text);
  } catch {
    parsed = null;
  }
  return {
    ok: Boolean(resp.ok && parsed?.ok !== false),
    error: parsed?.error || (!resp.ok ? text.slice(0, 200) : ""),
    path: parsed?.path || path,
  };
}

function listVideos() {
  return Object.values(videos)
    .filter((v) => isRealVideoId(v.videoId))
    .sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0))
    .map((v) => ({
      ...v,
      title: displayTitle(v.videoId),
      complete: isComplete(v),
      canPush: isComplete(v) && v.pushStatus !== "pushing",
      tracks: {
        video: Boolean(v.videoUrl),
        audio: Boolean(v.audioUrl),
      },
    }));
}

chrome.webRequest.onCompleted.addListener(
  (details) => {
    if (details.statusCode >= 400) return;
    if (details.tabId < 0) return;
    const kind = kindOf(details.url);
    if (!kind) return;
    if (!/douyinvod\.com|bytevod\.com/i.test(details.url)) return;

    chrome.tabs
      .get(details.tabId)
      .then((tab) => {
        remember({
          ts: Date.now(),
          kind,
          url: details.url,
          tabId: details.tabId,
          pageUrl: tab?.url || "",
        });
      })
      .catch(() => {
        remember({
          ts: Date.now(),
          kind,
          url: details.url,
          tabId: details.tabId,
          pageUrl: "",
        });
      });
  },
  { urls: ["*://*.douyinvod.com/*", "*://*.bytevod.com/*"] }
);

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type === "get_state") {
    const list = listVideos();
    const stats = refreshBadge(); // force badge == current list stats
    sendResponse({ videos: list, stats, helper: LOCAL_BASE });
    return true;
  }
  if (msg?.type === "clear") {
    videos = {};
    tabDrafts = {};
    pushedIds.clear();
    pendingHits.length = 0;
    persist();
    chrome.action.setBadgeText({ text: "" });
    sendResponse({ ok: true });
    return true;
  }
  if (msg?.type === "push_video") {
    pushVideo(String(msg.videoId || ""), { force: true })
      .then((r) => sendResponse(r))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true;
  }
  if (msg?.type === "push_latest") {
    const ready = listVideos().filter((v) => v.complete && v.pushStatus !== "done");
    const target = ready[0] || listVideos().find((v) => v.complete);
    if (!target) {
      sendResponse({ ok: false, error: "没有双轨齐全的视频可推送" });
      return true;
    }
    pushVideo(target.videoId, { force: true })
      .then((r) => sendResponse(r))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true;
  }
  if (msg?.type === "open_output") {
    openOutput(String(msg.path || ""))
      .then((r) => sendResponse(r))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true;
  }
  if (msg?.type === "sync_badge") {
    sendResponse({ ok: true, stats: refreshBadge() });
    return true;
  }
  return false;
});
