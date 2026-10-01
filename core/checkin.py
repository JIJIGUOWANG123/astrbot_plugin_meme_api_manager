import os
import json
import time
import random
import datetime
from astrbot.api import logger


def _today_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d")


def _month_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m")


def get_group_id(event) -> str:
    try:
        mo = getattr(event, "message_obj", None)
        if mo is not None:
            gid = getattr(mo, "group_id", "") or getattr(mo, "group", "") or ""
            if gid:
                return str(gid)
    except Exception:
        pass
    try:
        gid = getattr(event, "group_id", "") or ""
        if gid:
            return str(gid)
    except Exception:
        pass
    return ""


def get_user_id(event) -> str:
    try:
        uid = event.get_sender_id() or ""
        if uid:
            return str(uid)
    except Exception:
        pass
    try:
        uid = getattr(event, "user_id", "") or ""
        if uid:
            return str(uid)
    except Exception:
        pass
    return "unknown"


def get_user_name(event) -> str:
    for attr in ("sender_name", "sender_nickname", "nickname", "nick"):
        try:
            v = getattr(event, attr, None)
            if v:
                return str(v)
        except Exception:
            pass
    try:
        mo = getattr(event, "message_obj", None)
        if mo is not None:
            for attr in ("sender_name", "sender_nickname", "nickname"):
                v = getattr(mo, attr, None)
                if v:
                    return str(v)
            sender = getattr(mo, "sender", None)
            if sender is not None:
                for attr in ("nickname", "card", "name"):
                    v = getattr(sender, attr, None)
                    if v:
                        return str(v)
    except Exception:
        pass
    return ""


def _fmt_time(ts: float) -> str:
    try:
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "（未知）"


class CheckinModule:
    def __init__(self, plugin_dir: str, data_path: str):
        self.plugin_dir = plugin_dir
        self.data_path = data_path
        self.enable = True
        self.trigger_names = ["签到"]
        self.rank_trigger_names = ["签到排行"]
        self.info_trigger_names = ["签到统计", "我的签到", "查询签到"]

        self.steal_enable = True
        self.steal_trigger_names = ["偷积分", "偷分"]
        self.steal_min = 1
        self.steal_max = 100
        self.steal_success_rate = 50
        self.steal_fail_punish_rate = 50
        self.steal_punish_min = 1
        self.steal_punish_max = 100

        self.bank_enable = True
        self.bank_trigger_names = ["银行", "我的银行"]
        self.bank_deposit_names = ["存钱", "存款"]
        self.bank_withdraw_names = ["取钱", "取款"]
        self.bank_interest_rate = 0.01
        self.bank_interest_hour = 0

        # ============ 打工配置 ============
        self.job_enable = True
        self.job_trigger_names = ["打工", "干活"]
        self.job_info_trigger_names = ["打工列表", "工作列表", "工种"]
        self.job_list = []  # [{"name": "", "duration_hours": 1, "reward_min": 10, "reward_max": 100}]
        self.cmd_job_add_names = ["添加工种", "新增工种"]
        self.cmd_job_del_names = ["删除工种", "删工种"]

        self.mount_enable = True
        self.mount_trigger_names = ["坐骑", "我的坐骑"]
        self.mount_list_trigger_names = ["坐骑列表", "坐骑商店"]
        self.mount_buy_trigger_names = ["购买坐骑", "买坐骑"]
        self.cmd_mount_add_names = ["添加坐骑", "新增坐骑"]
        self.cmd_mount_del_names = ["删除坐骑", "删坐骑"]

        self.group_mode = "off"
        self.group_whitelist = []
        self.group_blacklist = []

        self.users = {}
        self.daily = {}
        self.speaks = {}
        self.last_interest_date = ""

        # ★ 由 main.py 注入的全局昵称缓存
        self.nickname_cache = {}

        self._load()

    def reload(self, cfg: dict):
        self.enable = bool(cfg.get("checkin_enable", True))

        raw = str(cfg.get("checkin_trigger_names", "签到") or "").strip()
        names = [x.strip() for x in raw.split(",") if x.strip()]
        self.trigger_names = names if names else ["签到"]

        raw = str(cfg.get("checkin_rank_trigger_names", "签到排行") or "").strip()
        names = [x.strip() for x in raw.split(",") if x.strip()]
        self.rank_trigger_names = names if names else ["签到排行"]

        raw = str(cfg.get("checkin_info_trigger_names", "签到统计,我的签到,查询签到") or "").strip()
        names = [x.strip() for x in raw.split(",") if x.strip()]
        self.info_trigger_names = names if names else ["签到统计"]

        self.steal_enable = bool(cfg.get("steal_enable", True))
        raw = str(cfg.get("steal_trigger_names", "偷积分,偷分") or "").strip()
        names = [x.strip() for x in raw.split(",") if x.strip()]
        self.steal_trigger_names = names if names else ["偷积分"]
        try:
            self.steal_min = max(1, int(str(cfg.get("steal_min", "1")).strip() or "1"))
        except Exception:
            self.steal_min = 1
        try:
            self.steal_max = max(self.steal_min, int(str(cfg.get("steal_max", "100")).strip() or "100"))
        except Exception:
            self.steal_max = 100
        try:
            self.steal_success_rate = max(0, min(100, int(str(cfg.get("steal_success_rate", "50")).strip() or "50")))
        except Exception:
            self.steal_success_rate = 50
        try:
            self.steal_fail_punish_rate = max(0, min(100, int(str(cfg.get("steal_fail_punish_rate", "50")).strip() or "50")))
        except Exception:
            self.steal_fail_punish_rate = 50
        try:
            self.steal_punish_min = max(1, int(str(cfg.get("steal_punish_min", "1")).strip() or "1"))
        except Exception:
            self.steal_punish_min = 1
        try:
            self.steal_punish_max = max(self.steal_punish_min, int(str(cfg.get("steal_punish_max", "100")).strip() or "100"))
        except Exception:
            self.steal_punish_max = 100

        self.bank_enable = bool(cfg.get("bank_enable", True))
        raw = str(cfg.get("bank_trigger_names", "银行,我的银行") or "").strip()
        names = [x.strip() for x in raw.split(",") if x.strip()]
        self.bank_trigger_names = names if names else ["银行"]
        raw = str(cfg.get("bank_deposit_names", "存钱,存款") or "").strip()
        names = [x.strip() for x in raw.split(",") if x.strip()]
        self.bank_deposit_names = names if names else ["存钱"]
        raw = str(cfg.get("bank_withdraw_names", "取钱,取款") or "").strip()
        names = [x.strip() for x in raw.split(",") if x.strip()]
        self.bank_withdraw_names = names if names else ["取钱"]
        try:
            self.bank_interest_rate = float(str(cfg.get("bank_interest_rate", "0.01")).strip() or "0.01")
        except Exception:
            self.bank_interest_rate = 0.01
        if self.bank_interest_rate < 0:
            self.bank_interest_rate = 0
        try:
            self.bank_interest_hour = max(0, min(23, int(str(cfg.get("bank_interest_hour", "0")).strip() or "0")))
        except Exception:
            self.bank_interest_hour = 0

        self.group_mode = str(cfg.get("checkin_group_mode", "off") or "off").strip().lower()
        if self.group_mode not in ("off", "whitelist", "blacklist"):
            self.group_mode = "off"
        self.group_whitelist = self._parse_lines(cfg.get("checkin_group_whitelist", ""))
        self.group_blacklist = self._parse_lines(cfg.get("checkin_group_blacklist", ""))

        # ============ 坐骑配置 ============
        self.mount_enable = bool(cfg.get("mount_enable", True))

        raw = str(cfg.get("mount_trigger_names", "坐骑,我的坐骑") or "").strip()
        names = [x.strip() for x in raw.split(",") if x.strip()]
        self.mount_trigger_names = names if names else ["坐骑"]

        raw = str(cfg.get("mount_list_trigger_names", "坐骑列表,坐骑商店") or "").strip()
        names = [x.strip() for x in raw.split(",") if x.strip()]
        self.mount_list_trigger_names = names if names else ["坐骑列表"]

        raw = str(cfg.get("mount_buy_trigger_names", "购买坐骑,买坐骑") or "").strip()
        names = [x.strip() for x in raw.split(",") if x.strip()]
        self.mount_buy_trigger_names = names if names else ["购买坐骑"]

        mount_list_raw = cfg.get("mount_list", [])
        self.mount_list = []
        if isinstance(mount_list_raw, list):
            for item in mount_list_raw:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", "")).strip()
                try:
                    price = int(str(item.get("price", "0")).strip() or "0")
                except Exception:
                    price = 0
                desc = str(item.get("desc", "")).strip()
                if name:
                    self.mount_list.append({
                        "name": name,
                        "price": max(0, price),
                        "desc": desc,
                    })

        # ============ 打工配置 ============
        self.job_enable = bool(cfg.get("job_enable", True))

        raw = str(cfg.get("job_trigger_names", "打工,干活") or "").strip()
        names = [x.strip() for x in raw.split(",") if x.strip()]
        self.job_trigger_names = names if names else ["打工"]

        raw = str(cfg.get("job_info_trigger_names", "打工列表,工作列表,工种") or "").strip()
        names = [x.strip() for x in raw.split(",") if x.strip()]
        self.job_info_trigger_names = names if names else ["打工列表"]

        job_list_raw = cfg.get("job_list", [])
        self.job_list = []
        if isinstance(job_list_raw, list):
            for item in job_list_raw:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", "")).strip()
                try:
                    dur = int(str(item.get("duration_hours", "1")).strip() or "1")
                except Exception:
                    dur = 1
                try:
                    rmin = int(str(item.get("reward_min", "10")).strip() or "10")
                except Exception:
                    rmin = 10
                try:
                    rmax = int(str(item.get("reward_max", "100")).strip() or "100")
                except Exception:
                    rmax = 100
                if dur < 1:
                    dur = 1
                if rmin < 0:
                    rmin = 0
                if rmax < rmin:
                    rmax = rmin
                if name:
                    self.job_list.append({
                        "name": name,
                        "duration_hours": dur,
                        "reward_min": rmin,
                        "reward_max": rmax,
                    })

        raw = str(cfg.get("cmd_job_add_names", "添加工种,新增工种") or "").strip()
        names = [x.strip() for x in raw.split(",") if x.strip()]
        self.cmd_job_add_names = names if names else ["添加工种"]

        raw = str(cfg.get("cmd_job_del_names", "删除工种,删工种") or "").strip()
        names = [x.strip() for x in raw.split(",") if x.strip()]
        self.cmd_job_del_names = names if names else ["删除工种"]

        raw = str(cfg.get("cmd_mount_add_names", "添加坐骑,新增坐骑") or "").strip()
        names = [x.strip() for x in raw.split(",") if x.strip()]
        self.cmd_mount_add_names = names if names else ["添加坐骑"]

        raw = str(cfg.get("cmd_mount_del_names", "删除坐骑,删坐骑") or "").strip()
        names = [x.strip() for x in raw.split(",") if x.strip()]
        self.cmd_mount_del_names = names if names else ["删除坐骑"]

    @staticmethod
    def _parse_lines(raw) -> list:
        if not raw:
            return []
        if isinstance(raw, list):
            out = []
            for it in raw:
                if isinstance(it, str):
                    out.extend(it.splitlines())
        else:
            out = str(raw).splitlines()
        return [x.strip() for x in out if x.strip() and not x.strip().startswith("#")]

    def _is_group_allowed(self, group_id: str) -> bool:
        if not group_id:
            return True
        if self.group_mode == "whitelist":
            return group_id in self.group_whitelist
        if self.group_mode == "blacklist":
            return group_id not in self.group_blacklist
        return True

    def _load(self):
        if not os.path.exists(self.data_path):
            return
        try:
            with open(self.data_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f) or {}
            self.users = data.get("users", {}) or {}
            self.daily = data.get("daily", {}) or {}
            self.speaks = data.get("speaks", {}) or {}
            self.last_interest_date = data.get("last_interest_date", "") or ""
        except Exception:
            logger.exception("[checkin] 读取失败")

    def _save(self):
        try:
            tmp = self.data_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({
                    "users": self.users,
                    "daily": self.daily,
                    "speaks": self.speaks,
                    "last_interest_date": self.last_interest_date,
                }, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.data_path)
        except Exception:
            logger.exception("[checkin] 保存失败")

    def match_trigger(self, text: str) -> bool:
        if not self.enable:
            return False
        for name in self.trigger_names:
            if text == name or text == f"/{name}":
                return True
        return False

    def match_rank_trigger(self, text: str) -> bool:
        if not self.enable:
            return False
        for name in self.rank_trigger_names:
            if text == name or text == f"/{name}":
                return True
        return False

    def match_info_trigger(self, text: str):
        if not self.enable:
            return None
        for name in self.info_trigger_names:
            if text == name or text == f"/{name}":
                return ("self",)
            for prefix in (name + " ", f"/{name} "):
                if text.startswith(prefix):
                    arg = text[len(prefix):].strip()
                    if arg:
                        return ("target", arg)
                    return ("self",)
        return None

    def match_steal_trigger(self, text: str):
        if not self.enable or not self.steal_enable:
            return None
        for name in self.steal_trigger_names:
            if text == name or text == f"/{name}":
                return ("self",)
            for prefix in (name + " ", f"/{name} "):
                if text.startswith(prefix):
                    arg = text[len(prefix):].strip()
                    if arg:
                        return ("target", arg)
                    return ("self",)
        return None

    def match_bank_trigger(self, text: str) -> bool:
        if not self.enable or not self.bank_enable:
            return False
        for name in self.bank_trigger_names:
            if text == name or text == f"/{name}":
                return True
        return False

    def match_deposit_trigger(self, text: str):
        if not self.enable or not self.bank_enable:
            return None
        for name in self.bank_deposit_names:
            for prefix in (name + " ", f"/{name} "):
                if text.startswith(prefix):
                    arg = text[len(prefix):].strip()
                    return ("amount", arg) if arg else ("amount", "")
            if text == name or text == f"/{name}":
                return ("amount", "")
        return None

    # ============================================================
    # 发言统计
    # ============================================================
    def match_withdraw_trigger(self, text: str):
        if not self.enable or not self.bank_enable:
            return None
        for name in self.bank_withdraw_names:
            for prefix in (name + " ", f"/{name} "):
                if text.startswith(prefix):
                    arg = text[len(prefix):].strip()
                    return ("amount", arg) if arg else ("amount", "")
            if text == name or text == f"/{name}":
                return ("amount", "")
        return None

    # ============================================================
    # 坐骑匹配
    # ============================================================
    def match_mount_trigger(self, text: str):
        if not self.enable or not self.mount_enable:
            return None
        for name in self.mount_trigger_names:
            if text == name or text == f"/{name}":
                return ("info",)
        return None

    def match_mount_list_trigger(self, text: str) -> bool:
        if not self.enable or not self.mount_enable:
            return False
        for name in self.mount_list_trigger_names:
            if text == name or text == f"/{name}":
                return True
        return False

    def match_mount_buy_trigger(self, text: str):
        if not self.enable or not self.mount_enable:
            return None
        for name in self.mount_buy_trigger_names:
            for prefix in (name + " ", f"/{name} "):
                if text.startswith(prefix):
                    arg = text[len(prefix):].strip()
                    if arg:
                        return ("buy", arg)
                    return None
        return None

    def match_mount_add_cmd(self, text: str):
        if not self.enable or not self.mount_enable:
            return None
        for name in self.cmd_mount_add_names:
            for prefix in (name + " ", f"/{name} "):
                if text.startswith(prefix):
                    arg = text[len(prefix):].strip()
                    if arg:
                        return arg
                    return ""
        return None

    def match_mount_del_cmd(self, text: str):
        if not self.enable or not self.mount_enable:
            return None
        for name in self.cmd_mount_del_names:
            for prefix in (name + " ", f"/{name} "):
                if text.startswith(prefix):
                    arg = text[len(prefix):].strip()
                    if arg:
                        return arg
                    return ""
        return None

    # ============================================================
    # 打工匹配
    # ============================================================
    def match_job_trigger(self, text: str):
        if not self.enable or not self.job_enable:
            return None
        for name in self.job_trigger_names:
            if text == name or text == f"/{name}":
                return ("list",)
            for prefix in (name + " ", f"/{name} "):
                if text.startswith(prefix):
                    arg = text[len(prefix):].strip()
                    if arg:
                        return ("work", arg)
                    return ("list",)
        return None

    def match_job_info_trigger(self, text: str) -> bool:
        if not self.enable or not self.job_enable:
            return False
        for name in self.job_info_trigger_names:
            if text == name or text == f"/{name}":
                return True
        return False

    def match_job_add_cmd(self, text: str):
        if not self.enable or not self.job_enable:
            return None
        for name in self.cmd_job_add_names:
            for prefix in (name + " ", f"/{name} "):
                if text.startswith(prefix):
                    arg = text[len(prefix):].strip()
                    if arg:
                        return arg
                    return ""
        return None

    def match_job_del_cmd(self, text: str):
        if not self.enable or not self.job_enable:
            return None
        for name in self.cmd_job_del_names:
            for prefix in (name + " ", f"/{name} "):
                if text.startswith(prefix):
                    arg = text[len(prefix):].strip()
                    if arg:
                        return arg
                    return ""
        return None


    def record_speak(self, user_id: str):
        if not user_id:
            return
        today = _today_str()
        day_map = self.speaks.setdefault(today, {})
        day_map[user_id] = int(day_map.get(user_id, 0)) + 1
        if len(self.speaks) > 30:
            old_keys = sorted(self.speaks.keys())[:-30]
            for k in old_keys:
                self.speaks.pop(k, None)

    def settle_interest_if_needed(self):
        if not self.bank_enable:
            return
        if self.bank_interest_rate <= 0:
            return
        today = _today_str()
        if self.last_interest_date == today:
            return
        now_hour = datetime.datetime.now().hour
        if now_hour < self.bank_interest_hour:
            return
        changed = False
        for uid, u in self.users.items():
            if not isinstance(u, dict):
                continue
            bank = int(u.get("bank", 0))
            if bank <= 0:
                continue
            interest = int(bank * self.bank_interest_rate)
            if interest <= 0:
                continue
            u["bank"] = bank + interest
            changed = True
        self.last_interest_date = today
        if changed:
            self._save()
            logger.info(f"[checkin] {today} 银行利息已结算")

    def do_checkin(self, event) -> str:
        group_id = get_group_id(event)
        if not self._is_group_allowed(group_id):
            return ""
        user_id = get_user_id(event)
        user_name = get_user_name(event) or f"QQ{user_id}"
        today = _today_str()
        month = _month_str()
        now = time.time()

        day_map = self.daily.setdefault(today, {})
        if user_id in day_map:
            rec = day_map[user_id]
            return (
                "======每日签到======\n"
                f"👤 {user_name}\n"
                "⚠️ 今天已经签到过了\n"
                f"🕐 签到时间：{_fmt_time(rec.get('ts', 0))}\n"
                f"🎁 今日获得：{rec.get('score', 0)} 积分\n"
                f"🏅 今日名次：第 {rec.get('rank', 0)} 名"
            )

        rank = len(day_map) + 1
        score = random.randint(1, 1000)

        u = self.users.setdefault(user_id, {
            "total_score": 0, "total_checkin": 0, "last_date": "",
            "streak": 0, "month_map": {}, "bank": 0,
        })
        u.setdefault("bank", 0)
        u["name"] = user_name

        last_date = u.get("last_date", "")
        if last_date:
            try:
                last_dt = datetime.datetime.strptime(last_date, "%Y-%m-%d").date()
                today_dt = datetime.datetime.strptime(today, "%Y-%m-%d").date()
                delta = (today_dt - last_dt).days
                if delta == 1:
                    u["streak"] = int(u.get("streak", 0)) + 1
                elif delta > 1:
                    u["streak"] = 1
            except Exception:
                u["streak"] = 1
        else:
            u["streak"] = 1

        u["last_date"] = today
        u["total_score"] = int(u.get("total_score", 0)) + score
        u["total_checkin"] = int(u.get("total_checkin", 0)) + 1

        mm = u.setdefault("month_map", {})
        mm[month] = int(mm.get(month, 0)) + 1
        if len(mm) > 6:
            old = sorted(mm.keys())[:-6]
            for k in old:
                mm.pop(k, None)
        month_count = int(mm.get(month, 0))
        speak_count = int(self.speaks.get(today, {}).get(user_id, 0))

        day_map[user_id] = {"ts": now, "rank": rank, "score": score}
        if len(self.daily) > 60:
            old = sorted(self.daily.keys())[:-60]
            for k in old:
                self.daily.pop(k, None)

        self._save()

        return "\n".join([
            "======每日签到======",
            f"👤 {user_name}",
            f"🕐 签到时间：{_fmt_time(now)}",
            f"🔥 连续签到：{u['streak']} 天",
            f"🏅 今日名次：第 {rank} 名",
            f"💬 今日发言：{speak_count} 次",
            f"📅 本月签到：{month_count} 天",
            f"📊 累计签到：{u['total_checkin']} 次",
            f"🎁 今日获得：{score} 积分",
            f"💰 拥有积分：{u['total_score']}",
        ])

    # ============================================================
    # 排行榜（★ 直接从全局昵称缓存获取）
    # ============================================================
    def build_rank_text(self) -> str:
        lines = ["======签到排行榜======"]
        if not self.users:
            lines.append("")
            lines.append("暂无签到记录")
            return "\n".join(lines)

        items = []
        for uid, u in self.users.items():
            if not isinstance(u, dict):
                continue
            items.append({
                "uid": uid,
                "score": int(u.get("total_score", 0)),
                "streak": int(u.get("streak", 0)),
                "total": int(u.get("total_checkin", 0)),
                "bank": int(u.get("bank", 0)),
            })

        def _get_name(uid):
            # 1. 全局昵称缓存（跨群共享）
            if uid in self.nickname_cache:
                return self.nickname_cache[uid]
            # 2. 签到记录里的旧昵称
            u = self.users.get(uid, {})
            name = str(u.get("name", "")).strip()
            if name and not name.startswith("QQ"):
                return name
            # 3. 兜底显示加密 QQ 号（前3位 + **** + 后2位）
            uid_str = str(uid)
            if len(uid_str) > 5:
                return f"{uid_str[:3]}****{uid_str[-2:]}"
            return uid_str

        lines.append("")
        lines.append("【积分榜 · 前十】")
        by_score = sorted(items, key=lambda x: x["score"], reverse=True)[:10]
        if not by_score:
            lines.append("  （暂无数据）")
        else:
            for i, it in enumerate(by_score, start=1):
                lines.append(f"  {i}. {_get_name(it['uid'])} — {it['score']} 分")

        lines.append("")
        lines.append("【连续签到榜 · 前十】")
        by_streak = sorted(items, key=lambda x: x["streak"], reverse=True)[:10]
        if not by_streak:
            lines.append("  （暂无数据）")
        else:
            for i, it in enumerate(by_streak, start=1):
                lines.append(f"  {i}. {_get_name(it['uid'])} — 连续 {it['streak']} 天")

        lines.append("")
        lines.append("【银行富豪榜 · 前十】")
        by_bank = sorted(items, key=lambda x: x["bank"], reverse=True)[:10]
        if not by_bank or by_bank[0]["bank"] == 0:
            lines.append("  （暂无数据）")
        else:
            for i, it in enumerate(by_bank, start=1):
                if it["bank"] <= 0:
                    continue
                lines.append(f"  {i}. {_get_name(it['uid'])} — {it['bank']} 分")

        lines.append("")
        lines.append("💡 数据来自所有群共享的签到记录")
        return "\n".join(lines)

    def build_user_info_text(self, target_uid: str, target_name: str = "") -> str:
        if not target_uid:
            return "⚠️ 未指定要查询的 QQ"
        today = _today_str()
        month = _month_str()
        u = self.users.get(target_uid)
        if not isinstance(u, dict):
            base = [
                "======签到统计======",
                f"👤 {target_name or ('QQ' + target_uid)}",
                f"💳 QQ：{target_uid}",
                "", "📊 累计签到：0 次", "💰 拥有积分：0", "🏦 银行余额：0",
                "🔥 连续签到：0 天", "📅 本月签到：0 天", "🕐 上次签到：从未签到",
                "", "📌 今日状态：❌ 今天还没签到", "🕐 今日签到时间：—", "💬 今日发言：0 次",
            ]
            return "\n".join(base)

        total_score = int(u.get("total_score", 0))
        total_checkin = int(u.get("total_checkin", 0))
        streak = int(u.get("streak", 0))
        last_date = u.get("last_date", "")
        mm = u.get("month_map", {}) or {}
        month_count = int(mm.get(month, 0))
        bank = int(u.get("bank", 0))

        today_rec = self.daily.get(today, {}).get(target_uid)
        if today_rec:
            today_state = f"✅ 已签到（第 {today_rec.get('rank', 0)} 名，+{today_rec.get('score', 0)} 分）"
            today_time = _fmt_time(today_rec.get("ts", 0))
        else:
            today_state = "❌ 今天还没签到"
            today_time = "—"

        speak_today = int(self.speaks.get(today, {}).get(target_uid, 0))

        lines = [
            "======签到统计======",
            f"👤 {target_name or ('QQ' + target_uid)}",
            f"💳 QQ：{target_uid}",
            "",
            f"📊 累计签到：{total_checkin} 次",
            f"💰 拥有积分：{total_score}",
            f"🏦 银行余额：{bank}",
            f"💎 总资产：{total_score + bank}",
            f"🔥 连续签到：{streak} 天",
            f"📅 本月签到：{month_count} 天",
            f"🕐 上次签到：{last_date or '从未签到'}",
            "",
            f"📌 今日状态：{today_state}",
            f"🕐 今日签到时间：{today_time}",
            f"💬 今日发言：{speak_today} 次",
        ]
        return "\n".join(lines)

    def do_steal(self, event, target_raw: str = "") -> str:
        group_id = get_group_id(event)
        if not self._is_group_allowed(group_id):
            return ""
        attacker_id = get_user_id(event)
        attacker_name = get_user_name(event) or f"QQ{attacker_id}"
        target_id = ""
        cleaned = str(target_raw).lstrip("@").strip()
        if cleaned.isdigit():
            target_id = cleaned
        if not target_id:
            return (
                f"⚠️ 请指定要偷的人\n"
                f"用法：「{self.steal_trigger_names[0]} @某人」"
                f"或「{self.steal_trigger_names[0]} QQ号」"
            )
        if target_id == attacker_id:
            return "⚠️ 不能偷自己的积分"

        attacker = self.users.get(attacker_id)
        if not isinstance(attacker, dict):
            return "⚠️ 你还没有签到记录，先去签到吧"
        attacker.setdefault("bank", 0)
        attacker["name"] = attacker_name

        target = self.users.get(target_id)
        if not isinstance(target, dict):
            return f"⚠️ QQ {target_id} 还没有签到记录"
        target.setdefault("bank", 0)

        target_score = int(target.get("total_score", 0))
        if target_score <= 0:
            return f"⚠️ QQ {target_id} 身上没有积分可以偷"

        amount = random.randint(self.steal_min, self.steal_max)
        amount = min(amount, target_score)

        roll = random.randint(1, 100)
        if roll <= self.steal_success_rate:
            target["total_score"] = target_score - amount
            attacker["total_score"] = int(attacker.get("total_score", 0)) + amount
            self._save()
            return "\n".join([
                "======偷积分======",
                f"🥷 {attacker_name}",
                f"🎯 目标：QQ {target_id}",
                "✅ 偷取成功！",
                f"💰 获得积分：+{amount}",
                f"💳 当前积分：{attacker['total_score']}",
            ])

        punish_roll = random.randint(1, 100)
        if punish_roll <= self.steal_fail_punish_rate:
            punish = random.randint(self.steal_punish_min, self.steal_punish_max)
            my_score = int(attacker.get("total_score", 0))
            punish = min(punish, my_score)
            if punish > 0:
                attacker["total_score"] = my_score - punish
                target["total_score"] = target_score + punish
                self._save()
                return "\n".join([
                    "======偷积分======",
                    f"🥷 {attacker_name}",
                    f"🎯 目标：QQ {target_id}",
                    "❌ 偷取失败，被发现了！",
                    f"💸 被对方拿走：-{punish}",
                    f"💳 当前积分：{attacker['total_score']}",
                ])
            else:
                self._save()
                return "\n".join([
                    "======偷积分======",
                    f"🥷 {attacker_name}",
                    f"🎯 目标：QQ {target_id}",
                    "❌ 偷取失败，被发现了！",
                    "💸 但你身上没有积分可罚",
                ])

        self._save()
        return "\n".join([
            "======偷积分======",
            f"🥷 {attacker_name}",
            f"🎯 目标：QQ {target_id}",
            "❌ 偷取失败，幸好跑掉了",
            f"💳 当前积分：{attacker.get('total_score', 0)}",
        ])

    def do_bank_info(self, event) -> str:
        group_id = get_group_id(event)
        if not self._is_group_allowed(group_id):
            return ""
        user_id = get_user_id(event)
        user_name = get_user_name(event) or f"QQ{user_id}"
        u = self.users.get(user_id)
        if not isinstance(u, dict):
            return "\n".join([
                "======我的银行======",
                f"👤 {user_name}",
                "🏦 银行余额：0",
                "💳 持有积分：0",
                "💡 先签到获得积分吧~",
            ])
        u["name"] = user_name
        bank = int(u.get("bank", 0))
        wallet = int(u.get("total_score", 0))
        rate_pct = self.bank_interest_rate * 100
        return "\n".join([
            "======我的银行======",
            f"👤 {user_name}",
            f"💳 持有积分：{wallet}",
            f"🏦 银行余额：{bank}",
            f"💰 总资产：{wallet + bank}",
            "",
            f"📈 日利率：{rate_pct:.2f}%",
            f"💡 用「{self.bank_deposit_names[0]} 数量」存钱",
            f"💡 用「{self.bank_withdraw_names[0]} 数量」取钱",
        ])

    def _parse_amount(self, arg: str, max_amount: int) -> int:
        if not arg:
            return 0
        arg = str(arg).strip().lower()
        if arg in ("all", "全部", "所有"):
            return max_amount
        if not arg.isdigit():
            return -1
        n = int(arg)
        if n <= 0:
            return -1
        return n

    def do_deposit(self, event, arg: str) -> str:
        group_id = get_group_id(event)
        if not self._is_group_allowed(group_id):
            return ""
        user_id = get_user_id(event)
        user_name = get_user_name(event) or f"QQ{user_id}"
        u = self.users.setdefault(user_id, {
            "total_score": 0, "total_checkin": 0, "last_date": "",
            "streak": 0, "month_map": {}, "bank": 0,
        })
        u.setdefault("bank", 0)
        u["name"] = user_name
        wallet = int(u.get("total_score", 0))
        amount = self._parse_amount(arg, wallet)
        if amount == -1:
            return (
                f"⚠️ 数量无效\n"
                f"用法：「{self.bank_deposit_names[0]} 100」"
                f"或「{self.bank_deposit_names[0]} all」"
            )
        if amount == 0:
            return (
                f"⚠️ 请指定存款数量\n"
                f"用法：「{self.bank_deposit_names[0]} 100」"
                f"或「{self.bank_deposit_names[0]} all」"
            )
        if amount > wallet:
            return f"⚠️ 持有积分不足（当前 {wallet}）"
        u["total_score"] = wallet - amount
        u["bank"] = int(u.get("bank", 0)) + amount
        self._save()
        return "\n".join([
            "======存入银行======",
            f"👤 {user_name}",
            f"💰 存入：+{amount}",
            f"🏦 银行余额：{u['bank']}",
            f"💳 持有积分：{u['total_score']}",
        ])

    def do_withdraw(self, event, arg: str) -> str:
        group_id = get_group_id(event)
        if not self._is_group_allowed(group_id):
            return ""
        user_id = get_user_id(event)
        user_name = get_user_name(event) or f"QQ{user_id}"
        u = self.users.get(user_id)
        if not isinstance(u, dict):
            return "⚠️ 你还没有签到记录"
        u["name"] = user_name
        bank = int(u.get("bank", 0))
        amount = self._parse_amount(arg, bank)
        if amount == -1:
            return (
                f"⚠️ 数量无效\n"
                f"用法：「{self.bank_withdraw_names[0]} 100」"
                f"或「{self.bank_withdraw_names[0]} all」"
            )
        if amount == 0:
            return (
                f"⚠️ 请指定取款数量\n"
                f"用法：「{self.bank_withdraw_names[0]} 100」"
                f"或「{self.bank_withdraw_names[0]} all」"
            )
        if amount > bank:
            return f"⚠️ 银行余额不足（当前 {bank}）"
        u["bank"] = bank - amount
        u["total_score"] = int(u.get("total_score", 0)) + amount
        self._save()
        return "\n".join([
            "======从银行取出======",
            f"👤 {user_name}",
            f"💰 取出：+{amount}",
            f"🏦 银行余额：{u['bank']}",
            f"💳 持有积分：{u['total_score']}",
        ])

    # ============================================================
    # 坐骑系统
    # ============================================================
    def do_mount_info(self, event) -> str:
        group_id = get_group_id(event)
        if not self._is_group_allowed(group_id):
            return ""
        user_id = get_user_id(event)
        user_name = get_user_name(event) or f"QQ{user_id}"
        u = self.users.get(user_id)
        if not isinstance(u, dict):
            return "⚠️ 你还没有签到记录，先去签到吧"
        u.setdefault("mounts", [])
        u.setdefault("current_mount", "")

        mounts = u.get("mounts", []) or []
        current = u.get("current_mount", "")

        lines = [
            "======我的坐骑======",
            f"👤 {user_name}",
            f"💰 拥有积分：{int(u.get('total_score', 0))}",
            "",
        ]
        if not mounts:
            lines.append("🐴 坐骑：暂无")
        else:
            lines.append(f"🐴 已拥有坐骑（{len(mounts)} 个）")
            for i, m in enumerate(mounts, start=1):
                tag = "  ⭐当前骑乘" if m == current else ""
                lines.append(f"  {i}. {m}{tag}")
        lines.append("")
        lines.append(f"💡 发送「{self.mount_list_trigger_names[0]}」查看坐骑商店")
        return "\n".join(lines)

    def do_mount_list(self) -> str:
        lines = ["======坐骑商店======"]
        if not self.mount_list:
            lines.append("")
            lines.append("暂无坐骑，请联系管理员在后台添加")
            return "\n".join(lines)
        lines.append("")
        for i, m in enumerate(self.mount_list, start=1):
            lines.append(f"{i}. {m['name']} —— {m['price']} 积分")
            if m.get("desc"):
                lines.append(f"    {m['desc']}")
        lines.append("")
        lines.append(f"💡 用「{self.mount_buy_trigger_names[0]} 坐骑名」购买")
        return "\n".join(lines)

    def do_mount_buy(self, event, mount_name: str) -> str:
        group_id = get_group_id(event)
        if not self._is_group_allowed(group_id):
            return ""
        user_id = get_user_id(event)
        user_name = get_user_name(event) or f"QQ{user_id}"
        mount_name = str(mount_name).strip()
        if not mount_name:
            return f"⚠️ 请指定坐骑名称\n用法：「{self.mount_buy_trigger_names[0]} 坐骑名」"

        target = None
        for m in self.mount_list:
            if m["name"] == mount_name:
                target = m
                break
        if target is None:
            return (
                f"⚠️ 坐骑「{mount_name}」不存在\n"
                f"💡 用「{self.mount_list_trigger_names[0]}」查看可购买坐骑"
            )

        u = self.users.setdefault(user_id, {
            "total_score": 0, "total_checkin": 0, "last_date": "",
            "streak": 0, "month_map": {}, "bank": 0,
        })
        u.setdefault("bank", 0)
        u.setdefault("mounts", [])
        u.setdefault("current_mount", "")

        if mount_name in u["mounts"]:
            return f"⚠️ 你已经拥有坐骑「{mount_name}」了"

        price = int(target["price"])
        wallet = int(u.get("total_score", 0))
        if wallet < price:
            return f"⚠️ 积分不足（当前 {wallet}，需要 {price}）"

        u["total_score"] = wallet - price
        u["mounts"].append(mount_name)
        if not u["current_mount"]:
            u["current_mount"] = mount_name
        self._save()

        return "\n".join([
            "======购买坐骑======",
            f"👤 {user_name}",
            f"🐴 坐骑：{mount_name}",
            f"💸 花费：-{price} 积分",
            f"💰 剩余积分：{u['total_score']}",
            "",
            "✅ 购买成功，已自动骑乘",
        ])

    def do_mount_add(self, arg: str) -> str:
        arg = str(arg or "").strip()
        if not arg:
            return (
                "⚠️ 参数不足\n"
                f"用法：「{self.cmd_mount_add_names[0]} 坐骑名 | 价格 | 描述」\n"
                "示例：「添加坐骑 修仙者专属 | 1000 | 脚踏飞剑，日行千里」"
            )
        parts = [x.strip() for x in arg.split("|")]
        if len(parts) < 1 or not parts[0]:
            return "⚠️ 坐骑名不能为空"

        name = parts[0]
        try:
            price = int(parts[1]) if len(parts) > 1 and parts[1] else 1000
        except Exception:
            return "⚠️ 价格必须是数字"
        if price < 0:
            price = 0

        desc = parts[2] if len(parts) > 2 else ""

        for m in self.mount_list:
            if m["name"] == name:
                return f"⚠️ 坐骑「{name}」已存在"

        self.mount_list.append({
            "name": name,
            "price": price,
            "desc": desc,
        })
        return (
            f"✅ 已添加坐骑：{name}\n"
            f"💰 价格：{price} 积分\n"
            f"📝 描述：{desc or '无'}\n"
            f"💡 请在 WebUI 点击「保存全部」以持久化"
        )

    def do_mount_del(self, arg: str) -> str:
        arg = str(arg or "").strip()
        if not arg:
            return (
                "⚠️ 参数不足\n"
                f"用法：「{self.cmd_mount_del_names[0]} 坐骑名或序号」\n"
                f"💡 可先发「{self.mount_list_trigger_names[0]}」查看序号"
            )

        idx = -1
        if arg.isdigit():
            n = int(arg) - 1
            if 0 <= n < len(self.mount_list):
                idx = n
        if idx == -1:
            for i, m in enumerate(self.mount_list):
                if m["name"] == arg:
                    idx = i
                    break
        if idx == -1:
            return f"⚠️ 未找到坐骑「{arg}」"

        removed = self.mount_list.pop(idx)
        return (
            f"✅ 已删除坐骑：{removed['name']}\n"
            f"💡 请在 WebUI 点击「保存全部」以持久化"
        )

    # ============================================================
    # 打工系统
    # ============================================================
    def do_job_list(self) -> str:
        lines = ["======打工列表======"]
        if not self.job_list:
            lines.append("")
            lines.append("暂无工种，请联系管理员添加")
            lines.append("")
            lines.append(
                f"💡 管理员可用「{self.cmd_job_add_names[0]} 工种名 | 冷却小时 | 最少收益 | 最多收益」添加"
            )
            return "\n".join(lines)
        lines.append("")
        for i, j in enumerate(self.job_list, start=1):
            lines.append(
                f"{i}. {j['name']} —— 冷却 {j['duration_hours']} 小时 "
                f"（{j['reward_min']}~{j['reward_max']} 积分）"
            )
        lines.append("")
        lines.append(f"💡 用「{self.job_trigger_names[0]} 工种」开始打工")
        return "\n".join(lines)

    def do_job_work(self, event, job_name: str = "") -> str:
        group_id = get_group_id(event)
        if not self._is_group_allowed(group_id):
            return ""
        user_id = get_user_id(event)
        user_name = get_user_name(event) or f"QQ{user_id}"

        if not self.job_list:
            return "⚠️ 暂无工种，请联系管理员添加"

        job_name = str(job_name).strip()
        if not job_name:
            return self.do_job_list()

        target = None
        for j in self.job_list:
            if j["name"] == job_name:
                target = j
                break
        if target is None:
            return (
                f"⚠️ 工种「{job_name}」不存在\n"
                f"💡 用「{self.job_info_trigger_names[0]}」查看可用工种"
            )

        u = self.users.setdefault(user_id, {
            "total_score": 0, "total_checkin": 0, "last_date": "",
            "streak": 0, "month_map": {}, "bank": 0,
        })
        u.setdefault("bank", 0)
        u.setdefault("job_cd", {})

        cd = u["job_cd"]
        now = time.time()
        last_ts = float(cd.get(job_name, 0) or 0)
        need_sec = int(target["duration_hours"]) * 3600
        elapsed = now - last_ts
        if last_ts > 0 and elapsed < need_sec:
            remain = int(need_sec - elapsed)
            h, rem = divmod(remain, 3600)
            m, s = divmod(rem, 60)
            return (
                f"⚠️ 你刚刚已经做过「{job_name}」了\n"
                f"⏰ 还需等待：{h}小时{m}分{s}秒\n"
                f"💡 冷却完成后可以再做"
            )

        reward = random.randint(target["reward_min"], target["reward_max"])
        u["total_score"] = int(u.get("total_score", 0)) + reward
        cd[job_name] = now
        self._save()

        return "\n".join([
            "======打工结果======",
            f"👤 {user_name}",
            f"🔨 工种：{job_name}",
            f"⏱️ 冷却：{target['duration_hours']} 小时",
            f"💵 获得：+{reward} 积分",
            f"💰 当前积分：{u['total_score']}",
            "",
            f"💡 下次可再做「{job_name}」需等 {target['duration_hours']} 小时",
        ])

    # ============================================================
    # 管理员工种管理
    # ============================================================
    def do_job_add(self, arg: str) -> str:
        arg = str(arg or "").strip()
        if not arg:
            return (
                "⚠️ 参数不足\n"
                f"用法：「{self.cmd_job_add_names[0]} 工种名 | 冷却小时 | 最少收益 | 最多收益」\n"
                "示例：「添加工种 搬砖 | 5 | 100 | 500」"
            )
        parts = [x.strip() for x in arg.split("|")]
        if len(parts) < 2:
            return (
                "⚠️ 参数不足\n"
                f"用法：「{self.cmd_job_add_names[0]} 工种名 | 冷却小时 | 最少收益 | 最多收益」\n"
                "示例：「添加工种 搬砖 | 5 | 100 | 500」"
            )
        name = parts[0].strip()
        if not name:
            return "⚠️ 工种名不能为空"
        try:
            dur = int(parts[1]) if len(parts) >= 2 and parts[1] else 1
        except Exception:
            return "⚠️ 冷却小时必须是数字"
        try:
            rmin = int(parts[2]) if len(parts) >= 3 and parts[2] else 10
        except Exception:
            return "⚠️ 最少收益必须是数字"
        try:
            rmax = int(parts[3]) if len(parts) >= 4 and parts[3] else 100
        except Exception:
            return "⚠️ 最多收益必须是数字"
        if dur < 1:
            return "⚠️ 冷却至少 1 小时"
        if rmin < 0:
            rmin = 0
        if rmax < rmin:
            rmax = rmin

        for j in self.job_list:
            if j["name"] == name:
                return f"⚠️ 工种「{name}」已存在"

        self.job_list.append({
            "name": name,
            "duration_hours": dur,
            "reward_min": rmin,
            "reward_max": rmax,
        })
        return (
            f"✅ 已添加工种：{name}\n"
            f"⏱️ 冷却：{dur} 小时\n"
            f"💰 收益：{rmin}~{rmax} 积分\n"
            f"💡 请在 WebUI 点击「保存全部」以持久化"
        )

    def do_job_del(self, arg: str) -> str:
        arg = str(arg or "").strip()
        if not arg:
            return (
                "⚠️ 参数不足\n"
                f"用法：「{self.cmd_job_del_names[0]} 工种名或序号」\n"
                f"💡 可先发「{self.job_info_trigger_names[0]}」查看序号"
            )

        idx = -1
        if arg.isdigit():
            n = int(arg) - 1
            if 0 <= n < len(self.job_list):
                idx = n
        if idx == -1:
            for i, j in enumerate(self.job_list):
                if j["name"] == arg:
                    idx = i
                    break
        if idx == -1:
            return f"⚠️ 未找到工种「{arg}」"

        removed = self.job_list.pop(idx)
        return (
            f"✅ 已删除工种：{removed['name']}\n"
            f"💡 请在 WebUI 点击「保存全部」以持久化"
        )