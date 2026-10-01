import os
import json
import time
import uuid
import random
import hashlib
import tempfile
import datetime
import aiohttp

from astrbot.api import logger


def _today_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d")


def _parse_names(raw: str) -> list:
    if not raw:
        return []
    text = str(raw)
    return [x.strip() for x in text.split(",") if x.strip()]


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


def get_avatar_url(qq: str) -> str:
    """QQ 头像 URL（640x640）"""
    if not qq:
        return ""
    return f"https://q1.qlogo.cn/g?b=qq&nk={qq}&s=640"


async def download_avatar(qq: str, timeout: int = 10) -> str:
    """下载 QQ 头像到临时文件，返回本地路径；失败返回空串"""
    if not qq:
        return ""
    url = get_avatar_url(qq)
    try:
        t = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=t) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.warning(f"[husband] 头像 HTTP {resp.status}")
                    return ""
                img_bytes = await resp.read()
        if not img_bytes:
            return ""

        tmp_dir = os.path.join(tempfile.gettempdir(), "astrbot_meme")
        os.makedirs(tmp_dir, exist_ok=True)
        fname = f"avatar_{qq}_{uuid.uuid4().hex[:6]}.jpg"
        fpath = os.path.join(tmp_dir, fname)
        with open(fpath, "wb") as f:
            f.write(img_bytes)
        return fpath
    except Exception:
        logger.exception("[husband] 下载头像失败")
        return ""


class HusbandModule:
    """
    今日老公模块：每个人每天各抽一次，结果互不相同。
    """

    def __init__(self, plugin_dir: str, data_path: str):
        self.plugin_dir = plugin_dir
        self.data_path = data_path
        self.trigger_names = ["今日老公", "老公"]
        self.enable = True
        self.group_mode = "off"
        self.group_whitelist = []
        self.group_blacklist = []
        self.user_records = {}
        self._load_records()

    def reload(self, cfg: dict):
        self.enable = bool(cfg.get("husband_enable", True))
        raw = str(cfg.get("husband_trigger_names", "今日老公,老公") or "").strip()
        names = _parse_names(raw)
        self.trigger_names = names if names else ["今日老公"]

        self.group_mode = str(cfg.get("husband_group_mode", "off") or "off").strip().lower()
        if self.group_mode not in ("off", "whitelist", "blacklist"):
            self.group_mode = "off"
        self.group_whitelist = _parse_lines(cfg.get("husband_group_whitelist", ""))
        self.group_blacklist = _parse_lines(cfg.get("husband_group_blacklist", ""))

    def _load_records(self):
        if not os.path.exists(self.data_path):
            self.user_records = {}
            return
        try:
            with open(self.data_path, "r", encoding="utf-8-sig") as f:
                self.user_records = json.load(f) or {}
        except Exception:
            self.user_records = {}

    def _save_records(self):
        try:
            tmp = self.data_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.user_records, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.data_path)
        except Exception:
            pass

    def _is_group_allowed(self, group_id: str) -> bool:
        if not group_id:
            return True
        if self.group_mode == "whitelist":
            return group_id in self.group_whitelist
        if self.group_mode == "blacklist":
            return group_id not in self.group_blacklist
        return True

    def match_trigger(self, text: str) -> bool:
        if not self.enable:
            return False
        for name in self.trigger_names:
            if not name:
                continue
            if text == name or text == f"/{name}":
                return True
        return False

    async def _get_group_members(self, event):
        group_id = get_group_id(event)
        if not group_id:
            return None

        bot = getattr(event, "bot", None)
        if bot is None:
            for attr in ("api", "client", "onebot"):
                alt = getattr(event, attr, None)
                if alt is not None:
                    bot = alt
                    break
        if bot is None:
            return None

        if hasattr(bot, "get_group_member_list"):
            try:
                members = await bot.get_group_member_list(group_id=int(group_id))
                if members:
                    return members
            except Exception:
                pass

        if hasattr(bot, "call_action"):
            try:
                members = await bot.call_action("get_group_member_list", group_id=int(group_id))
                if members:
                    return members
            except Exception:
                pass

        api = getattr(bot, "api", None)
        if api is not None and hasattr(api, "call_action"):
            try:
                members = await api.call_action("get_group_member_list", group_id=int(group_id))
                if members:
                    return members
            except Exception:
                pass

        return None

    async def get_today_text(self, event) -> str:
        """保留原有文本输出（备用）"""
        group_id = get_group_id(event)
        if not self._is_group_allowed(group_id):
            return ""

        user_id = get_user_id(event)
        today = _today_str()
        key = f"{today}|{group_id}|{user_id}"

        rec = self.user_records.get(key)
        if rec:
            return self._format(rec)

        members = await self._get_group_members(event)
        if not members:
            return "⚠️ 获取群成员失败，请稍后再试"

        seed_str = f"husband-{group_id}-{user_id}-{today}"
        rnd = random.Random(seed_str)
        chosen = rnd.choice(members)

        qq = str(chosen.get("user_id", ""))
        name = chosen.get("card") or chosen.get("nickname") or f"QQ{qq}"

        rec = {"qq": qq, "name": name, "ts": int(time.time())}
        self.user_records[key] = rec
        self._save_records()
        return self._format(rec)

    async def get_today_result(self, event):
        """
        新接口：返回 (文本, 头像本地路径或 None)
        供 main.py 调用，可图文一起发。
        """
        group_id = get_group_id(event)
        if not self._is_group_allowed(group_id):
            return "", None

        user_id = get_user_id(event)
        today = _today_str()
        key = f"{today}|{group_id}|{user_id}"

        rec = self.user_records.get(key)
        if not rec:
            members = await self._get_group_members(event)
            if not members:
                return "⚠️ 获取群成员失败，请稍后再试", None

            seed_str = f"husband-{group_id}-{user_id}-{today}"
            rnd = random.Random(seed_str)
            chosen = rnd.choice(members)

            qq = str(chosen.get("user_id", ""))
            name = chosen.get("card") or chosen.get("nickname") or f"QQ{qq}"

            rec = {"qq": qq, "name": name, "ts": int(time.time())}
            self.user_records[key] = rec
            self._save_records()

        qq = rec.get("qq", "")
        name = rec.get("name", "")

        text = "\n".join([
            "======今日老公======",
            f"👨 {name}",
            f"💳 QQ：{qq}",
            "",
            "💡 每天一次，明天再刷新"
        ])

        avatar_path = await download_avatar(qq) if qq else ""
        return text, avatar_path or None

    def _format(self, rec: dict) -> str:
        return "\n".join([
            "======今日老公======",
            f"👨 {rec.get('name', '')}",
            f"💳 QQ：{rec.get('qq', '')}",
            "",
            "💡 每天一次，明天再刷新"
        ])