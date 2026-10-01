import os
import re
import json

PLUGIN_ID = "astrbot_plugin_meme_api_manager"
PLUGIN_CONFIG_FILENAME = f"{PLUGIN_ID}_config.json"
PLUGIN_FORTUNE_DATA_FILENAME = f"{PLUGIN_ID}_fortune.json"
PLUGIN_HUSBAND_DATA_FILENAME = f"{PLUGIN_ID}_husband.json"
PLUGIN_LUCK_DATA_FILENAME = f"{PLUGIN_ID}_luck.json"
PLUGIN_GREETING_DATA_FILENAME = f"{PLUGIN_ID}_greeting.json"
PLUGIN_MINECRAFT_DATA_FILENAME = f"{PLUGIN_ID}_minecraft.json"
PLUGIN_CHECKIN_DATA_FILENAME = f"{PLUGIN_ID}_checkin.json"
PLUGIN_HOURLY_CHIME_DATA_FILENAME = f"{PLUGIN_ID}_hourly_chime.json"
PLUGIN_STATUS_PUSH_DATA_FILENAME = f"{PLUGIN_ID}_status_push.json"
PLUGIN_DAILY_NEWS_DATA_FILENAME = f"{PLUGIN_ID}_daily_news.json"
PLUGIN_NICKNAME_DATA_FILENAME = f"{PLUGIN_ID}_nickname.json"


def plugin_dir() -> str:
    """当前插件根目录"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _find_astrbot_root() -> str:
    """定位 AstrBot 根目录（仅用于确定 data/ 的父级，不用于直接写数据）"""
    try:
        import astrbot
        pkg_dir = os.path.dirname(os.path.abspath(astrbot.__file__))
        root = os.path.dirname(pkg_dir)
        if os.path.isdir(os.path.join(root, "data")):
            return root
        root2 = os.path.dirname(root)
        if os.path.isdir(os.path.join(root2, "data")):
            return root2
    except Exception:
        pass
    cur = plugin_dir()
    for _ in range(6):
        # 优先认 data/plugin_data（新规范），其次兼容老的 data/config
        if (os.path.isdir(os.path.join(cur, "data", "plugin_data"))
                or os.path.isdir(os.path.join(cur, "data", "config"))):
            return cur
        cur = os.path.dirname(cur)
    return os.getcwd()


# 旧版本的数据目录（data/config），仅用于一次性迁移
def _legacy_cfg_dir() -> str:
    return os.path.join(_find_astrbot_root(), "data", "config")


# ★ 规范要求：插件持久化数据统一放在 data/plugin_data/<插件名>/
def _plugin_data_dir() -> str:
    """
    返回本插件的数据目录，并确保存在。
    优先使用 AstrBot 提供的接口，取不到时按规范路径自行推导。
    """
    candidates = []

    # ① AstrBot 4.x 提供的接口
    try:
        from astrbot.core.utils.astrbot_path import get_astrbot_data_path  # type: ignore
        p = get_astrbot_data_path()
        if p:
            candidates.append(os.path.join(str(p), "plugin_data", PLUGIN_ID))
    except Exception:
        pass
    try:
        from astrbot.core.utils.astrbot_path import get_astrbot_plugin_data_path  # type: ignore
        p = get_astrbot_plugin_data_path()
        if p:
            candidates.append(str(p))
    except Exception:
        pass

    # ② 按规范路径推导
    candidates.append(
        os.path.join(_find_astrbot_root(), "data", "plugin_data", PLUGIN_ID)
    )

    for path in candidates:
        try:
            os.makedirs(path, exist_ok=True)
            return path
        except Exception:
            continue

    # ③ 兜底：插件目录下的 data/（极端情况下也不能丢数据）
    fallback = os.path.join(plugin_dir(), "data")
    os.makedirs(fallback, exist_ok=True)
    return fallback


# 迁移只跑一次的标记
_MIGRATED = [False]


def _migrate_legacy_data():
    """
    把旧位置（data/config 与 data/backups）里的本插件数据迁移到新目录。
    只在目标文件不存在时搬运，绝不覆盖已有数据；搬运成功后保留原文件不删除。
    """
    if _MIGRATED[0]:
        return
    _MIGRATED[0] = True
    try:
        target = _plugin_data_dir()
        legacy = _legacy_cfg_dir()
        if not os.path.isdir(legacy):
            return
        moved = 0
        for name in (
            PLUGIN_CONFIG_FILENAME,
            PLUGIN_FORTUNE_DATA_FILENAME,
            PLUGIN_HUSBAND_DATA_FILENAME,
            PLUGIN_LUCK_DATA_FILENAME,
            PLUGIN_GREETING_DATA_FILENAME,
            PLUGIN_MINECRAFT_DATA_FILENAME,
            PLUGIN_CHECKIN_DATA_FILENAME,
            PLUGIN_HOURLY_CHIME_DATA_FILENAME,
            PLUGIN_STATUS_PUSH_DATA_FILENAME,
            PLUGIN_DAILY_NEWS_DATA_FILENAME,
            PLUGIN_NICKNAME_DATA_FILENAME,
        ):
            src = os.path.join(legacy, name)
            dst = os.path.join(target, name)
            if not os.path.isfile(src) or os.path.exists(dst):
                continue
            try:
                with open(src, "rb") as f:
                    blob = f.read()
                tmp = dst + ".migrate.tmp"
                with open(tmp, "wb") as f:
                    f.write(blob)
                os.replace(tmp, dst)
                moved += 1
            except Exception:
                continue
        if moved:
            try:
                from astrbot.api import logger
                logger.info(
                    f"[{PLUGIN_ID}] 已把 {moved} 个数据文件迁移到 plugin_data 目录：{target}"
                )
            except Exception:
                pass
    except Exception:
        pass


def _cfg_dir() -> str:
    """本插件数据目录（data/plugin_data/<插件名>/）"""
    _migrate_legacy_data()
    return _plugin_data_dir()


def config_path() -> str:
    return os.path.join(_cfg_dir(), PLUGIN_CONFIG_FILENAME)


def fortune_data_path() -> str:
    return os.path.join(_cfg_dir(), PLUGIN_FORTUNE_DATA_FILENAME)


def husband_data_path() -> str:
    return os.path.join(_cfg_dir(), PLUGIN_HUSBAND_DATA_FILENAME)


def luck_data_path() -> str:
    return os.path.join(_cfg_dir(), PLUGIN_LUCK_DATA_FILENAME)


def greeting_data_path() -> str:
    return os.path.join(_cfg_dir(), PLUGIN_GREETING_DATA_FILENAME)


def minecraft_data_path() -> str:
    return os.path.join(_cfg_dir(), PLUGIN_MINECRAFT_DATA_FILENAME)


def checkin_data_path() -> str:
    return os.path.join(_cfg_dir(), PLUGIN_CHECKIN_DATA_FILENAME)


def hourly_chime_data_path() -> str:
    return os.path.join(_cfg_dir(), PLUGIN_HOURLY_CHIME_DATA_FILENAME)


def status_push_data_path() -> str:
    return os.path.join(_cfg_dir(), PLUGIN_STATUS_PUSH_DATA_FILENAME)


def daily_news_data_path() -> str:
    return os.path.join(_cfg_dir(), PLUGIN_DAILY_NEWS_DATA_FILENAME)


def nickname_data_path() -> str:
    return os.path.join(_cfg_dir(), PLUGIN_NICKNAME_DATA_FILENAME)


def read_plugin_version(star_obj=None) -> str:
    """读取插件版本号（优先 metadata → star 对象属性 → yaml）"""
    if star_obj is not None:
        for attr in ("metadata", "star_meta", "meta", "plugin_metadata"):
            try:
                meta = getattr(star_obj, attr, None)
                if meta is None:
                    continue
                v = (
                    getattr(meta, "version", None)
                    or getattr(meta, "plugin_version", None)
                    or getattr(meta, "ver", None)
                )
                if v:
                    return str(v).strip()
                if isinstance(meta, dict):
                    v = meta.get("version") or meta.get("plugin_version")
                    if v:
                        return str(v).strip()
            except Exception:
                pass

    try:
        import yaml
        path = os.path.join(plugin_dir(), "metadata.yaml")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8-sig") as f:
                data = yaml.safe_load(f) or {}
            v = data.get("version")
            if v:
                return str(v).strip()
    except Exception:
        pass

    return "未知"


def read_disk_config() -> dict:
    """读取插件磁盘配置，失败返回 {}"""
    path = config_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


def parse_gid_list(raw) -> list:
    """
    解析后台填写的群号列表，返回去重后的字符串列表（保持填写顺序）。
    支持换行 / 英文逗号 / 中文逗号 / 空格 / 顿号分隔，忽略非数字内容。
    """
    if raw is None:
        return []
    text = str(raw)
    if not text.strip():
        return []
    out, seen = [], set()
    for part in re.split(r"[\s,，、;；]+", text):
        gid = part.strip()
        if not gid or not gid.isdigit():
            continue
        if gid in seen:
            continue
        seen.add(gid)
        out.append(gid)
    return out


def write_disk_config(data: dict) -> bool:
    """原子写入插件磁盘配置"""
    path = config_path()
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except Exception:
        return False