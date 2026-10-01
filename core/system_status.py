import os
import sys
import json
import time
import platform
import datetime


try:
    from .path_utils import read_disk_config as _read_disk_config_util
    _HAS_PATH_UTILS = True
except Exception:
    _HAS_PATH_UTILS = False

try:
    import psutil
    _HAS_PSUTIL = True
except Exception:
    _HAS_PSUTIL = False


GLOBAL_STATS = {"recv": 0, "send": 0}

# 由 main.py 注入的插件版本
PLUGIN_VERSION = ""


def set_plugin_version(version: str):
    global PLUGIN_VERSION
    PLUGIN_VERSION = str(version or "").strip()


# ============================================================
# 路径工具
# ============================================================
_PLUGIN_ID = "astrbot_plugin_meme_api_manager"
_CONFIG_FILENAME = f"{_PLUGIN_ID}_config.json"


def _find_astrbot_root() -> str:
    try:
        import astrbot
        pkg_dir = os.path.dirname(os.path.abspath(astrbot.__file__))
        root = os.path.dirname(pkg_dir)
        if os.path.isdir(os.path.join(root, "data", "config")):
            return root
        root2 = os.path.dirname(root)
        if os.path.isdir(os.path.join(root2, "data", "config")):
            return root2
    except Exception:
        pass
    cur = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        candidate = os.path.join(cur, "data", "config")
        if os.path.isdir(candidate):
            return cur
        cur = os.path.dirname(cur)
    return os.getcwd()


def _config_path() -> str:
    root = _find_astrbot_root()
    cfg_dir = os.path.join(root, "data", "config")
    os.makedirs(cfg_dir, exist_ok=True)
    return os.path.join(cfg_dir, _CONFIG_FILENAME)


def _read_plugin_cfg() -> dict:
    if _HAS_PATH_UTILS:
        try:
            data = _read_disk_config_util()
            return data if isinstance(data, dict) else {}
        except Exception:
            pass
    try:
        path = _config_path()
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _cfg_str(cfg: dict, key: str, default: str = "") -> str:
    v = cfg.get(key, default)
    if v is None:
        return default
    return str(v)


# ============================================================
# 格式化工具
# ============================================================
def _cfg_bool(cfg: dict, key: str, default: bool = True) -> bool:
    v = cfg.get(key, default)
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on", "是", "开启")


def _cfg_text(cfg: dict, key: str, default: str = "") -> str:
    v = cfg.get(key, default)
    if v is None:
        return default
    return str(v)


def human_bytes(n: float) -> str:
    try:
        n = float(n)
    except Exception:
        return str(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024.0:
            return f"{n:.2f}{unit}"
        n /= 1024.0
    return f"{n:.2f}PB"


def human_seconds(sec: float) -> str:
    try:
        sec = int(sec)
    except Exception:
        return str(sec)
    d, sec = divmod(sec, 86400)
    h, sec = divmod(sec, 3600)
    m, s = divmod(sec, 60)
    parts = []
    if d:
        parts.append(f"{d}天")
    if h:
        parts.append(f"{h}时")
    if m:
        parts.append(f"{m}分")
    parts.append(f"{s}秒")
    return "".join(parts)


def get_astrbot_version() -> str:
    try:
        import astrbot
        v = getattr(astrbot, "__version__", None)
        if v:
            return str(v)
    except Exception:
        pass
    try:
        from astrbot.core.config import VERSION
        if VERSION:
            return str(VERSION)
    except Exception:
        pass
    return "未知"


def get_os_version() -> str:
    try:
        system = platform.system()
        release = platform.release()
        version = platform.version()
        if system == "Windows":
            return f"Windows {release} (Build {version})"
        if system == "Linux":
            try:
                with open("/etc/os-release", "r", encoding="utf-8") as f:
                    data = {}
                    for line in f:
                        line = line.strip()
                        if "=" in line:
                            k, v = line.split("=", 1)
                            data[k] = v.strip('"')
                pretty = data.get("PRETTY_NAME") or data.get("NAME") or "Linux"
                return f"{pretty} (内核 {release})"
            except Exception:
                return f"Linux {release}"
        if system == "Darwin":
            return f"macOS {release}"
        return f"{system} {release}"
    except Exception:
        return "未知"


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


def get_bot_id(event) -> str:
    try:
        bot_id = event.get_self_id() or ""
        if bot_id:
            return str(bot_id)
    except Exception:
        pass
    return "未知"


def get_sender_name(event) -> str:
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


def get_pc_uptime_seconds() -> float:
    if _HAS_PSUTIL:
        try:
            return time.time() - psutil.boot_time()
        except Exception:
            return 0.0
    return 0.0


def get_cpu_usage_str() -> str:
    """
    CPU 占用：优先用 psutil，第一次调用 interval=None 会返回自进程启动以来的均值，
    因此这里做一次极短采样以获得较准的瞬时值。
    """
    if not _HAS_PSUTIL:
        return "⚠️ 未安装 psutil"
    try:
        try:
            cores = psutil.cpu_count(logical=True) or 0
        except Exception:
            cores = 0
        percent = None
        try:
            percent = psutil.cpu_percent(interval=0.15)
        except Exception:
            try:
                percent = psutil.cpu_percent(interval=None)
            except Exception:
                percent = None
        if percent is None:
            return "获取失败"
        try:
            percent = float(percent)
        except Exception:
            return "获取失败"
        if percent < 0:
            return "获取失败"
        # psutil 在部分平台会给出 >100 的值（多核累加），这里归一化到 0-100
        if percent > 100.0:
            percent = min(100.0, percent / max(1, cores or 1))
        text = f"{percent:.1f}%"
        if cores:
            text += f"（{cores}核心）"
        return text
    except Exception:
        return "获取失败"


def get_memory_usage_str() -> str:
    if not _HAS_PSUTIL:
        return "⚠️ 未安装 psutil"
    try:
        vm = psutil.virtual_memory()
        return f"{vm.percent}% 已用 {human_bytes(vm.used)} / 共 {human_bytes(vm.total)}"
    except Exception:
        return "获取失败"


def get_disk_usage_str() -> str:
    if not _HAS_PSUTIL:
        return "⚠️ 未安装 psutil"
    try:
        parts = psutil.disk_partitions(all=False)
    except Exception:
        return "获取失败"
    lines = []
    shown = 0
    for p in parts:
        if shown >= 4:
            break
        try:
            usage = psutil.disk_usage(p.mountpoint)
        except Exception:
            continue
        lines.append(
            f"{p.device}：{usage.percent}% 已用 {human_bytes(usage.used)} / 共 {human_bytes(usage.total)}"
        )
        shown += 1
    return "\n".join(lines) if lines else "获取失败"


# ============================================================
# 主入口：按配置输出指定项目
# ============================================================
def collect_runtime_status(event=None, group_id: str = None, cfg: dict = None) -> str:
    """
    生成机器人运行状态文本。

    event    : 触发事件；定时推送时可为 None（此时用 group_id 直接指定群号）
    group_id : 无事件场景（定时推送 / 页面预览）下手动指定的群号
    cfg      : 插件配置；传入则按 cmd_status_* 开关裁剪输出
    """
    cfg = cfg if isinstance(cfg, dict) else _read_plugin_cfg()

    title = _cfg_text(cfg, "cmd_status_title", "======机器人运行状态======").strip()
    lines = [title] if title else ["======机器人运行状态======"]

    show_basic = _cfg_bool(cfg, "cmd_status_show_basic", True)
    show_uptime = _cfg_bool(cfg, "cmd_status_show_uptime", True)
    show_cpu = _cfg_bool(cfg, "cmd_status_show_cpu", True)
    show_mem = _cfg_bool(cfg, "cmd_status_show_mem", True)
    show_disk = _cfg_bool(cfg, "cmd_status_show_disk", True)

    # ---- 基础信息 ----
    if show_basic:
        if group_id:
            gid = str(group_id).strip()
        else:
            gid = get_group_id(event) if event is not None else ""
        lines.append(f"当前群群号：{gid or '未知'}")

        bot_id = get_bot_id(event) if event is not None else "未知"
        lines.append(f"机器人QQ：{bot_id}")

        lines.append(f"插件版本：{PLUGIN_VERSION or '未知'}")
        lines.append(f"AstrBot版本：{get_astrbot_version()}")
        lines.append(f"系统版本：{get_os_version()}")

    # ---- 开机时长 ----
    if show_uptime:
        uptime = get_pc_uptime_seconds()
        if uptime > 0:
            lines.append(f"电脑开机时间：{human_seconds(uptime)}")
        else:
            lines.append("电脑开机时间：⚠️ 未安装 psutil，无法获取")

    # ---- 消息统计 ----
    if show_basic:
        lines.append(f"收到消息数量：{GLOBAL_STATS['recv']} 条")
        lines.append(f"发出消息数量：{GLOBAL_STATS['send']} 条")

    # ---- CPU 占用（放在内存占用上面）----
    if show_cpu:
        lines.append(f"CPU占用：{get_cpu_usage_str()}")

    # ---- 运行内存占用 ----
    if show_mem:
        lines.append(f"运行内存占用：{get_memory_usage_str()}")

    # ---- 硬盘占用 ----
    if show_disk:
        lines.append("硬盘占用：")
        for line in get_disk_usage_str().splitlines():
            lines.append(f"  {line}")

    text = "\n".join(lines)

    tail = _cfg_text(cfg, "cmd_status_tail", "")
    if tail.strip():
        text = f"{text}\n{tail}"

    return text