"""
每日定时状态推送模块。

特性：
  - 后台总开关 + 默认推送时间（HH:MM，分钟级）
  - 每个群可单独开关、单独指定推送时间
  - 每群记录 unified_msg_origin，用于主动推送
  - 按「日期 + 时间点」防重，避免同一分钟重复推送
  - 供远程指令查询/设置（支持指定群号）

与 hourly_chime 同样使用模块级全局锁 + 每次加锁前重载磁盘，
避免多实例并发覆盖状态文件。
"""

import os
import json
import time
import datetime
import threading
from astrbot.api import logger

# ★ 模块级全局锁，防止多实例并发覆盖
_GLOBAL_PUSH_LOCK = threading.Lock()

DEFAULT_TIME = "09:00"


# ============================================================
# 工具
# ============================================================
def now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d")


def now_hm() -> str:
    return datetime.datetime.now().strftime("%H:%M")


def parse_hhmm(raw) -> str:
    """把 9 / 9:5 / 09:00 / 9：00 等输入规范成 HH:MM；非法返回空串。"""
    if raw is None:
        return ""
    text = str(raw).strip()
    if not text:
        return ""
    # 统一全角冒号与点号
    text = text.replace("：", ":").replace(".", ":").replace("。", ":")
    if ":" not in text:
        # 只给了小时
        if text.isdigit():
            h = int(text)
            if 0 <= h <= 23:
                return f"{h:02d}:00"
        return ""
    parts = text.split(":")
    if len(parts) != 2:
        return ""
    hh, mm = parts[0].strip(), parts[1].strip()
    if not hh.isdigit() or not mm.isdigit():
        return ""
    h, m = int(hh), int(mm)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return ""
    return f"{h:02d}:{m:02d}"


class StatusPushModule:
    """每日定时状态推送模块"""

    def __init__(self, plugin_dir: str, data_path: str):
        self.plugin_dir = plugin_dir
        self.data_path = data_path

        # 全局配置（由 reload 注入）
        self.enable = False
        self.default_time = DEFAULT_TIME
        self.interval = 30

        # 每群状态：{group_id: {"on": bool, "time": "HH:MM"}}
        self.groups = {}
        # 已推送记录：{group_id: "YYYY-MM-DD HH:MM"}
        self.last_push = {}
        # 主动推送用：{group_id: unified_msg_origin}
        self.umos = {}

        self._load_state()

    # ============================================================
    # 配置
    # ============================================================
    def reload(self, cfg: dict):
        cfg = cfg if isinstance(cfg, dict) else {}
        self.enable = bool(cfg.get("daily_status_push_enable", False))

        t = parse_hhmm(cfg.get("daily_status_push_time", DEFAULT_TIME))
        self.default_time = t or DEFAULT_TIME

        try:
            itv = int(str(cfg.get("daily_status_push_interval", "30")).strip() or "30")
        except Exception:
            itv = 30
        self.interval = max(10, itv)

    # ============================================================
    # 状态持久化（加锁由调用方保证）
    # ============================================================
    def _load_state(self):
        if not self.data_path or not os.path.exists(self.data_path):
            return
        try:
            with open(self.data_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f) or {}
            self.groups = data.get("groups", {}) or {}
            self.last_push = data.get("last_push", {}) or {}
            self.umos = data.get("umos", {}) or {}
        except Exception:
            logger.exception("[status_push] 读取状态失败")

    def _save_state(self):
        if not self.data_path:
            return
        try:
            tmp = self.data_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "groups": self.groups,
                        "last_push": self.last_push,
                        "umos": self.umos,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            os.replace(tmp, self.data_path)
        except Exception:
            logger.exception("[status_push] 保存状态失败")

    # ============================================================
    # UMO 记录
    # ============================================================
    def record_context(self, group_id, umo: str = ""):
        """记录群最近一次可用的 UMO，供定时推送复用。"""
        gid = str(group_id or "").strip()
        umo = str(umo or "").strip()
        if not gid or not umo:
            return
        # 快速路径：内存中已是同一个 UMO，直接返回，避免频繁加锁和写盘
        if self.umos.get(gid) == umo:
            return
        with _GLOBAL_PUSH_LOCK:
            self._load_state()
            if self.umos.get(gid) != umo:
                self.umos[gid] = umo
                self._save_state()

    def get_umo(self, group_id) -> str:
        return str(self.umos.get(str(group_id), "") or "")

    # ============================================================
    # 每群配置
    # ============================================================
    def _group_cfg(self, group_id) -> dict:
        gid = str(group_id)
        cfg = self.groups.get(gid)
        if not isinstance(cfg, dict):
            cfg = {"on": False, "time": ""}
        return cfg

    def is_group_on(self, group_id) -> bool:
        return bool(self._group_cfg(group_id).get("on", False))

    def get_group_time(self, group_id) -> str:
        """返回该群生效的推送时间（群自定义优先，否则全局默认）"""
        raw = self._group_cfg(group_id).get("time", "")
        return parse_hhmm(raw) or self.default_time

    def get_group_raw_time(self, group_id) -> str:
        """返回该群显式设置的时间（未设置为空串）"""
        return parse_hhmm(self._group_cfg(group_id).get("time", ""))

    def set_group_on(self, group_id, on: bool):
        with _GLOBAL_PUSH_LOCK:
            self._load_state()
            gid = str(group_id)
            cfg = self._group_cfg(gid)
            cfg["on"] = bool(on)
            cfg.setdefault("time", "")
            self.groups[gid] = cfg
            self._save_state()

    def set_group_time(self, group_id, hhmm: str) -> bool:
        """设置群推送时间；传空串表示恢复使用全局默认时间。"""
        text = str(hhmm or "").strip()
        if text:
            parsed = parse_hhmm(text)
            if not parsed:
                return False
        else:
            parsed = ""
        with _GLOBAL_PUSH_LOCK:
            self._load_state()
            gid = str(group_id)
            cfg = self._group_cfg(gid)
            cfg["time"] = parsed
            cfg.setdefault("on", False)
            self.groups[gid] = cfg
            self._save_state()
        return True

    def get_all_group_ids(self) -> list:
        with _GLOBAL_PUSH_LOCK:
            self._load_state()
            return list(self.groups.keys())

    def list_groups(self) -> list:
        out = []
        for gid, cfg in self.groups.items():
            if not isinstance(cfg, dict) or not cfg.get("on"):
                continue
            out.append({
                "group_id": gid,
                "time": self.get_group_time(gid),
                "custom": bool(self.get_group_raw_time(gid)),
            })
        return sorted(out, key=lambda x: x["group_id"])

    # ============================================================
    # 到点判定 + 防重（原子）
    # ============================================================
    def check_and_mark(self, group_id, hhmm: str) -> bool:
        """
        在全局锁内完成：重载磁盘 -> 校验开关 -> 校验时间是否到点 -> 标记已推送。
        返回 True 表示本轮应当推送。
        """
        target = parse_hhmm(hhmm)
        if not target:
            return False
        with _GLOBAL_PUSH_LOCK:
            self._load_state()
            gid = str(group_id)
            if not self.is_group_on(gid):
                return False
            if self.get_group_time(gid) != target:
                return False
            key = f"{today_str()} {target}"
            if self.last_push.get(gid) == key:
                return False
            self.last_push[gid] = key
            # 清理过期记录，避免无限增长
            if len(self.last_push) > 500:
                today = today_str()
                stale = [k for k, v in self.last_push.items()
                         if not str(v).startswith(today)]
                for k in stale:
                    self.last_push.pop(k, None)
            self._save_state()
            return True

    def pending_groups(self, hhmm: str) -> list:
        """返回当前时间点应当推送的群号列表（无副作用，供测试/调试）。"""
        target = parse_hhmm(hhmm)
        if not target:
            return []
        out = []
        for gid in self.get_all_group_ids():
            if not self.is_group_on(gid):
                continue
            if self.get_group_time(gid) == target:
                out.append(gid)
        return sorted(out)
