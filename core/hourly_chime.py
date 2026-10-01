import os
import json
import time
import datetime
import threading
from astrbot.api import logger

# ★ 新增：模块级全局锁，防止多实例并发覆盖
_GLOBAL_CHIME_LOCK = threading.Lock()


def _now_hour() -> int:
    return datetime.datetime.now().hour


def _today_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d")


def _fmt_time(ts=None) -> str:
    if ts is None:
        ts = time.time()
    try:
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "（未知）"


class HourlyChimeModule:
    """
    整点报时模块：
      - 按群开启/关闭
      - 默认整点报时（0-23 全部整点），也可只报指定整点
      - 支持自定义报时文案（{hour} 占位符）
      - 后台每 N 秒轮询一次，命中整点则推送
      - 每个群保存一份 unified_msg_origin，用于主动推送
      - 支持手动触发测试推送（不写 last_chime，不影响正常整点判重）
    """

    def __init__(self, plugin_dir: str, data_path: str):
        self.plugin_dir = plugin_dir
        self.data_path = data_path
        self.enable = True
        self.interval = 30
        self.default_template = "🕐 现在是 {hour} 点整，整点报时！"
        self.groups = {}
        self.last_chime = {}
        self.umos = {}   # {group_id: unified_msg_origin}
        self._load_state()

    # ============================================================
    # 配置
    # ============================================================
    def reload(self, cfg: dict):
        self.enable = bool(cfg.get("hourly_chime_enable", True))
        try:
            itv = int(str(cfg.get("hourly_chime_interval", "30")).strip() or "30")
        except Exception:
            itv = 30
        if itv < 5:
            itv = 5
        self.interval = itv
        self.default_template = str(
            cfg.get("hourly_chime_template", "🕐 现在是 {hour} 点整，整点报时！")
            or "🕐 现在是 {hour} 点整，整点报时！"
        ).strip()

    # ============================================================
    # 状态持久化（加锁由调用方保证）
    # ============================================================
    def _load_state(self):
        if not os.path.exists(self.data_path):
            return
        try:
            with open(self.data_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f) or {}
            self.groups = data.get("groups", {}) or {}
            self.last_chime = data.get("last_chime", {}) or {}
            self.umos = data.get("umos", {}) or {}
        except Exception:
            logger.exception("[hourly_chime] 读取状态失败")

    def _save_state(self):
        try:
            tmp = self.data_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "groups": self.groups,
                        "last_chime": self.last_chime,
                        "umos": self.umos,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            os.replace(tmp, self.data_path)
        except Exception:
            logger.exception("[hourly_chime] 保存状态失败")

    # ============================================================
    # UMO 记录（用于主动推送）
    # ============================================================
    def record_umo(self, group_id, umo: str):
        if not group_id or not umo:
            return
        gid = str(group_id)
        # 快速路径：内存中已存在相同的 UMO，直接返回，避免频繁加锁和写盘
        if self.umos.get(gid) == umo:
            return
            
        with _GLOBAL_CHIME_LOCK:
            # 强制读取磁盘最新状态，防止覆盖其他协程的修改
            self._load_state()
            if self.umos.get(gid) != umo:
                self.umos[gid] = umo
                self._save_state()

    def get_umo(self, group_id) -> str:
        return self.umos.get(str(group_id), "")

    # ============================================================
    # 群开关
    # ============================================================
    def is_group_on(self, group_id) -> bool:
        gid = str(group_id)
        cfg = self.groups.get(gid)
        if not isinstance(cfg, dict):
            return False
        return bool(cfg.get("on", False))

    def set_group_on(self, group_id, on: bool):
        with _GLOBAL_CHIME_LOCK:
            # 强制重新加载磁盘最新状态，防止并发覆盖
            self._load_state()
            gid = str(group_id)
            cfg = self.groups.get(gid)
            if not isinstance(cfg, dict):
                cfg = {"on": False, "template": "", "hours": []}
            cfg["on"] = bool(on)
            self.groups[gid] = cfg
            self._save_state()

    def get_group_hours(self, group_id) -> list:
        gid = str(group_id)
        cfg = self.groups.get(gid)
        if not isinstance(cfg, dict):
            return []
        hours = cfg.get("hours", [])
        if not isinstance(hours, list):
            return []
        out = []
        for h in hours:
            try:
                n = int(h)
                if 0 <= n <= 23 and n not in out:
                    out.append(n)
            except Exception:
                continue
        return sorted(out)

    def set_group_hours(self, group_id, hours: list):
        with _GLOBAL_CHIME_LOCK:
            self._load_state()
            gid = str(group_id)
            cfg = self.groups.get(gid)
            if not isinstance(cfg, dict):
                cfg = {"on": False, "template": "", "hours": []}
            cleaned = []
            for h in hours:
                try:
                    n = int(h)
                    if 0 <= n <= 23 and n not in cleaned:
                        cleaned.append(n)
                except Exception:
                    continue
            cfg["hours"] = sorted(cleaned)
            self.groups[gid] = cfg
            self._save_state()

    def get_group_template(self, group_id) -> str:
        gid = str(group_id)
        cfg = self.groups.get(gid)
        if not isinstance(cfg, dict):
            return ""
        return str(cfg.get("template", "")).strip()

    def set_group_template(self, group_id, template: str):
        with _GLOBAL_CHIME_LOCK:
            self._load_state()
            gid = str(group_id)
            cfg = self.groups.get(gid)
            if not isinstance(cfg, dict):
                cfg = {"on": False, "template": "", "hours": []}
            cfg["template"] = str(template or "").strip()
            self.groups[gid] = cfg
            self._save_state()

    def list_groups(self) -> list:
        out = []
        for gid, cfg in self.groups.items():
            if not isinstance(cfg, dict):
                continue
            if not cfg.get("on"):
                continue
            out.append({
                "group_id": gid,
                "hours": self.get_group_hours(gid),
                "template": self.get_group_template(gid) or self.default_template,
            })
        return out

    def get_all_group_ids(self) -> list:
        """获取所有配置过的群ID（供后台任务遍历）"""
        with _GLOBAL_CHIME_LOCK:
            self._load_state()
            return list(self.groups.keys())

    # ============================================================
    # 文案渲染
    # ============================================================
    def render_text(self, template: str, hour: int) -> str:
        if not template:
            template = self.default_template
        try:
            return template.format(hour=hour)
        except Exception:
            return template.replace("{hour}", str(hour))

    # ============================================================
    # ★ 核心修复：原子检查并标记
    # ============================================================
    def check_and_mark(self, group_id, hour: int) -> bool:
        """
        在全局锁内完成：重新加载磁盘最新状态 -> 检查开关/时间 -> 标记已发送 -> 保存。
        彻底解决多实例并发导致的重复发送问题。
        """
        with _GLOBAL_CHIME_LOCK:
            # 强制从文件重新加载最新状态
            self._load_state()
            
            gid = str(group_id)
            # 1. 检查开关是否开启
            if not self.is_group_on(gid):
                return False
                
            # 2. 检查报时时段
            hours = self.get_group_hours(gid)
            if hours and hour not in hours:
                return False
                
            # 3. 检查今天该整点是否已报时
            today = _today_str()
            key = f"{today} {hour:02d}"
            if self.last_chime.get(gid) == key:
                return False
                
            # 4. 标记为已发送，并在锁内写入磁盘
            self.last_chime[gid] = key
            if len(self.last_chime) > 500:
                keys_to_remove = [k for k, v in self.last_chime.items() if not v.startswith(today)]
                for k in keys_to_remove:
                    self.last_chime.pop(k, None)
                    
            self._save_state()
            return True

    # ============================================================
    # 手动触发（测试用，不写 last_chime）
    # ============================================================
    def build_manual_text(self, group_id, hour: int = None) -> str:
        """构造手动测试推送的文案（不加"测试"前缀，保持和正常报时一致）"""
        if hour is None:
            hour = _now_hour()
        tpl = self.get_group_template(group_id) or self.default_template
        return self.render_text(tpl, hour)