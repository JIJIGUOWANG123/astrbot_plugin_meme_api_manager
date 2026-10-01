// ============================================================
// 鸡鸡娱乐系统 · 配置页面前端 (v1.7.1 · 方案三 + 超时保护)
// 读取：桥接 apiGet 优先，超时/失败自动降级 fetch
// 保存：桥接 apiPost 优先，超时/失败自动降级 fetch
// ============================================================

const bridge = window.AstrBotPluginPage;

// ── 全局状态 ──
let SCHEMA = {};
let CONFIG = {};
let currentView = "menu";
let bridgeReady = false;

const PLUGIN_ID = "astrbot_plugin_meme_api_manager";

// ── 工具 ──
const $ = (id) => document.getElementById(id);
function esc(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}

const toastEl = $("toast");
function toast(msg, type = "success") {
  if (!toastEl) return;
  toastEl.textContent = msg;
  toastEl.className = `toast toast-${type} show`;
  setTimeout(() => { toastEl.className = `toast toast-${type}`; }, 2200);
}

// ============================================================
// 桥接初始化（带超时保护，防止 bridge.ready() 永远挂住）
// ============================================================
async function initBridge(retries = 2, timeoutMs = 2000) {
  for (let i = 0; i < retries; i++) {
    try {
      if (!bridge || typeof bridge.ready !== "function") {
        throw new Error("AstrBotPluginPage 不存在或缺少 ready()");
      }
      console.log(`[bridge] ready 第 ${i + 1}/${retries} 次尝试`);
      await Promise.race([
        bridge.ready(),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error(`bridge.ready() 超时（${timeoutMs}ms）`)), timeoutMs)
        ),
      ]);
      bridgeReady = true;
      const el = $("bridgeStatus");
      if (el) {
        el.textContent = "桥接已就绪";
        el.className = "bridge-status ok";
      }
      console.log("[bridge] ready 成功");
      return true;
    } catch (e) {
      console.warn(`[bridge] ready 失败 (${i + 1}/${retries}):`, e);
      await new Promise(r => setTimeout(r, 300));
    }
  }
  bridgeReady = false;
  const el = $("bridgeStatus");
  if (el) {
    el.textContent = "桥接不可用（降级 fetch）";
    el.className = "bridge-status fail";
  }
  console.warn("[bridge] 已放弃，使用 fetch 降级");
  return false;
}

// ============================================================
// 通用请求工具
// ============================================================
async function tryFetchJSON(url, options = {}) {
  const r = await fetch(url, {
    credentials: "same-origin",
    ...options,
  });
  if (!r.ok) {
    throw new Error(`HTTP ${r.status} ${url}`);
  }
  return await r.json();
}

// 配置接口候选 URL（GET / POST 共用）
// 后端通过 context.register_web_api 注册的路由是 /<PLUGIN_ID>/<action>，
// 在 AstrBot 面板中经 /api/plug/ 分发命中；因此兜底只能用这一种形态。
function buildRouteUrls(action) {
  return [
    `/${PLUGIN_ID}/${action}`,                     // 直接命中注册路由
    `/api/plug/${PLUGIN_ID}/${action}`,            // 经面板插件扩展入口分发
  ];
}

function buildConfigUrls() {
  return buildRouteUrls("config");
}

// ============================================================
// 配置加载（桥接优先 + 超时 + fetch 兜底）
// ============================================================
async function loadAllConfig() {
  const errors = [];

  // ---------- 优先 bridge.apiGet（带超时）----------
  if (bridgeReady && bridge && typeof bridge.apiGet === "function") {
    try {
      console.log(`[config] bridge.apiGet("config")`);
      const res = await Promise.race([
        bridge.apiGet("config"),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error("bridge.apiGet 超时（2000ms）")), 2000)
        ),
      ]);
      console.log(`[config] bridge.apiGet("config") 返回:`, res);
      if (res && (res.schema || res.config)) {
        SCHEMA = res.schema || {};
        CONFIG = res.config || {};
        console.log(`[config] 桥接成功: schema=${Object.keys(SCHEMA).length}, config=${Object.keys(CONFIG).length}`);
        return true;
      }
      errors.push(`bridge.apiGet("config") 返回空`);
    } catch (e) {
      console.warn(`[config] bridge.apiGet("config") 失败:`, e);
      errors.push(`bridge.apiGet("config"): ${e.message || e}`);
    }
  } else {
    errors.push("桥接不可用");
  }

  // ---------- 兜底：同源 fetch ----------
  for (const url of buildConfigUrls()) {
    try {
      console.log(`[config] fetch GET ${url}`);
      const j = await tryFetchJSON(url);
      if (j && (j.schema || j.config)) {
        SCHEMA = j.schema || {};
        CONFIG = j.config || {};
        console.log(`[config] fetch GET 成功: schema=${Object.keys(SCHEMA).length}, config=${Object.keys(CONFIG).length}`);
        return true;
      }
    } catch (e) {
      console.warn(`[config] fetch GET ${url} 失败:`, e);
      errors.push(`${url}: ${e.message || e}`);
    }
  }

  console.error("[config] 全部失败:", errors);
  const errEl = $("errorMsg");
  if (errEl) errEl.innerHTML = errors.map(e => `· ${esc(e)}`).join("<br>");
  return false;
}

// ============================================================
// 保存结果判定
// 后端统一返回 {ok: bool, msg: string, config?: {...}}
//   返回 true  -> 已确定结果（成功）
//   返回 false -> 已确定结果（失败，并已提示）
//   返回 null  -> 本次尝试没有明确结论，可换 URL / 传参形态重试
// ============================================================
function applySaveResult(res, tag) {
  if (!res || typeof res !== "object") return null;
  if (res.ok === true) {
    console.log(`[config] ✅ 保存成功（${tag}）`);
    return true;
  }
  if (res.ok === false) {
    const msg = res.msg || "未知错误";
    console.warn(`[config] ⚠️ 后端拒绝（${tag}）：${msg}`);
    // "数据为空" 说明本次传参形态没被识别，交给下一种形态重试
    if (msg === "数据为空") return null;
    toast(`保存失败：${msg}`, "error");
    return false;
  }
  console.warn(`[config] 响应缺少 ok 字段（${tag}），视为未确认`);
  return null;
}

// ============================================================
// 配置保存（桥接优先 + 超时 + fetch 兜底）
// ============================================================
async function saveConfig(partial) {
  CONFIG = Object.assign({}, CONFIG, partial);

  // ---------- ① 优先桥接：直接传配置体 ----------
  if (bridgeReady && bridge && typeof bridge.apiPost === "function") {
    const attempts = [
      { desc: 'apiPost("config", payload)',           fn: () => bridge.apiPost("config", partial) },
      { desc: 'apiPost("config", {data: payload})',   fn: () => bridge.apiPost("config", { data: partial }) },
      { desc: 'apiPost("saveConfig", payload)',       fn: () => bridge.apiPost("saveConfig", partial) },
    ];

    for (const at of attempts) {
      try {
        console.log(`[config] bridge.${at.desc}`);
        const res = await Promise.race([
          at.fn(),
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error(`bridge.${at.desc} 超时`)), 2000)
          ),
        ]);
        console.log(`[config] bridge.${at.desc} 返回:`, res);

        const settled = applySaveResult(res, `bridge.${at.desc}`);
        if (settled !== null) return settled;
      } catch (e) {
        console.warn(`[config] bridge.${at.desc} 异常:`, e);
      }
    }
  } else {
    console.warn("[config] 桥接不可用，跳过 bridge.apiPost");
  }

  // ---------- ② 兜底：同源 fetch ----------
  for (const url of buildConfigUrls()) {
    try {
      console.log(`[config] fetch POST ${url}`, partial);
      const r = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(partial),
      });
      if (!r.ok) {
        console.warn(`[config] fetch POST ${url} HTTP ${r.status}`);
        continue;
      }
      const j = await r.json();
      console.log(`[config] fetch POST ${url} 返回:`, j);
      const settled = applySaveResult(j, `fetch ${url}`);
      if (settled !== null) return settled;
    } catch (e) {
      console.warn(`[config] fetch POST ${url} 失败:`, e);
    }
  }

  toast("保存失败，请查看控制台日志", "error");
  return false;
}

// ============================================================
// Schema 取值辅助
// ============================================================
function cfgVal(key) {
  if (key in CONFIG) return CONFIG[key];
  const s = SCHEMA[key];
  return s && "default" in s ? s.default : "";
}
function cfgDesc(key) { return (SCHEMA[key] && SCHEMA[key].description) || key; }
function cfgHint(key) { return (SCHEMA[key] && SCHEMA[key].hint) || ""; }

// ============================================================
// 通用控件渲染
// ============================================================
function renderBool(key) {
  const on = !!cfgVal(key);
  return `<div class="switch-row">
    <div>
      <div class="switch-label">${esc(cfgDesc(key))}</div>
      ${cfgHint(key) ? `<div class="switch-desc">${esc(cfgHint(key))}</div>` : ""}
    </div>
    <label class="switch">
      <input type="checkbox" data-cfg="${key}" data-type="bool" ${on ? "checked" : ""} />
      <span class="slider"></span>
    </label>
  </div>`;
}

function renderString(key, opts = {}) {
  const v = cfgVal(key);
  const common = `data-cfg="${key}" data-type="string"`;
  const input = opts.textarea
    ? `<textarea ${common} rows="3">${esc(v)}</textarea>`
    : `<input type="text" ${common} value="${esc(v)}" />`;
  return `<div class="form-group">
    <label>${esc(cfgDesc(key))}</label>
    ${input}
    ${cfgHint(key) ? `<span class="hint">${esc(cfgHint(key))}</span>` : ""}
  </div>`;
}

function renderInt(key) {
  const v = cfgVal(key);
  return `<div class="form-group">
    <label>${esc(cfgDesc(key))}</label>
    <input type="number" data-cfg="${key}" data-type="int" value="${esc(v)}" />
    ${cfgHint(key) ? `<span class="hint">${esc(cfgHint(key))}</span>` : ""}
  </div>`;
}

function renderTemplateList(key) {
  const items = Array.isArray(cfgVal(key)) ? cfgVal(key) : [];
  const schema = SCHEMA[key] || {};
  const templates = schema.templates || {};
  const tplKey = Object.keys(templates)[0] || "";
  const tpl = templates[tplKey] || { items: {} };
  const fields = Object.entries(tpl.items || {});

  let html = `<div class="template-list" data-tplkey="${key}">`;
  items.forEach((item, idx) => {
    html += `<div class="template-item" data-idx="${idx}">`;
    html += `<div class="template-item-header">
      <div class="template-item-title">${esc(tpl.name || tplKey)} #${idx + 1}</div>
      <button class="btn btn-sm btn-danger" data-action="del-tpl" data-key="${key}" data-idx="${idx}">删除</button>
    </div>`;
    html += `<div class="template-item-body">`;
    fields.forEach(([fk, fs]) => {
      const label = fs.description || fk;
      const ftype = fs.type || "string";
      const fval = item[fk] != null ? item[fk] : (fs.default || "");
      const dataAttr = `data-tplkey="${key}" data-idx="${idx}" data-field="${fk}" data-ftype="${ftype}"`;
      if (ftype === "text") {
        html += `<div class="form-row"><div class="form-group">
          <label>${esc(label)}</label>
          <textarea ${dataAttr} rows="2">${esc(fval)}</textarea>
        </div></div>`;
      } else {
        html += `<div class="form-row"><div class="form-group">
          <label>${esc(label)}</label>
          <input type="text" ${dataAttr} value="${esc(fval)}" />
        </div></div>`;
      }
    });
    html += `</div></div>`;
  });
  html += `</div>`;
  html += `<button class="btn btn-primary btn-sm" data-action="add-tpl" data-key="${key}" style="margin-top:10px;">+ 添加条目</button>`;
  return html;
}

// ============================================================
// 视图定义
// ============================================================
const VIEWS = {
  menu: {
    title: "菜单指令",
    groups: [
      { title: "主菜单与子菜单入口", keys: ["cmd_main", "cmd_meme_menu", "cmd_mc_menu", "cmd_greeting_menu", "cmd_checkin_menu", "cmd_daily_menu", "cmd_admin"] },
      { title: "菜单效果预览", type: "menu-preview" },
    ],
  },
  meme: {
    title: "接口系统",
    groups: [
      { title: "指令配置", keys: ["cmd_meme_image", "cmd_meme_video"] },
      { title: "基础配置", keys: ["cmd_list", "cmd_add", "cmd_del", "cmd_save", "default_key"] },
      { title: "自定义接口列表", keys: ["api_list"] },
      { title: "每群屏蔽关键词", keys: ["group_block_keywords"] },
    ],
  },
  mc: {
    title: "MC 系统",
    groups: [
      { title: "指令配置", keys: ["cmd_minecraft", "cmd_mc_auto", "cmd_mc_test"] },
      { title: "功能开关", keys: ["minecraft_enable"] },
      { title: "检测参数", keys: ["minecraft_check_interval", "minecraft_auto_groups"] },
      { title: "测试推送", keys: ["minecraft_test_groups"] },
    ],
  },
  greeting: {
    title: "打卡系统",
    groups: [
      { title: "指令配置", keys: ["cmd_greeting_morning", "cmd_greeting_night", "cmd_greeting_rank", "cmd_greeting_stats"] },
      { title: "功能开关", keys: ["greeting_enable"] },
      { title: "时间与规则", keys: ["greeting_time_format", "greeting_day_start_hour", "greeting_morning_cutoff_hour", "greeting_night_cutoff_hour", "greeting_night_cutoff_minute", "greeting_min_awake_seconds", "greeting_max_repeat_remind"] },
      { title: "起床提示语", keys: ["greeting_morning_messages"] },
      { title: "睡觉提示语", keys: ["greeting_night_messages"] },
    ],
  },
  checkin: {
    title: "签到系统",
    groups: [
      { title: "功能开关", keys: ["checkin_enable"] },
      { title: "指令配置", keys: ["checkin_trigger_names", "checkin_rank_trigger_names", "checkin_info_trigger_names"] },
      { title: "群黑白名单", keys: ["checkin_group_mode", "checkin_group_whitelist", "checkin_group_blacklist"] },
    ],
  },
  steal: {
    title: "偷积分",
    groups: [
      { title: "功能开关", keys: ["steal_enable"] },
      { title: "指令与范围", keys: ["steal_trigger_names", "steal_min", "steal_max"] },
      { title: "概率与惩罚", keys: ["steal_success_rate", "steal_fail_punish_rate", "steal_punish_min", "steal_punish_max"] },
    ],
  },
  bank: {
    title: "银行",
    groups: [
      { title: "功能开关", keys: ["bank_enable"] },
      { title: "指令配置", keys: ["bank_trigger_names", "bank_deposit_names", "bank_withdraw_names"] },
      { title: "利率与结算", keys: ["bank_interest_rate", "bank_interest_hour"] },
    ],
  },
  mount: {
    title: "坐骑系统",
    groups: [
      { title: "功能开关", keys: ["mount_enable"] },
      { title: "指令配置", keys: ["mount_trigger_names", "mount_list_trigger_names", "mount_buy_trigger_names", "cmd_mount_add_names", "cmd_mount_del_names"] },
      { title: "坐骑列表", keys: ["mount_list"] },
    ],
  },
  job: {
    title: "打工系统",
    groups: [
      { title: "功能开关", keys: ["job_enable"] },
      { title: "指令配置", keys: ["job_trigger_names", "job_info_trigger_names", "cmd_job_add_names", "cmd_job_del_names"] },
      { title: "工种列表", keys: ["job_list"] },
    ],
  },
  fortune: {
    title: "今日运势",
    groups: [
      { title: "功能开关", keys: ["fortune_enable"] },
      { title: "指令配置", keys: ["fortune_trigger_names"] },
      { title: "群黑白名单", keys: ["fortune_group_mode", "fortune_group_whitelist", "fortune_group_blacklist"] },
      { title: "运势内容列表", keys: ["fortune_list"] },
    ],
  },
  husband: {
    title: "今日老公",
    groups: [
      { title: "功能开关", keys: ["husband_enable"] },
      { title: "指令配置", keys: ["husband_trigger_names"] },
      { title: "群黑白名单", keys: ["husband_group_mode", "husband_group_whitelist", "husband_group_blacklist"] },
    ],
  },
  luck: {
    title: "今日人品",
    groups: [
      { title: "功能开关", keys: ["luck_enable"] },
      { title: "指令配置", keys: ["luck_trigger_names"] },
      { title: "群黑白名单", keys: ["luck_group_mode", "luck_group_whitelist", "luck_group_blacklist"] },
    ],
  },
  news: {
    title: "每日读报",
    groups: [
      { title: "功能开关", keys: ["daily_news_enable"] },
      { title: "定时推送", keys: ["daily_news_time", "daily_news_interval"] },
      { title: "指令配置", keys: ["cmd_daily_news", "cmd_daily_news_on", "cmd_daily_news_off", "cmd_daily_news_time", "cmd_daily_news_list"] },
    ],
  },
  chime: {
    title: "整点报时",
    groups: [
      { title: "功能开关", keys: ["hourly_chime_enable"] },
      { title: "参数配置", keys: ["hourly_chime_interval", "hourly_chime_template"] },
      { title: "指令配置", keys: ["cmd_chime_on", "cmd_chime_off", "cmd_chime_status", "cmd_chime_hours", "cmd_chime_text", "cmd_chime_list", "cmd_chime_test"] },
    ],
  },
  word: {
    title: "词库系统",
    groups: [
      { title: "功能开关", keys: ["word_reply_enable"] },
      { title: "指令配置", keys: ["cmd_word_add", "cmd_word_del", "cmd_word_list"] },
      { title: "词库列表", keys: ["word_reply_list"] },
      { title: "群黑白名单", keys: ["word_reply_group_mode", "word_reply_group_whitelist", "word_reply_group_blacklist"] },
    ],
  },
  admin: {
    title: "管理系统",
    groups: [
      { title: "指令配置", keys: ["cmd_enable", "cmd_disable", "cmd_enable_feature", "cmd_disable_feature", "cmd_feature_status"] },
      { title: "必须艾特机器人", keys: ["must_at_bot", "cmd_must_at_bot_on", "cmd_must_at_bot_off", "cmd_must_at_bot_status"] },
      { title: "管理员设置", keys: ["cmd_view_admin", "cmd_refresh_admin", "cmd_add_admin", "cmd_del_admin", "cmd_admin_list", "plugin_admins", "group_admin_cache_ttl"] },
      { title: "群黑白名单", keys: ["group_mode", "group_whitelist", "group_blacklist", "disabled_groups"] },
      { title: "群员管理（踢出 / 禁言 / 拉黑）", keys: ["moderation_enable", "mute_duration", "blacklist_default_action", "member_blacklist"] },
      { title: "群员管理指令", keys: ["cmd_kick", "cmd_mute", "cmd_unmute", "cmd_blacklist", "cmd_unblacklist", "cmd_blacklist_list"] },
      { title: "电脑状态 · 输出预览与测试", type: "status-panel" },
      { title: "电脑状态", keys: ["cmd_status", "cmd_status_title", "cmd_status_tail", "cmd_status_show_basic", "cmd_status_show_uptime", "cmd_status_show_cpu", "cmd_status_show_mem", "cmd_status_show_disk"] },
      { title: "每日定时状态推送", keys: ["daily_status_push_enable", "daily_status_push_time", "daily_status_push_interval", "cmd_daily_push_on", "cmd_daily_push_off", "cmd_daily_push_time", "cmd_daily_push_list"] },
    ],
  },
};

// ============================================================
// 电脑状态：预览 + 测试推送
// ============================================================
function buildStatusPanelHtml() {
  return `<div class="status-panel">
    <div class="status-panel-head">
      <span class="status-panel-title">当前状态输出预览</span>
      <span class="status-panel-actions">
        <button class="btn btn-info btn-sm" id="refreshStatusBtn">🔄 刷新预览</button>
        <button class="btn btn-primary btn-sm" id="testPushBtn">🚀 测试推送</button>
      </span>
    </div>
    <pre class="status-preview" id="statusPreview">点击「刷新预览」查看当前配置下的实际输出</pre>
    <div class="status-panel-hint" id="statusPushResult"></div>
    <div class="status-panel-hint">
      预览与测试推送都会<strong>叠加当前表单里未保存的修改</strong>，方便先看效果再保存。
      测试推送需要目标群已记录过 UMO（该群发过任意一条消息）。
    </div>
  </div>`;
}

async function fetchStatusPreview() {
  const box = $("statusPreview");
  if (!box) return;
  box.textContent = "加载中...";
  const hint = $("statusPushResult");
  if (hint) hint.textContent = "";

  const applyResult = (res) => {
    if (res && res.ok && res.text) {
      box.textContent = res.text;
      if (hint) hint.textContent = `📄 预览来源：${res.group_id ? `群 ${res.group_id}` : "无群上下文"}`;
      return true;
    }
    return false;
  };

  // ① 桥接优先
  if (bridgeReady && bridge && typeof bridge.apiGet === "function") {
    try {
      const res = await Promise.race([
        bridge.apiGet("previewStatus"),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error("bridge.apiGet 超时")), 3000)
        ),
      ]);
      if (applyResult(res)) return;
    } catch (e) {
      console.warn("[status] 桥接预览失败，降级 fetch:", e);
    }
  }

  // ② fetch 兜底
  for (const url of buildRouteUrls("previewStatus")) {
    try {
      const r = await fetch(url, { credentials: "same-origin" });
      if (!r.ok) continue;
      if (applyResult(await r.json())) return;
    } catch (e) {
      console.warn(`[status] fetch ${url} 失败:`, e);
    }
  }

  box.textContent = "获取失败，请检查桥接是否可用或后端状态模块是否加载";
}

async function onTestPush() {
  const btn = $("testPushBtn");
  const out = $("statusPushResult");
  if (btn) { btn.disabled = true; btn.textContent = "推送中..."; }
  if (out) out.textContent = "";

  // 带上当前表单值，让测试推送反映未保存的修改
  const payload = { data: collectFormData() };

  const finish = (res, err) => {
    if (err) {
      const msg = (err && err.message) || String(err);
      if (out) out.textContent = `❌ 推送失败：${msg}`;
      toast("推送失败，请查看控制台", "error");
      return;
    }
    if (res && res.ok) {
      if (out) out.textContent = `✅ 已推送到群 ${res.group_id || "?"}`;
      toast("✅ 测试推送成功");
    } else {
      const msg = (res && res.msg) || "未知错误";
      if (out) out.textContent = `❌ 推送失败：${msg}`;
      toast(`推送失败：${msg}`, "error");
    }
  };

  try {
    // ① 桥接优先
    let handled = false;
    if (bridgeReady && bridge && typeof bridge.apiPost === "function") {
      try {
        const res = await Promise.race([
          bridge.apiPost("testStatusPush", payload),
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error("bridge.apiPost 超时")), 15000)
          ),
        ]);
        console.log("[status] testStatusPush 返回:", res);
        finish(res, null);
        handled = true;
      } catch (e) {
        console.warn("[status] 桥接测试推送失败，降级 fetch:", e);
      }
    }

    // ② fetch 兜底
    if (!handled) {
      let done = false;
      let lastErr = null;
      for (const url of buildRouteUrls("testStatusPush")) {
        try {
          const r = await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          if (!r.ok) { lastErr = new Error(`HTTP ${r.status}`); continue; }
          const j = await r.json();
          console.log(`[status] fetch ${url} 返回:`, j);
          finish(j, null);
          done = true;
          break;
        } catch (e) {
          lastErr = e;
          console.warn(`[status] fetch ${url} 失败:`, e);
        }
      }
      if (!done) finish(null, lastErr || new Error("全部通道失败"));
    }
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "🚀 测试推送"; }
  }
}

// ============================================================
// 数据备份 / 导出
// ============================================================
function bytesText(n) {
  const v = Number(n) || 0;
  if (v < 1024) return `${v} B`;
  if (v < 1024 * 1024) return `${(v / 1024).toFixed(1)} KB`;
  return `${(v / 1024 / 1024).toFixed(2)} MB`;
}

function setBackupResult(msg, type) {
  const el = $("backupResult");
  if (!el) return;
  el.textContent = msg || "";
  el.className = `backup-result${type ? ` ${type}` : ""}`;
}

// 统一的「桥接优先 + fetch 兜底」请求
async function backupRequest(action, { method = "GET", body = null } = {}) {
  // ① 桥接
  if (bridgeReady && bridge) {
    try {
      if (method === "GET" && typeof bridge.apiGet === "function") {
        return await Promise.race([
          bridge.apiGet(action),
          new Promise((_, rj) => setTimeout(() => rj(new Error("bridge 超时")), 8000)),
        ]);
      }
      if (method === "POST" && typeof bridge.apiPost === "function") {
        return await Promise.race([
          bridge.apiPost(action, body || {}),
          new Promise((_, rj) => setTimeout(() => rj(new Error("bridge 超时")), 30000)),
        ]);
      }
    } catch (e) {
      console.warn(`[backup] 桥接 ${action} 失败，降级 fetch:`, e);
    }
  }
  // ② fetch 兜底
  let lastErr = null;
  for (const url of buildRouteUrls(action)) {
    try {
      const opt = { method, credentials: "same-origin" };
      if (method === "POST") {
        opt.headers = { "Content-Type": "application/json" };
        opt.body = JSON.stringify(body || {});
      }
      const r = await fetch(url, opt);
      if (!r.ok) { lastErr = new Error(`HTTP ${r.status}`); continue; }
      return await r.json();
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error("请求失败");
}

async function openBackupModal() {
  const modal = $("backupModal");
  if (!modal) return;
  modal.classList.add("open");
  setBackupResult("");
  const filesEl = $("backupFiles");
  if (filesEl) filesEl.textContent = "读取中...";
  try {
    const res = await backupRequest("backupInfo");
    if (res && res.ok) {
      const dirEl = $("backupDefaultDir");
      if (dirEl) dirEl.textContent = res.default_dir || "（未知）";
      const input = $("backupDirInput");
      if (input && !input.value) input.placeholder = `留空使用：${res.default_dir || "默认目录"}`;
      if (filesEl) {
        const files = res.files || [];
        filesEl.innerHTML = files.map(f => {
          const tag = f.exists
            ? `<span class="ok">✔</span> ${esc(f.file)} <span class="miss">(${bytesText(f.size)})</span>`
            : `<span class="miss">✘ ${esc(f.file)}（暂无数据）</span>`;
          return `${tag}　${esc(f.label)}`;
        }).join("<br>");
      }
    } else {
      if (filesEl) filesEl.textContent = `读取失败：${(res && res.msg) || "未知错误"}`;
    }
  } catch (e) {
    console.warn("[backup] 读取备份信息失败:", e);
    if (filesEl) filesEl.textContent = "读取失败，请检查桥接或后端路由";
  }
}

function closeBackupModal() {
  const modal = $("backupModal");
  if (modal) modal.classList.remove("open");
}

async function onDoBackup() {
  const btn = $("doBackupBtn");
  const input = $("backupDirInput");
  const target = (input && input.value.trim()) || "";
  if (btn) { btn.disabled = true; btn.textContent = "备份中..."; }
  setBackupResult("正在备份，请稍候...");
  try {
    const res = await backupRequest("backup", { method: "POST", body: { target_dir: target } });
    if (res && res.ok) {
      const n = (res.files || []).length;
      setBackupResult(`✅ ${res.msg}\n备份目录：${res.path}`, "ok");
      toast(`✅ 已备份 ${n} 个文件`);
    } else {
      setBackupResult(`❌ ${(res && res.msg) || "备份失败"}`, "err");
      toast("备份失败", "error");
    }
  } catch (e) {
    console.warn("[backup] 备份失败:", e);
    setBackupResult(`❌ 备份失败：${(e && e.message) || e}`, "err");
    toast("备份失败", "error");
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "备份到该目录"; }
  }
}

async function onDownloadBackup() {
  const btn = $("doDownloadBtn");
  if (btn) { btn.disabled = true; btn.textContent = "打包中..."; }
  setBackupResult("正在打包全部数据...");
  try {
    const res = await backupRequest("backupDownload");
    if (!res || !res.ok || !res.bundle) {
      setBackupResult(`❌ ${(res && res.msg) || "打包失败"}`, "err");
      return;
    }
    const text = JSON.stringify(res.bundle, null, 2);
    const blob = new Blob([text], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const stamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${PLUGIN_ID}_backup_${stamp}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    setBackupResult(`✅ 已导出 ${res.bundle.file_count} 个文件，请查看浏览器的下载目录`, "ok");
    toast("✅ 已开始下载备份");
  } catch (e) {
    console.warn("[backup] 下载失败:", e);
    setBackupResult(`❌ 下载失败：${(e && e.message) || e}`, "err");
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "下载 JSON 备份"; }
  }
}

// ============================================================
// 数据导入 / 还原
// ============================================================
function importCheckboxMergeSkip() {
  const cb = $("importMergeSkip");
  return !!(cb && cb.checked);
}

function setImportPreview(msg, type) {
  const el = $("importPreview");
  if (!el) return;
  el.textContent = msg || "";
  el.style.color = type === "err" ? "var(--danger)" : "var(--text-secondary)";
}

function renderImportPreview(res) {
  const el = $("importPreview");
  if (!el || !res) return;
  const files = res.files || [];
  const head = `${res.msg || ""}<br>来源：${esc(res.source || "")}<br><br>`;
  const body = files.map(f => {
    if (f.valid) {
      return `<span class="ok">✔</span> ${esc(f.file)} <span class="miss">(${bytesText(f.size)})</span>　${esc(f.label || "")}`;
    }
    return `<span class="miss">✘ ${esc(f.file)}　${esc(f.reason || "不可用")}</span>`;
  }).join("<br>");
  el.innerHTML = head + body;
}

async function onImportPreview() {
  const input = $("importSourceInput");
  const source = (input && input.value.trim()) || "";
  if (!source) {
    setImportPreview("请先填写备份目录或备份包路径", "err");
    return;
  }
  const btn = $("doImportPreviewBtn");
  if (btn) { btn.disabled = true; btn.textContent = "预检中..."; }
  setImportPreview("正在检查，请稍候...");
  try {
    const res = await backupRequest("importPreview", { method: "POST", body: { source } });
    if (res && res.ok) {
      renderImportPreview(res);
    } else {
      setImportPreview(`❌ ${(res && res.msg) || "预检失败"}`, "err");
    }
  } catch (e) {
    console.warn("[backup] 预检失败:", e);
    setImportPreview(`❌ 预检失败：${(e && e.message) || e}`, "err");
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "先预检"; }
  }
}

async function onDoImport() {
  const input = $("importSourceInput");
  const source = (input && input.value.trim()) || "";
  if (!source) {
    setImportPreview("请先填写备份目录或备份包路径", "err");
    return;
  }
  const mode = importCheckboxMergeSkip() ? "merge_skip" : "replace";
  const modeText = mode === "merge_skip" ? "仅补充缺失文件" : "覆盖导入";
  if (!confirm(`确认以「${modeText}」方式导入？\n\n来源：${source}\n\n导入前会自动备份当前数据，可随时回退。`)) {
    return;
  }

  const btn = $("doImportBtn");
  if (btn) { btn.disabled = true; btn.textContent = "导入中..."; }
  setImportPreview("正在导入，请稍候...");
  try {
    const res = await backupRequest("importData", { method: "POST", body: { source, mode } });
    if (res && res.ok) {
      const n = (res.imported || []).length;
      const sk = (res.skipped || []).length;
      let text = `✅ ${res.msg}`;
      if (res.backup_dir) text += `\n导入前备份：${res.backup_dir}`;
      text += `\n\n💡 数据已写入，刷新页面即可看到最新内容`;
      setImportPreview(text, "ok");
      toast(`✅ 已导入 ${n} 个文件${sk ? `，跳过 ${sk} 个` : ""}`);
    } else {
      setImportPreview(`❌ ${(res && res.msg) || "导入失败"}`, "err");
      toast("导入失败", "error");
    }
  } catch (e) {
    console.warn("[backup] 导入失败:", e);
    setImportPreview(`❌ 导入失败：${(e && e.message) || e}`, "err");
    toast("导入失败", "error");
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "确认导入"; }
  }
}

// ============================================================
// 渲染
// ============================================================
function renderView(viewKey) {
  const view = VIEWS[viewKey];
  if (!view) return;
  $("pageTitle").textContent = view.title;
  $("topbarActions").innerHTML = `<button class="btn btn-muted" id="backupOpenBtn">💾 导出数据</button><button class="btn btn-primary" id="saveAllBtn">💾 保存全部</button>`;

  let html = "";
  for (const group of view.groups) {
    html += `<div class="section">`;
    html += `<div class="section-header"><div class="section-title">${esc(group.title)}</div></div>`;

    if (group.type === "menu-preview") {
      html += `<div class="menu-preview">${esc(menuPreviewText())}</div>`;
    } else if (group.type === "status-panel") {
      html += buildStatusPanelHtml();
    } else {
      for (const key of group.keys) {
        const s = SCHEMA[key];
        if (!s) {
          console.warn(`[render] SCHEMA 缺少字段: ${key}`);
          continue;
        }
        const type = s.type || "string";
        if (type === "bool") html += renderBool(key);
        else if (type === "int") html += renderInt(key);
        else if (type === "text") html += renderString(key, { textarea: true });
        else if (type === "template_list") html += renderTemplateList(key);
        else html += renderString(key);
      }
    }
    html += `</div>`;
  }

  $("content").innerHTML = html;
  const saveBtn = $("saveAllBtn");
  if (saveBtn) saveBtn.addEventListener("click", onSaveAll);
  const backupBtn = $("backupOpenBtn");
  if (backupBtn) backupBtn.addEventListener("click", openBackupModal);

  const refreshBtn = $("refreshStatusBtn");
  if (refreshBtn) refreshBtn.addEventListener("click", fetchStatusPreview);
  const testBtn = $("testPushBtn");
  if (testBtn) testBtn.addEventListener("click", onTestPush);

  attachTemplateEvents();
}

function menuPreviewText() {
  return `━━━ 主菜单 ━━━
🎭 接口系统    ⛏ MC系统
📅 打卡系统    💰 签到系统
🎲 每日系列    🔧 管理系统
━━━━━━━━━━━━`;
}

// ============================================================
// 收集表单数据
// ============================================================
function collectFormData() {
  const data = {};

  document.querySelectorAll("[data-cfg]").forEach(el => {
    const key = el.dataset.cfg;
    const type = el.dataset.type;
    if (type === "bool") data[key] = el.checked;
    else if (type === "int") data[key] = parseInt(el.value) || 0;
    else data[key] = el.value;
  });

  document.querySelectorAll(".template-list").forEach(listEl => {
    const key = listEl.dataset.tplkey;
    const arr = [];
    listEl.querySelectorAll(".template-item").forEach(itemEl => {
      const obj = { __template_key: Object.keys((SCHEMA[key] || {}).templates || {})[0] || "" };
      itemEl.querySelectorAll("[data-field]").forEach(f => {
        obj[f.dataset.field] = f.value;
      });
      arr.push(obj);
    });
    data[key] = arr;
  });

  return data;
}

// ============================================================
// 保存全部
// ============================================================
async function onSaveAll() {
  const btn = $("saveAllBtn");
  if (!btn) return;
  btn.disabled = true;
  btn.textContent = "保存中...";
  try {
    const data = collectFormData();
    console.log("[save] 待提交:", data);
    const ok = await saveConfig(data);
    if (ok) toast("✅ 配置已保存，重启 AstrBot 生效");
    else toast("❌ 保存失败，请查看控制台", "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "💾 保存全部";
  }
}

// ============================================================
// template_list 增删事件
// ============================================================
function attachTemplateEvents() {
  document.querySelectorAll("[data-action='add-tpl']").forEach(btn => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.key;
      const data = collectFormData();
      if (!Array.isArray(data[key])) data[key] = [];
      const tplKey = Object.keys((SCHEMA[key] || {}).templates || {})[0] || "";
      const newItem = { __template_key: tplKey };
      const fields = Object.keys(((SCHEMA[key] || {}).templates || {})[tplKey]?.items || {});
      fields.forEach(f => newItem[f] = "");
      data[key].push(newItem);
      CONFIG[key] = data[key];
      renderView(currentView);
    });
  });

  document.querySelectorAll("[data-action='del-tpl']").forEach(btn => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.key;
      const idx = parseInt(btn.dataset.idx);
      if (!confirm(`确定删除该条目 #${idx + 1}？`)) return;
      const data = collectFormData();
      if (Array.isArray(data[key])) {
        data[key].splice(idx, 1);
        CONFIG[key] = data[key];
        renderView(currentView);
      }
    });
  });
}

// ============================================================
// 导航
// ============================================================
document.querySelectorAll(".nav-item").forEach(item => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
    item.classList.add("active");
    currentView = item.dataset.view;
    renderView(currentView);
  });
});

// ============================================================
// 主题切换
// ============================================================
const themeBtn = $("themeToggleBtn");
if (themeBtn) {
  themeBtn.addEventListener("click", () => {
    const html = document.documentElement;
    html.setAttribute("data-theme", (html.getAttribute("data-theme") || "light") === "dark" ? "light" : "dark");
  });
}

// ============================================================
// 重新加载
// ============================================================
const reloadBtn = $("reloadBtn");
if (reloadBtn) {
  reloadBtn.addEventListener("click", () => location.reload());
}

// ============================================================
// 模态框（备用）
// ============================================================
const closeModal = $("closeEditModal");
if (closeModal) closeModal.addEventListener("click", () => $("editModal").classList.remove("open"));
const cancelModal = $("cancelEditBtn");
if (cancelModal) cancelModal.addEventListener("click", () => $("editModal").classList.remove("open"));

// ============================================================
// 启动流程（★ 桥接失败不阻塞，继续走 fetch）
// ============================================================
async function boot() {
  $("content").innerHTML = '<div class="loading">加载中...</div>';
  $("errorOverlay").classList.remove("show");

  console.log("=".repeat(60));
  console.log("[boot] 鸡鸡娱乐系统配置页启动");
  console.log("[boot] window.AstrBotPluginPage:", bridge);
  console.log("=".repeat(60));

  const okBridge = await initBridge();
  // ★ 桥接失败也继续往下走，让 fetch 兜底
  const okLoad = await loadAllConfig();

  if (!okLoad) {
    $("errorOverlay").classList.add("show");
    $("errorBridgeStatus").textContent = okBridge ? "已就绪" : "不可用";
    const errEl = $("errorMsg");
    if (errEl && !errEl.textContent.trim()) {
      errEl.textContent = "无法读取插件配置，请检查后端路由是否注册成功，或查看浏览器控制台日志。";
    }
    return;
  }

  $("errorOverlay").classList.remove("show");
  renderView(currentView);
}

const retryBtn = $("retryBtn");
if (retryBtn) retryBtn.addEventListener("click", () => boot());

// 备份弹窗事件
const _bkClose = $("closeBackupModal");
if (_bkClose) _bkClose.addEventListener("click", closeBackupModal);
const _bkClose2 = $("closeBackupBtn");
if (_bkClose2) _bkClose2.addEventListener("click", closeBackupModal);
const _bkDo = $("doBackupBtn");
if (_bkDo) _bkDo.addEventListener("click", onDoBackup);
const _bkDl = $("doDownloadBtn");
if (_bkDl) _bkDl.addEventListener("click", onDownloadBackup);
const _bkImpPrev = $("doImportPreviewBtn");
if (_bkImpPrev) _bkImpPrev.addEventListener("click", onImportPreview);
const _bkImp = $("doImportBtn");
if (_bkImp) _bkImp.addEventListener("click", onDoImport);
const _bkOverlay = $("backupModal");
if (_bkOverlay) {
  _bkOverlay.addEventListener("click", (e) => {
    if (e.target === _bkOverlay) closeBackupModal();
  });
}

// 键盘快捷键 R：无输入焦点时强制刷新
document.addEventListener("keydown", (e) => {
  if (e.key.toLowerCase() === "r" && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
    location.reload();
  }
});

boot();