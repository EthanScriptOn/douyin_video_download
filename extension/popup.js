function short(url, n = 72) {
  if (!url) return "-";
  return url.length > n ? `${url.slice(0, n)}…` : url;
}

function badgeFor(v) {
  if (v.pushStatus === "done") return { cls: "done", text: "已推送" };
  if (v.pushStatus === "pushing") return { cls: "pushing", text: "推送中" };
  if (v.pushStatus === "error") return { cls: "error", text: "推送失败" };
  if (v.complete) return { cls: "ready", text: "可推送" };
  return { cls: "missing", text: "缺轨" };
}

let refreshing = false;
let lastSignature = "";

function signatureOf(state) {
  const stats = state.stats || {};
  const videos = state.videos || [];
  return JSON.stringify({
    stats,
    ids: videos.map((v) => [
      v.videoId,
      v.pushStatus,
      v.tracks?.video,
      v.tracks?.audio,
      v.output || "",
      v.updatedAt || 0,
    ]),
  });
}

async function refresh() {
  if (refreshing) return;
  refreshing = true;
  try {
    const state = await chrome.runtime.sendMessage({ type: "get_state" });
    if (!state) return;
    const sig = signatureOf(state);
    if (sig === lastSignature) return;
    lastSignature = sig;

    const stats = state.stats || {};
    const ready = stats.ready || 0;
    chrome.action.setBadgeText({ text: ready > 0 ? String(ready) : "" });
    chrome.action.setBadgeBackgroundColor({ color: "#16a34a" });
    document.getElementById("meta").textContent =
      `v0.3.2 · 视频 ${stats.total || 0} · 双轨齐全 ${stats.complete || 0} · 可推 ${ready} · 已推 ${stats.done || 0}` +
      (state.helper ? ` · ${state.helper}` : "");

    const list = document.getElementById("list");
    list.innerHTML = "";
    const videos = state.videos || [];
    if (!videos.length) {
      list.innerHTML =
        `<div class="empty">还没有拦截到。先启动本机助手（.exe / .app），再播放带 modal_id 的抖音视频。</div>`;
      return;
    }

    for (const v of videos.slice(0, 20)) {
      const badge = badgeFor(v);
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <div class="card-head">
          <div class="title">${v.title || v.videoId}</div>
          <span class="badge ${badge.cls}">${badge.text}</span>
        </div>
        <div class="tracks">
          <span class="track ${v.tracks?.video ? "ok" : "no"}">视频轨</span>
          <span class="track ${v.tracks?.audio ? "ok" : "no"}">音频轨</span>
        </div>
        <div class="page">${short(v.pageUrl || "", 96)}</div>
        ${v.output ? `<div class="path" title="${v.output}">${v.output}</div>` : ""}
        <div class="actions">
          <button class="primary push-one" data-id="${v.videoId}" ${v.complete && v.pushStatus !== "pushing" ? "" : "disabled"}>
            ${v.pushStatus === "done" ? "重新推送" : "推送到本地"}
          </button>
          <button class="open-one" data-path="${v.output || ""}" ${v.output ? "" : "disabled"}>打开</button>
          <button class="copy-one" data-path="${v.output || ""}" ${v.output ? "" : "disabled"}>复制路径</button>
        </div>
        ${v.pushError ? `<div class="bad" style="margin-top:6px;font-size:11px">${short(v.pushError, 160)}</div>` : ""}
      `;
      list.appendChild(card);
    }

    list.querySelectorAll(".push-one").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-id");
        const status = document.getElementById("status");
        status.textContent = `正在推送 ${id}…`;
        btn.disabled = true;
        lastSignature = "";
        const r = await chrome.runtime.sendMessage({ type: "push_video", videoId: id });
        status.innerHTML = r?.ok
          ? `<span class="ok">已推送</span>`
          : `<span class="bad">${r?.error || "失败"}</span>`;
        refresh();
      });
    });

    list.querySelectorAll(".open-one").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const path = btn.getAttribute("data-path") || "";
        const status = document.getElementById("status");
        status.textContent = "正在打开…";
        const r = await chrome.runtime.sendMessage({ type: "open_output", path });
        status.innerHTML = r?.ok
          ? `<span class="ok">已在 Finder / 播放器打开</span>`
          : `<span class="bad">${r?.error || "打开失败（助手是否在运行？）"}</span>`;
      });
    });

    list.querySelectorAll(".copy-one").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const path = btn.getAttribute("data-path") || "";
        const status = document.getElementById("status");
        try {
          await navigator.clipboard.writeText(path);
          status.innerHTML = `<span class="ok">路径已复制</span>`;
        } catch {
          status.innerHTML = `<span class="bad">复制失败</span>`;
        }
      });
    });
  } catch (err) {
    document.getElementById("status").innerHTML =
      `<span class="bad">刷新失败: ${String(err)}</span>`;
  } finally {
    refreshing = false;
  }
}

document.getElementById("clear").addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ type: "clear" });
  chrome.action.setBadgeText({ text: "" });
  chrome.action.setTitle({ title: "抖音媒体拦截 v0.3.1" });
  document.getElementById("status").textContent = "已清空";
  lastSignature = "";
  refresh();
});

document.getElementById("pushLatest").addEventListener("click", async () => {
  const status = document.getElementById("status");
  status.textContent = "推送中…";
  lastSignature = "";
  const r = await chrome.runtime.sendMessage({ type: "push_latest" });
  status.innerHTML = r?.ok
    ? `<span class="ok">已推送</span>`
    : `<span class="bad">${r?.error || "失败"}</span>`;
  refresh();
});

// Popup used to render once; badge kept rising in background → numbers looked wrong.
chrome.storage.session.onChanged.addListener(() => {
  lastSignature = "";
  refresh();
});
setInterval(refresh, 1000);

refresh();
