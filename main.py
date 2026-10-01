#测试#
import os
import time
import json
import asyncio
import datetime
import inspect
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.event.filter import EventMessageType
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import At, Plain, Image, Video
from aiohttp import web

def _with_cors(resp: web.Response) -> web.Response:
    """
    已不再下发任何 CORS 放行头。
    页面与接口都由 AstrBot 面板同源访问，放开跨域只会扩大攻击面，
    因此这里只原样返回响应（函数名保留以兼容既有调用）。
    """
    return resp

async def _options_handler(request):
    """处理浏览器 OPTIONS 预检：只回 204，不附带任何 CORS 放行头"""
    return web.Response(status=204)


async def _fetch_daily_news_text() -> str:
    """拉取 60s 读报的文字版，作为图片不可用时的回退。"""
    try:
        import aiohttp as _aiohttp
        from .core.daily_news import NEWS_API_TEXT
        _t = _aiohttp.ClientTimeout(total=15)
        async with _aiohttp.ClientSession(timeout=_t) as session:
            async with session.get(NEWS_API_TEXT) as resp:
                if resp.status != 200:
                    return ""
                body = await resp.read()
        text = body.decode("utf-8", "ignore").strip()
        if not text:
            return ""
        return "📰 【今日读报】\n\n" + text
    except Exception:
        logger.exception("[apix-meme] 获取读报文字失败")
        return ""

try:
    from .core.system_status import (
        collect_runtime_status,
        GLOBAL_STATS,
        set_plugin_version,
    )
    _HAS_STATUS = True
except Exception as e:
    _HAS_STATUS = False
    GLOBAL_STATS = {"recv": 0, "send": 0}
    def set_plugin_version(v): pass
    logger.warning(f"[apix-meme] system_status 模块加载失败: {e}")

try:
    from .core.group_filter import (
        parse_line_list,
        parse_group_block_keywords,
        is_group_allowed,
        is_keyword_blocked,
        parse_gid_whitelist,
        group_allowed,
    )
    _HAS_FILTER = True
except Exception as e:
    _HAS_FILTER = False
    logger.warning(f"[apix-meme] group_filter 模块加载失败: {e}")
    def parse_line_list(raw): return []
    def parse_group_block_keywords(raw): return {}
    def is_group_allowed(g, m, w, b): return True
    def is_keyword_blocked(g, k, mp): return False
    def parse_gid_whitelist(raw): return []
    def group_allowed(g, allowed): return True

try:
    from .core.fortune import FortuneModule
    _HAS_FORTUNE = True
except Exception as e:
    _HAS_FORTUNE = False
    FortuneModule = None
    logger.warning(f"[apix-meme] fortune 模块加载失败: {e}")

try:
    from .core.husband import HusbandModule
    _HAS_HUSBAND = True
except Exception as e:
    _HAS_HUSBAND = False
    HusbandModule = None
    logger.warning(f"[apix-meme] husband 模块加载失败: {e}")

try:
    from .core.luck import LuckModule
    _HAS_LUCK = True
except Exception as e:
    _HAS_LUCK = False
    LuckModule = None
    logger.warning(f"[apix-meme] luck 模块加载失败: {e}")

try:
    from .core.meme_api import (
        parse_params,
        build_url,
        download_image,
        download_media,
        detect_param_types,
    )
    _HAS_MEME_API = True
except Exception as e:
    _HAS_MEME_API = False
    logger.warning(f"[apix-meme] meme_api 模块加载失败: {e}")
    def parse_params(raw): return []
    def build_url(t, p): return t
    def detect_param_types(t, n): return ["any"] * n
    async def download_image(url, timeout=15):
        raise RuntimeError("meme_api 模块未加载")
    async def download_media(url, timeout=15):
        raise RuntimeError("meme_api 模块未加载")

try:
    from .core.word_reply import WordReplyModule
    _HAS_WORD_REPLY = True
except Exception as e:
    _HAS_WORD_REPLY = False
    WordReplyModule = None
    logger.warning(f"[apix-meme] word_reply 模块加载失败: {e}")

try:
    from .core.greeting import GreetingModule
    _HAS_GREETING = True
except Exception as e:
    _HAS_GREETING = False
    GreetingModule = None
    logger.warning(f"[apix-meme] greeting 模块加载失败: {e}")

try:
    from .core.minecraft import MinecraftVersionModule
    _HAS_MINECRAFT = True
except Exception as e:
    _HAS_MINECRAFT = False
    MinecraftVersionModule = None
    logger.warning(f"[apix-meme] minecraft 模块加载失败: {e}")

try:
    from .core.checkin import CheckinModule
    _HAS_CHECKIN = True
except Exception as e:
    _HAS_CHECKIN = False
    CheckinModule = None
    logger.warning(f"[apix-meme] checkin 模块加载失败: {e}")

try:
    from .core.group_admin import GroupAdminModule
    _HAS_GROUP_ADMIN = True
except Exception as e:
    _HAS_GROUP_ADMIN = False
    GroupAdminModule = None
    logger.warning(f"[apix-meme] group_admin 模块加载失败: {e}")

try:
    from .core.admin_commands import AdminCommands, FEATURE_LABEL
    _HAS_ADMIN_CMDS = True
except Exception as e:
    _HAS_ADMIN_CMDS = False
    AdminCommands = None
    FEATURE_LABEL = {}
    logger.warning(f"[apix-meme] admin_commands 模块加载失败: {e}")

try:
    from .core.hourly_chime import HourlyChimeModule
    _HAS_HOURLY_CHIME = True
except Exception as e:
    _HAS_HOURLY_CHIME = False
    HourlyChimeModule = None
    logger.warning(f"[apix-meme] hourly_chime 模块加载失败: {e}")

try:
    from .core.web_config import (
        register_web_apis,
        read_schema,
        read_config,
        write_config,
    )
    _HAS_WEB_CONFIG = True
except Exception as e:
    _HAS_WEB_CONFIG = False
    logger.warning(f"[apix-meme] web_config 模块加载失败: {e}")
    def register_web_apis(context): return False
    def read_schema(): return {}
    def read_config(): return {}
    def write_config(data): return False

try:
    from .core.status_push import StatusPushModule, fmt_seconds
    _HAS_STATUS_PUSH = True
except Exception as e:
    _HAS_STATUS_PUSH = False
    StatusPushModule = None
    def fmt_seconds(sec): return "—"
    logger.warning(f"[apix-meme] status_push 模块加载失败: {e}")

try:
    from .core.moderation import (
        ModerationModule,
        parse_blacklist,
        get_action as get_blacklist_action,
        upsert_blacklist,
        remove_blacklist,
        ACTION_KICK,
        ACTION_MUTE,
        ACTION_IGNORE,
        ACTION_LABEL,
    )
    _HAS_MODERATION = True
except Exception as e:
    _HAS_MODERATION = False
    ModerationModule = None
    logger.warning(f"[apix-meme] moderation 模块加载失败: {e}")
    def parse_blacklist(raw): return {}
    def get_blacklist_action(bl, uid, default="ignore"): return ""
    def upsert_blacklist(raw, uid, act): return str(raw or "")
    def remove_blacklist(raw, uid): return str(raw or ""), False
    ACTION_KICK, ACTION_MUTE, ACTION_IGNORE = "kick", "mute", "ignore"
    ACTION_LABEL = {}

try:
    from .core.daily_news import DailyNewsModule
    _HAS_DAILY_NEWS = True
except Exception as e:
    _HAS_DAILY_NEWS = False
    DailyNewsModule = None
    logger.warning(f"[apix-meme] daily_news 模块加载失败: {e}")

try:
    from .core.umo_push import (
        get_event_umo,
        push_message,
    )
    _HAS_UMO_PUSH = True
except Exception as e:
    _HAS_UMO_PUSH = False
    logger.warning(f"[apix-meme] umo_push 模块加载失败: {e}")
    def get_event_umo(event): return ""
    async def push_message(context, group_id, text, umo="",
                           hourly_chime_module=None, minecraft_module=None):
        return False

try:
    from .core.menu_builder import (
        build_main_menu,
        build_meme_menu,
        build_mc_menu,
        build_greeting_menu,
        build_checkin_menu,
        build_daily_menu,
        build_admin_menu,
        build_meme_feature_menu,
        build_mc_version_menu,
        build_greeting_morning_menu,
        build_greeting_night_menu,
        build_greeting_rank_menu,
        build_checkin_signin_menu,
        build_checkin_query_menu,
        build_checkin_bank_menu,
        build_checkin_steal_menu,
        build_checkin_mount_menu,
        build_checkin_job_menu,
        build_meme_admin_menu,
        build_word_admin_menu,
        build_checkin_admin_menu,
        build_status_admin_menu,
        build_switch_admin_menu,
        build_chime_admin_menu,
        build_news_admin_menu,
        build_member_admin_menu,
        build_must_at_admin_menu,
        build_super_admin_menu,
    )
    _HAS_MENU = True
except Exception as e:
    _HAS_MENU = False
    logger.warning(f"[apix-meme] menu_builder 模块加载失败: {e}")
    def build_main_menu(p): return ""
    def build_meme_menu(p): return ""
    def build_mc_menu(p): return ""
    def build_greeting_menu(p): return ""
    def build_checkin_menu(p): return ""
    def build_daily_menu(p): return ""
    def build_admin_menu(p): return ""
    def build_meme_feature_menu(p): return ""
    def build_mc_version_menu(p): return ""
    def build_greeting_morning_menu(p): return ""
    def build_greeting_night_menu(p): return ""
    def build_greeting_rank_menu(p): return ""
    def build_checkin_signin_menu(p): return ""
    def build_checkin_query_menu(p): return ""
    def build_checkin_bank_menu(p): return ""
    def build_checkin_steal_menu(p): return ""
    def build_checkin_mount_menu(p): return ""
    def build_checkin_job_menu(p): return ""
    def build_meme_admin_menu(p): return ""
    def build_word_admin_menu(p): return ""
    def build_checkin_admin_menu(p): return ""
    def build_status_admin_menu(p): return ""
    def build_switch_admin_menu(p): return ""
    def build_chime_admin_menu(p): return ""
    def build_news_admin_menu(p): return ""
    def build_member_admin_menu(p): return ""
    def build_must_at_admin_menu(p): return ""
    def build_super_admin_menu(p): return ""

try:
    from .core.background import (
        ensure_mc_checker,
        ensure_hourly_chime,
        ensure_status_push,
        daily_status_push_checker,
        ensure_daily_news,
        daily_news_checker,
    )
    _HAS_BACKGROUND = True
except Exception as e:
    _HAS_BACKGROUND = False
    logger.warning(f"[apix-meme] background 模块加载失败: {e}")
    async def ensure_mc_checker(plugin): pass
    async def ensure_hourly_chime(plugin): pass
    async def ensure_status_push(plugin): pass
    async def daily_status_push_checker(plugin): pass
    async def ensure_daily_news(plugin): pass
    async def daily_news_checker(plugin): pass


# ============================================================
# ★ 引用新的工具模块
# ============================================================
from .core.path_utils import (
    PLUGIN_ID,
    plugin_dir as _plugin_dir,
    config_path as _config_path,
    fortune_data_path as _fortune_data_path,
    husband_data_path as _husband_data_path,
    luck_data_path as _luck_data_path,
    greeting_data_path as _greeting_data_path,
    minecraft_data_path as _minecraft_data_path,
    checkin_data_path as _checkin_data_path,
    hourly_chime_data_path as _hourly_chime_data_path,
    status_push_data_path as _status_push_data_path,
    daily_news_data_path as _daily_news_data_path,
    read_plugin_version,
    read_disk_config,
    write_disk_config,
)
from .core.event_helpers import (
    to_str,
    get_group_id_from_event as _get_group_id_from_event,
    get_ats_from_msg,
    split_text_and_ats,
    restore_ats,
    has_at_bot,
    get_sender_name,
)
from .core.nickname import NicknameCache


@register(
    PLUGIN_ID,
    "鸡鸡娱乐系统",
    "接口系统 + 每日运势 + 今日老公 + 今日人品 + 早安晚安 + Minecraft Java版检测 + 电脑状态 + 定时状态推送 + 每日读报 + 自定义词库 + 早晚安打卡排行 + 每日签到 + 偷积分 + 银行系统 + 坐骑商店 + 打工系统 + 整点报时 + 群员管理 + 数据备份 + 简约菜单系统",
    "1.7.1",
    "chicken butt"
)
class ApixIqfkSimpleMeme(Star):
    BASE_URL = "https://apix.iqfk.top/api/sv1"
    PAGE_SIZE = 20

    def __init__(self, context: Context, config: dict):
        super().__init__(context)

        self.config = config or {}
        self.rules = []
        self.must_at_bot = False
        self.default_key = "dd13536f0b5756d4"
        self.cmd_main_name = "鸡鸡娱乐系统"
        self.cmd_admin_name = "管理员指令"
        self.cmd_list_name = "表情包列表"
        self.cmd_greeting_morning_raw = "早安,早上好,起床"
        self.cmd_greeting_night_raw = "晚安,睡觉,睡了"
        self.cmd_minecraft_name = "MC版本"
        self.cmd_mc_auto_name = "MC自动检测"
        self.cmd_mc_test_name = "MC测试推送"
        self.cmd_add_name = "添加表情"
        self.cmd_del_name = "删除规则"
        self.cmd_save_name = "保存规则"
        self.cmd_status_names = ["电脑状态"]
        self.cmd_status_name = "电脑状态"
        self.cmd_word_add_name = "加词"
        self.cmd_word_del_name = "删词"
        self.cmd_word_list_name = "词库列表"
        self.cmd_enable_name = "娱乐系统开"
        self.cmd_disable_name = "娱乐系统关"
        self.cmd_view_admin_name = "查看管理员"
        self.cmd_refresh_admin_name = "刷新群管"
        self.cmd_add_admin_name = "加管理员"
        self.cmd_del_admin_name = "删管理员"
        self.cmd_admin_list_name = "管理员列表"
        self.cmd_enable_feature_name = "开启功能"
        self.cmd_disable_feature_name = "关闭功能"
        self.cmd_feature_status_name = "功能状态"
        self.cmd_greeting_rank_name = "打卡排行"
        self.cmd_greeting_stats_name = "打卡统计"
        self.cmd_job_add_name = "添加工种"
        self.cmd_job_del_name = "删除工种"
        self.cmd_mount_add_name = "添加坐骑"
        self.cmd_mount_del_name = "删除坐骑"

        self.cmd_must_at_bot_on_name = "必须艾特开"
        self.cmd_must_at_bot_off_name = "必须艾特关"
        self.cmd_must_at_bot_status_name = "必须艾特状态"

        self.cmd_meme_menu_name = "接口系统"
        self.cmd_meme_image_name = "图片接口"
        self.cmd_meme_video_name = "视频接口"
        self.cmd_mc_menu_name = "MC系统"
        self.cmd_greeting_menu_name = "打卡系统"
        self.cmd_checkin_menu_name = "签到系统"
        self.cmd_daily_menu_name = "每日系列"

        self.cmd_chime_on_name = "整点报时开"
        self.cmd_chime_off_name = "整点报时关"
        self.cmd_chime_status_name = "整点报时状态"
        self.cmd_chime_hours_name = "整点报时时段"
        self.cmd_chime_text_name = "整点报时文案"
        self.cmd_chime_list_name = "整点报时列表"
        self.cmd_chime_test_name = "整点报时测试"

        # ★ 每日定时状态推送指令
        self.cmd_daily_push_on_name = "状态推送开"
        self.cmd_daily_push_off_name = "状态推送关"
        self.cmd_daily_push_time_name = "状态推送间隔"
        self.cmd_daily_push_list_name = "状态推送列表"

        # ★ 群员管理指令
        self.cmd_kick_name = "踢出群员"
        self.cmd_mute_name = "禁言群员"
        self.cmd_unmute_name = "解除禁言"
        self.cmd_blacklist_name = "拉黑成员"
        self.cmd_unblacklist_name = "解除拉黑"
        self.cmd_blacklist_list_name = "黑名单列表"

        # ★ 每日读报指令
        self.cmd_daily_news_name = "每日读报"
        self.cmd_daily_news_on_name = "读报推送开"
        self.cmd_daily_news_off_name = "读报推送关"
        self.cmd_daily_news_time_name = "读报推送时间"
        self.cmd_daily_news_list_name = "读报推送列表"

        self.group_mode = "off"
        self.group_whitelist = []
        self.group_blacklist = []
        # ★ 群白名单（不填 = 不限制群聊）
        self.allowed_groups = []
        # ★ 电脑状态单独群开关
        self.status_groups = []
        # ★ 电脑状态功能总开关（同时控制定时推送）
        self.status_enable = True
        # ★ 接口系统功能总开关 + 允许使用的群号（留空=不限群）
        self.meme_enable = True
        self.meme_groups = []
        self.group_block_map = {}
        self.disabled_groups = []
        self.plugin_admins = []
        self.web_admin_token = ""   # 写操作令牌（可选，reload_cfg 会按配置覆盖）
        # 群员管理（reload_cfg 会按配置覆盖）
        self.moderation_enable = True
        self._blacklist_raw = ""
        self.member_blacklist = {}
        self.blacklist_default_action = "ignore"
        self.mute_duration = 600
        self.group_feature_switches = {}
        self.group_must_at_bot = {}
        self.minecraft_auto_groups = []
        self.minecraft_test_groups = []
        self.feature_switch = {
            "fortune": True,
            "husband": True,
            "luck": True,
            "word_reply": True,
            "meme": True,
            "greeting": True,
            "minecraft": True,
            "checkin": True,
        }

        self._dirty = False
        self._mc_checker_started = False
        self._mc_checker_task = None
        self._chime_checker_started = False
        self._chime_checker_task = None
        self._status_push_started = False
        self._status_push_task = None
        self._daily_news_started = False
        self._daily_news_task = None
        self._platform_id_cache = None

        # ★ 全局昵称缓存（跨群共享 QQ 昵称）
        self._nickname_cache = NicknameCache()
        self.nickname_cache = self._nickname_cache.as_dict()

        try:
            set_plugin_version(read_plugin_version(self))
        except Exception:
            logger.exception("[apix-meme] 注入插件版本失败")

        self.fortune_module = None
        if _HAS_FORTUNE:
            try:
                self.fortune_module = FortuneModule(
                    plugin_dir=_plugin_dir(),
                    data_path=_fortune_data_path(),
                )
            except Exception:
                logger.exception("[apix-meme] 初始化运势模块失败")

        self.husband_module = None
        if _HAS_HUSBAND:
            try:
                self.husband_module = HusbandModule(
                    plugin_dir=_plugin_dir(),
                    data_path=_husband_data_path(),
                )
                logger.info("[apix-meme] 老公模块初始化成功")
            except Exception:
                logger.exception("[apix-meme] 初始化老公模块失败")

        self.luck_module = None
        if _HAS_LUCK:
            try:
                self.luck_module = LuckModule(
                    plugin_dir=_plugin_dir(),
                    data_path=_luck_data_path(),
                )
                logger.info("[apix-meme] 人品模块初始化成功")
            except Exception:
                logger.exception("[apix-meme] 初始化人品模块失败")

        self.word_reply_module = None
        if _HAS_WORD_REPLY:
            try:
                self.word_reply_module = WordReplyModule(
                    plugin_dir=_plugin_dir(),
                    data_path="",
                )
                logger.info("[apix-meme] 词库模块初始化成功")
            except Exception:
                logger.exception("[apix-meme] 初始化词库模块失败")

        self.greeting_module = None
        if _HAS_GREETING:
            try:
                self.greeting_module = GreetingModule(
                    plugin_dir=_plugin_dir(),
                    data_path=_greeting_data_path(),
                )
                self.greeting_module.nickname_cache = self.nickname_cache
                logger.info("[apix-meme] 早安晚安模块初始化成功")
            except Exception:
                logger.exception("[apix-meme] 初始化早安晚安模块失败")

        self.minecraft_module = None
        if _HAS_MINECRAFT:
            try:
                self.minecraft_module = MinecraftVersionModule(
                    plugin_dir=_plugin_dir(),
                    data_path=_minecraft_data_path(),
                )
                logger.info("[apix-meme] MC 版本检测模块初始化成功")
            except Exception:
                logger.exception("[apix-meme] 初始化 MC 版本模块失败")

        self.checkin_module = None
        if _HAS_CHECKIN:
            try:
                self.checkin_module = CheckinModule(
                    plugin_dir=_plugin_dir(),
                    data_path=_checkin_data_path(),
                )
                self.checkin_module.nickname_cache = self.nickname_cache
                logger.info("[apix-meme] 签到模块初始化成功")
            except Exception:
                logger.exception("[apix-meme] 初始化签到模块失败")

        self.group_admin_module = None
        if _HAS_GROUP_ADMIN:
            try:
                self.group_admin_module = GroupAdminModule()
                logger.info("[apix-meme] 群管识别模块初始化成功")
            except Exception:
                logger.exception("[apix-meme] 初始化群管模块失败")

        self.moderation_module = None
        if _HAS_MODERATION:
            try:
                self.moderation_module = ModerationModule(self.group_admin_module)
                logger.info("[apix-meme] 群员管理模块初始化成功")
            except Exception:
                logger.exception("[apix-meme] 初始化群员管理模块失败")

        self.admin_commands = None
        if _HAS_ADMIN_CMDS:
            try:
                self.admin_commands = AdminCommands(self)
                logger.info("[apix-meme] 管理指令模块初始化成功")
            except Exception:
                logger.exception("[apix-meme] 初始化管理指令模块失败")

        self.hourly_chime_module = None
        if _HAS_HOURLY_CHIME:
            try:
                self.hourly_chime_module = HourlyChimeModule(
                    plugin_dir=_plugin_dir(),
                    data_path=_hourly_chime_data_path(),
                )
                logger.info("[apix-meme] 整点报时模块初始化成功")
            except Exception:
                logger.exception("[apix-meme] 初始化整点报时模块失败")

        self.status_push_module = None
        if _HAS_STATUS_PUSH:
            try:
                self.status_push_module = StatusPushModule(
                    plugin_dir=_plugin_dir(),
                    data_path=_status_push_data_path(),
                )
                logger.info("[apix-meme] 定时状态推送模块初始化成功")
            except Exception:
                logger.exception("[apix-meme] 初始化定时状态推送模块失败")

        self.daily_news_module = None
        if _HAS_DAILY_NEWS:
            try:
                self.daily_news_module = DailyNewsModule(
                    plugin_dir=_plugin_dir(),
                    data_path=_daily_news_data_path(),
                )
                logger.info("[apix-meme] 每日读报模块初始化成功")
            except Exception:
                logger.exception("[apix-meme] 初始化每日读报模块失败")

        try:
            logger.info(f"[apix-meme] 磁盘配置路径: {_config_path()}")
        except Exception:
            pass

        self.reload_cfg()
        self._migrate_old_format()

        # 1) 先注册桥接路由（给独立 HTML 用）
        try:
            self._register_bridge_routes()
        except Exception:
            logger.exception("[apix-meme] 注册桥接路由异常")

        # 2) 再注册 web_config 的 aiohttp 路由（备选）
        if _HAS_WEB_CONFIG:
            try:
                ok = register_web_apis(self.context)
                if ok:
                    logger.info("[apix-meme] 自定义配置页面路由已注册")
                else:
                    logger.warning("[apix-meme] 自定义配置页面路由注册失败")
            except Exception:
                logger.exception("[apix-meme] 注册自定义配置页面路由异常")

    # ============================================================
    # ★ 注册桥接路由（同源访问，不下发任何 CORS 放行头）
    # ============================================================
    def _register_bridge_routes(self):
        try:
            from astrbot.api.web import json_response, error_response
        except Exception:
            try:
                from aiohttp import web as _web
                def json_response(data, status_code=200):
                    return _web.json_response(data, status=status_code)
                def error_response(msg, status_code=400):
                    return _web.json_response({"ok": False, "msg": msg}, status=status_code)
            except Exception:
                json_response = lambda d, status_code=200: d
                error_response = lambda m, status_code=400: {"ok": False, "msg": m}

        # ★ 安全：本插件的页面与接口都由 AstrBot 面板同源访问，
        #   因此不再下发任何 Access-Control-Allow-Origin（避免跨域全开）。
        #   同时校验 Origin，非本机/非面板来源的跨域请求一律拒绝。

        def _origin_allowed(request) -> bool:
            """
            校验请求来源：
              · 没有 Origin 头 —— 同源请求或非浏览器客户端，放行
              · 有 Origin —— 只允许与本机同源的地址（面板自身）
            """
            try:
                req = request if request is not None else _bound_request()
                if req is None:
                    return True
                headers = getattr(req, "headers", None)
                if not headers:
                    return True
                origin = str(headers.get("Origin", "") or "").strip()
                if not origin:
                    return True
                from urllib.parse import urlparse
                host = urlparse(origin).hostname or ""
                return host in ("127.0.0.1", "localhost", "::1", "0.0.0.0")
            except Exception:
                # 校验本身出错时不拦截，避免误伤正常使用
                return True

        def _with_cors(resp):
            """不再下发 CORS 头，仅返回响应本身（保留函数名以免大范围改动）"""
            return resp

        def _options_response():
            """OPTIONS 直接返回 204，不带任何 CORS 放行头"""
            try:
                from aiohttp import web as _web
                return _web.Response(status=204)
            except Exception:
                return {"ok": True}

        def _reject_cross_origin(request=None):
            """跨域来源直接拒绝，返回 Response 或 None"""
            if _origin_allowed(request):
                return None
            logger.warning("[apix-meme] 已拒绝来自非本机来源的 Web 请求")
            return _with_cors(json_response(
                {"ok": False, "msg": "拒绝跨域访问"}, status_code=403
            ))

        def _require_admin(request=None):
            """
            写操作的额外鉴权。

            说明：这些接口本身已由 AstrBot 面板（需登录）分发，且上面已强制
            拒绝跨域来源，因此这里提供一层**可选的**令牌校验：
              · 后台配置了 `web_admin_token` -> 必须携带匹配的令牌才能写
              · 未配置令牌 -> 依赖「同源 + 面板登录」这层防护
            返回 None 表示通过，否则返回错误响应。
            """
            token_cfg = str(getattr(self, "web_admin_token", "") or "").strip()
            if not token_cfg:
                return None
            try:
                req = request if request is not None else _bound_request()
            except Exception:
                req = request
            given = ""
            try:
                if req is not None:
                    h = getattr(req, "headers", None)
                    if h:
                        given = str(h.get("X-Plugin-Token", "") or "")
            except Exception:
                given = ""
            if given and given == token_cfg:
                return None
            logger.warning("[apix-meme] 写操作令牌校验失败，已拒绝")
            return _with_cors(json_response(
                {"ok": False, "msg": "无权限：令牌缺失或不正确"},
                status_code=403,
            ))

        # ---------- 请求对象 / 请求体提取 ----------
        def _bound_request():
            """AstrBot 4.27+ 插件 Web API 的请求对象由框架绑定在模块级代理上，
            而不是通过处理函数的第一个位置参数传入（路由无 <...> 占位符时
            框架只会传 path_params，request 永远是 None）。"""
            try:
                from astrbot.api.web import request as _req
                return _req
            except Exception:
                return None

        def _req_method(src) -> str:
            if src is None:
                return ""
            try:
                return str(getattr(src, "method", "") or "").upper()
            except Exception:
                return ""

        async def _extract_payload(request=None, kwargs=None):
            """按 位置参数 → 框架绑定请求(body/json) → kwargs 顺序提取配置字典。"""
            # 1) 位置参数直接就是配置字典（旧版 aiohttp 直连路由）
            if isinstance(request, dict) and request:
                return request

            # 2) 框架绑定的请求对象（AstrBot 4.27+ 唯一可靠来源）
            #    同时兼容 Starlette 风格 json()/text()/body()
            #    与 Quart 风格 get_json()/get_data()
            for src in (_bound_request(), request):
                if src is None:
                    continue
                for reader in ("json", "text", "body", "get_json", "get_data"):
                    fn = getattr(src, reader, None)
                    if not callable(fn):
                        continue
                    try:
                        raw = fn()
                        if inspect.isawaitable(raw):
                            raw = await raw
                    except Exception:
                        continue
                    if isinstance(raw, dict) and raw:
                        return raw
                    if isinstance(raw, (bytes, bytearray)):
                        raw = bytes(raw).decode("utf-8", "ignore")
                    if isinstance(raw, str) and raw.strip():
                        try:
                            parsed = json.loads(raw)
                        except Exception:
                            continue
                        if isinstance(parsed, dict) and parsed:
                            return parsed

            # 3) kwargs 兜底（仅 path_params，通常为空）
            if kwargs:
                meta_keys = {"request", "self", "context", "data", "config", "body", "payload"}
                candidate = {k: v for k, v in kwargs.items() if k not in meta_keys}
                if candidate:
                    return candidate
            return None

        # ---------- GET /config ----------
        async def _get_config_handler(request=None, **kwargs):
            # OPTIONS 预检
            if _req_method(request) == "OPTIONS" or _req_method(_bound_request()) == "OPTIONS":
                return _options_response()
            # ★ 安全：拒绝跨域
            denied = _reject_cross_origin(request)
            if denied is not None:
                return denied
            try:
                schema = {}
                if _HAS_WEB_CONFIG:
                    try:
                        schema = read_schema()
                    except Exception:
                        logger.exception("[apix-meme] read_schema 失败")
                config = self._read_disk_config() or {}
                if not isinstance(config, dict):
                    config = {}
                logger.info(
                    f"[apix-meme] GET /config: schema={len(schema)} config={len(config)}"
                )
                return _with_cors(json_response({"ok": True, "schema": schema, "config": config}))
            except Exception as e:
                logger.exception("[apix-meme] GET /config 失败")
                return _with_cors(error_response(f"读取失败: {e}", status_code=500))

        # ---------- POST /config ----------
        async def _save_config_handler(request=None, **kwargs):
            # OPTIONS 预检（request 可能为 None，必须用安全的取值方式）
            if _req_method(request) == "OPTIONS" or _req_method(_bound_request()) == "OPTIONS":
                return _options_response()
            # ★ 安全：拒绝跨域 + 写操作鉴权
            denied = _reject_cross_origin(request)
            if denied is not None:
                return denied
            denied = _require_admin(request)
            if denied is not None:
                return denied

            try:
                logger.info("[apix‑meme] POST /config 被调用")
                data = await _extract_payload(request, kwargs)
                logger.info(f"[apix-meme] POST /config 提取到 payload 类型={type(data).__name__}")

                # 兼容外层再包一层 {data:{}} / {config:{}}
                if isinstance(data, dict):
                    for _wrap in ("data", "config"):
                        if len(data) == 1 and isinstance(data.get(_wrap), dict) and data[_wrap]:
                            data = data[_wrap]
                            break

                # 校验数据
                if not isinstance(data, dict) or not data:
                    logger.warning("[apix-meme] POST /config 数据为空")
                    return _with_cors(json_response({"ok": False, "msg": "数据为空"}))

                # 读取旧配置，合并更新
                old_cfg = self._read_disk_config() or {}
                if not isinstance(old_cfg, dict):
                    old_cfg = {}
                old_cfg.update(data)
                save_ok = self._write_disk_config(old_cfg)

                logger.info(f"[apix-meme] 配置保存结果 ok={save_ok}，共 {len(data)} 项")
                return _with_cors(json_response({
                    "ok": bool(save_ok),
                    "msg": "已保存" if save_ok else "保存失败！",
                    "config": old_cfg,
                }))

            except Exception as e:
                logger.exception("[apix-meme] 保存配置接口异常")
                return _with_cors(json_response({"ok": False, "msg": f"保存失败:{e}"}, status_code=500))

        # ---------- GET /previewStatus ----------
        async def _preview_status_handler(request=None, **kwargs):
            """返回当前配置下的电脑状态文本，供独立页面预览。"""
            # ★ 安全：拒绝跨域
            denied = _reject_cross_origin(request)
            if denied is not None:
                return denied
            try:
                group_id = ""
                try:
                    req = _bound_request()
                    q = getattr(req, "query", None)
                    if q is not None:
                        group_id = str(q.get("group_id", "") or "")
                    if not group_id:
                        group_id = str(kwargs.get("group_id", "") or "")
                except Exception:
                    pass

                text = collect_runtime_status(
                    event=None,
                    group_id=group_id or None,
                    cfg=self._read_disk_config() or {},
                )
                return _with_cors(json_response({
                    "ok": True,
                    "text": text,
                    "group_id": group_id,
                }))
            except Exception as e:
                logger.exception("[apix-meme] 预览电脑状态失败")
                return _with_cors(json_response({"ok": False, "msg": f"预览失败: {e}"}, status_code=500))

        # ---------- POST /testStatusPush ----------
        async def _test_status_push_handler(request=None, **kwargs):
            """按当前（含未保存）配置生成状态文本并立即推送到指定群。"""
            # ★ 安全：拒绝跨域 + 写操作鉴权
            denied = _reject_cross_origin(request)
            if denied is not None:
                return denied
            denied = _require_admin(request)
            if denied is not None:
                return denied
            try:
                if self.status_push_module is None:
                    return _with_cors(json_response({"ok": False, "msg": "定时状态推送模块未加载"}))

                data = await _extract_payload(request, kwargs)
                if isinstance(data, dict):
                    for _wrap in ("data", "config"):
                        if len(data) == 1 and isinstance(data.get(_wrap), dict) and data[_wrap]:
                            data = data[_wrap]
                            break
                if not isinstance(data, dict):
                    data = {}

                group_id = str(data.pop("group_id", "") or "").strip()
                # 优先用推送模块里已知的群；否则取已开启推送的第一个群
                if not group_id:
                    enabled = self.status_push_module.list_groups()
                    if enabled:
                        group_id = enabled[0]["group_id"]
                if not group_id:
                    return _with_cors(json_response({
                        "ok": False,
                        "msg": "没有可推送的群：请先在群里用「状态推送开」开启，或把群号作为 group_id 传入",
                    }))

                # 磁盘配置 + 表单里未保存的修改
                cfg = dict(self._read_disk_config() or {})
                cfg.update(data)

                text = collect_runtime_status(
                    event=None, group_id=group_id, cfg=cfg
                )
                umo = self.status_push_module.get_umo(group_id)
                ok = await self._push_mc_notification(group_id, text, umo=umo)
                logger.info(f"[apix-meme] 测试推送群 {group_id} 结果 ok={ok}")
                return _with_cors(json_response({
                    "ok": bool(ok),
                    "group_id": group_id,
                    "msg": "已推送" if ok else "推送失败：该群可能尚未记录 UMO（请先在该群发一条消息）",
                }))
            except Exception as e:
                logger.exception("[apix-meme] 测试推送失败")
                return _with_cors(json_response({"ok": False, "msg": f"推送失败: {e}"}, status_code=500))

        # ---------- GET /backupInfo ----------
        async def _backup_info_handler(request=None, **kwargs):
            """返回默认备份目录与数据文件清单，供页面展示。"""
            # ★ 安全：拒绝跨域
            denied = _reject_cross_origin(request)
            if denied is not None:
                return denied
            try:
                from .core.backup import all_data_files, default_backup_dir
                files = []
                for label, path in all_data_files():
                    try:
                        exists = os.path.isfile(path)
                        size = os.path.getsize(path) if exists else 0
                    except Exception:
                        exists, size = False, 0
                    files.append({
                        "label": label,
                        "file": os.path.basename(path),
                        "exists": exists,
                        "size": size,
                    })
                return _with_cors(json_response({
                    "ok": True,
                    "default_dir": default_backup_dir(),
                    "files": files,
                }))
            except Exception as e:
                logger.exception("[apix-meme] 读取备份信息失败")
                return _with_cors(json_response({"ok": False, "msg": f"读取失败: {e}"}, status_code=500))

        # ---------- POST /backup ----------
        async def _backup_handler(request=None, **kwargs):
            """把数据备份到指定目录（留空则用默认目录）。"""
            # ★ 安全：拒绝跨域 + 写操作鉴权
            denied = _reject_cross_origin(request)
            if denied is not None:
                return denied
            denied = _require_admin(request)
            if denied is not None:
                return denied
            try:
                data = await _extract_payload(request, kwargs)
                if isinstance(data, dict):
                    for _wrap in ("data", "config"):
                        if len(data) == 1 and isinstance(data.get(_wrap), dict) and data[_wrap]:
                            data = data[_wrap]
                            break
                if not isinstance(data, dict):
                    data = {}
                target_dir = str(data.get("target_dir", "") or "").strip()

                from .core.backup import create_backup
                result = create_backup(target_dir)
                if result.get("ok"):
                    logger.info(f"[apix-meme] 数据已备份到 {result.get('path')}")
                return _with_cors(json_response(result))
            except Exception as e:
                logger.exception("[apix-meme] 备份失败")
                return _with_cors(json_response({"ok": False, "msg": f"备份失败: {e}"}, status_code=500))

        # ---------- GET /backupDownload ----------
        async def _backup_download_handler(request=None, **kwargs):
            """返回全部数据文件的聚合 JSON，供浏览器下载。"""
            # ★ 安全：拒绝跨域
            denied = _reject_cross_origin(request)
            if denied is not None:
                return denied
            try:
                from .core.backup import build_bundle
                result = build_bundle()
                return _with_cors(json_response(result))
            except Exception as e:
                logger.exception("[apix-meme] 生成下载包失败")
                return _with_cors(json_response({"ok": False, "msg": f"生成失败: {e}"}, status_code=500))

        # ---------- POST /importPreview ----------
        async def _import_preview_handler(request=None, **kwargs):
            """预检导入来源，不写入任何文件。"""
            # ★ 安全：拒绝跨域
            denied = _reject_cross_origin(request)
            if denied is not None:
                return denied
            try:
                data = await _extract_payload(request, kwargs)
                if isinstance(data, dict):
                    for _wrap in ("data", "config"):
                        if len(data) == 1 and isinstance(data.get(_wrap), dict) and data[_wrap]:
                            data = data[_wrap]
                            break
                if not isinstance(data, dict):
                    data = {}
                source = str(data.get("source", "") or "").strip()
                if not source:
                    return _with_cors(json_response({
                        "ok": False, "files": [], "total": 0,
                        "msg": "请填写备份目录或备份包路径",
                    }))
                from .core.backup import preview_import
                return _with_cors(json_response(preview_import(source)))
            except Exception as e:
                logger.exception("[apix-meme] 导入预检失败")
                return _with_cors(json_response({"ok": False, "files": [], "total": 0,
                                                 "msg": f"预检失败: {e}"}, status_code=500))

        # ---------- POST /importData ----------
        async def _import_data_handler(request=None, **kwargs):
            """从备份目录或备份包还原数据（导入前自动备份当前数据）。"""
            # ★ 安全：拒绝跨域 + 写操作鉴权
            denied = _reject_cross_origin(request)
            if denied is not None:
                return denied
            denied = _require_admin(request)
            if denied is not None:
                return denied
            try:
                data = await _extract_payload(request, kwargs)
                if isinstance(data, dict):
                    for _wrap in ("data", "config"):
                        if len(data) == 1 and isinstance(data.get(_wrap), dict) and data[_wrap]:
                            data = data[_wrap]
                            break
                if not isinstance(data, dict):
                    data = {}
                source = str(data.get("source", "") or "").strip()
                mode = str(data.get("mode", "replace") or "replace").strip()
                if mode not in ("replace", "merge_skip"):
                    mode = "replace"
                if not source:
                    return _with_cors(json_response({
                        "ok": False, "imported": [], "skipped": [],
                        "msg": "请填写备份目录或备份包路径",
                    }))
                from .core.backup import import_data
                result = import_data(source, mode=mode)
                if result.get("ok"):
                    logger.info(f"[apix-meme] 数据导入完成：{result.get('msg')}")
                return _with_cors(json_response(result))
            except Exception as e:
                logger.exception("[apix-meme] 导入失败")
                return _with_cors(json_response({"ok": False, "imported": [], "skipped": [],
                                                 "msg": f"导入失败: {e}"}, status_code=500))

        # ---------- GET /page ----------
        async def _page_handler(request=None, **kwargs):
            if _req_method(request) == "OPTIONS" or _req_method(_bound_request()) == "OPTIONS":
                return _options_response()
            # ★ 安全：拒绝跨域
            denied = _reject_cross_origin(request)
            if denied is not None:
                return denied
            try:
                if _HAS_WEB_CONFIG:
                    try:
                        from .core.web_config import render_page_html
                        html = render_page_html()
                        if html:
                            from aiohttp import web as _web
                            return _web.Response(text=html, content_type="text/html")
                    except Exception:
                        logger.exception("[apix-meme] 渲染页面失败")
                from aiohttp import web as _web
                return _web.Response(text="index.html not found", status=404)
            except Exception as e:
                logger.exception("[apix-meme] GET /page 失败")
                from aiohttp import web as _web
                return _web.Response(text=f"error: {e}", status=500)

        if not hasattr(self.context, "register_web_api"):
            logger.error("[apix-meme] context 没有 register_web_api，无法注册桥接路由")
            return False

        # ★ 给 config 路由加上 OPTIONS 方法
        routes = [
            (f"/{PLUGIN_ID}/config", _get_config_handler,  ["GET", "OPTIONS"],  "读取配置"),
            (f"/{PLUGIN_ID}/config", _save_config_handler, ["POST", "OPTIONS"], "保存配置"),
            (f"/{PLUGIN_ID}/previewStatus",    _preview_status_handler,    ["GET", "OPTIONS"],  "预览电脑状态"),
            (f"/{PLUGIN_ID}/testStatusPush",   _test_status_push_handler,  ["POST", "OPTIONS"], "测试推送电脑状态"),
            (f"/{PLUGIN_ID}/backupInfo",       _backup_info_handler,       ["GET", "OPTIONS"],  "备份信息"),
            (f"/{PLUGIN_ID}/backup",           _backup_handler,            ["POST", "OPTIONS"], "备份数据到目录"),
            (f"/{PLUGIN_ID}/backupDownload",   _backup_download_handler,   ["GET", "OPTIONS"],  "导出数据供下载"),
            (f"/{PLUGIN_ID}/importPreview",    _import_preview_handler,    ["POST", "OPTIONS"], "预检导入来源"),
            (f"/{PLUGIN_ID}/importData",       _import_data_handler,       ["POST", "OPTIONS"], "导入数据"),
            (f"/{PLUGIN_ID}/page",   _page_handler,        ["GET", "OPTIONS"],  "配置页面"),
        ]

        ok_count = 0
        for route, func, methods, desc in routes:
            try:
                self.context.register_web_api(route, func, methods, desc)
                ok_count += 1
                logger.info(f"[apix-meme] 桥接路由已注册: {route} {methods}")
            except Exception as e:
                logger.error(f"[apix-meme] 注册失败 {route} {methods}: {e}")

        return ok_count > 0

    # ============================================================
    # 基础判定 / 配置读写
    # ============================================================
    def _config_path(self) -> str:
        return _config_path()

    def _is_group_feature_enable(self, group_id: str, feature_key: str) -> bool:
        if not group_id:
            return True
        gid = str(group_id)
        group_cfg = self.group_feature_switches.get(gid, {})
        return bool(group_cfg.get(feature_key, True))

    def _should_require_at(self, group_id: str) -> bool:
        if group_id and str(group_id) in self.group_must_at_bot:
            return bool(self.group_must_at_bot[str(group_id)])
        return bool(self.must_at_bot)

    async def _check_admin(self, event) -> bool:
        if self.admin_commands is None:
            try:
                return event.is_admin()
            except Exception:
                return False
        return await self.admin_commands.check_admin(event)

    async def _push_mc_notification(self, group_id: str, text: str, umo: str = "") -> bool:
        return await push_message(
            self.context,
            group_id,
            text,
            umo=umo,
            hourly_chime_module=self.hourly_chime_module,
            minecraft_module=self.minecraft_module,
        )

    def _read_disk_config(self) -> dict:
        return read_disk_config()

    # ============================================================
    # ★ AstrBot 桥接入口：get_config / save_config
    # ============================================================
    async def get_config(self):
        """
        前端 AstrBotPluginPage.apiGet("getConfig") 会调用这里。
        返回 {"ok": True, "schema": {...}, "config": {...}}
        """
        try:
            schema = {}
            if _HAS_WEB_CONFIG:
                try:
                    schema = read_schema()
                except Exception:
                    logger.exception("[apix-meme] read_schema 失败")

            # 统一用 path_utils 读取，和 system_status.py 走同一个路径
            config = self._read_disk_config() or {}
            if not isinstance(config, dict):
                config = {}

            logger.info(
                f"[apix-meme] get_config: schema={len(schema)} 项, "
                f"config={len(config)} 项, path={_config_path()}"
            )
            return {"ok": True, "schema": schema, "config": config}
        except Exception:
            logger.exception("[apix-meme] get_config 失败")
            return {"ok": False, "msg": "读取失败", "schema": {}, "config": {}}

    async def save_config(self, data=None, **kwargs):
        """
        前端 AstrBotPluginPage.apiPost("saveConfig", {...}) 会调用这里。
        兼容 AstrBot 各种传参方式：
          - save_config({...})
          - save_config(data={...})
          - save_config(config={...})
          - save_config(body={...})
          - 甚至 kwargs 本身就是配置键值对
        """
        try:
            logger.info(
                f"[apix-meme] save_config 收到 type={type(data).__name__}, "
                f"kwargs_keys={list(kwargs.keys()) if kwargs else []}"
            )

            payload = None

            # ---------- 1) 位置参数 data ----------
            if isinstance(data, dict) and data:
                payload = data
                logger.info(f"[apix-meme] save_config 使用位置参数，{len(payload)} 项")

            # ---------- 2) kwargs 里带 data / config / body / payload ----------
            if not payload and kwargs:
                for k in ("data", "config", "body", "payload"):
                    v = kwargs.get(k)
                    if isinstance(v, dict) and v:
                        inner = v.get("data") if "data" in v and len(v) == 1 else v
                        if isinstance(inner, dict) and inner:
                            payload = inner
                            logger.info(f"[apix-meme] save_config 命中 kwargs[{k}]，{len(payload)} 项")
                            break
                    if isinstance(v, str) and v.strip():
                        try:
                            import json as _json
                            parsed = _json.loads(v)
                            if isinstance(parsed, dict) and parsed:
                                payload = parsed
                                logger.info(f"[apix-meme] save_config 命中 kwargs[{k}] 字符串，{len(payload)} 项")
                                break
                        except Exception:
                            pass

            # ---------- 3) kwargs 本身就是配置键值对 ----------
            if not payload and kwargs:
                meta_keys = {"request", "self", "context", "data", "config", "body", "payload"}
                candidate = {k: v for k, v in kwargs.items() if k not in meta_keys}
                if candidate:
                    payload = candidate
                    logger.info(f"[apix-meme] save_config 命中 kwargs 自身，{len(payload)} 项")

            if not isinstance(payload, dict) or not payload:
                logger.warning("[apix-meme] save_config 数据为空，拒绝保存")
                return {"ok": False, "msg": "保存数据为空"}

            # ---------- 4) 兼容外层再包一层 ----------
            if "data" in payload and isinstance(payload["data"], dict) and len(payload) == 1:
                payload = payload["data"]
            if "config" in payload and isinstance(payload["config"], dict) and len(payload) == 1:
                payload = payload["config"]

            logger.info(f"[apix-meme] save_config 待写入 keys={list(payload.keys())}")

            # ---------- 5) 统一用 path_utils 合并写盘 ----------
            existing = self._read_disk_config() or {}
            if not isinstance(existing, dict):
                existing = {}
            existing.update(payload)
            ok = self._write_disk_config(existing)
            return {"ok": bool(ok), "msg": "已保存" if ok else "保存失败"}
        except Exception:
            logger.exception("[apix-meme] save_config 失败")
            return {"ok": False, "msg": "保存异常"}

    def _write_disk_config(self, data: dict) -> bool:
        ok = write_disk_config(data)
        if ok:
            logger.info(f"[apix-meme] 已写入磁盘: {_config_path()}")
        return ok

    # ============================================================
    # 旧格式迁移
    # ============================================================
    def _migrate_old_format(self):
        try:
            disk_cfg = self._read_disk_config()
            if not disk_cfg:
                return
            api_list = disk_cfg.get("api_list", [])
            if not isinstance(api_list, list):
                return
            changed = False
            new_list = []
            for item in api_list:
                if not isinstance(item, dict):
                    continue
                kw = to_str(item.get("keywords", "")).strip()
                url_template = to_str(item.get("url_template", "")).strip()
                param_count = to_str(item.get("param_count", "")).strip()
                old_meme = to_str(item.get("meme", "")).strip()
                if not kw:
                    continue
                if not url_template and old_meme:
                    url_template = (
                        f"{self.BASE_URL}?meme={old_meme}"
                        f"&key={self.default_key}&pic={{pic}}"
                    )
                    param_count = param_count or "1"
                    changed = True
                elif url_template and "meme=&" in url_template and old_meme:
                    url_template = url_template.replace(
                        "meme=&", f"meme={old_meme}&"
                    )
                    changed = True
                if not url_template:
                    continue
                if not param_count:
                    param_count = "1"
                    changed = True
                if "meme" in item:
                    changed = True
                new_list.append({
                    "__template_key": "meme_rule",
                    "keywords": kw,
                    "url_template": url_template,
                    "param_count": param_count,
                    "media_type": to_str(item.get("media_type", "image")).strip().lower() or "image",
                    "json_field": to_str(item.get("json_field", "")).strip(),
                })
            if changed:
                disk_cfg["api_list"] = new_list
                self._write_disk_config(disk_cfg)
                logger.info(f"[apix-meme] 配置已自动迁移到新格式，共 {len(new_list)} 条规则")
        except Exception:
            logger.exception("[apix-meme] 自动迁移失败")

    # ============================================================
    # 配置刷新
    # ============================================================
    def reload_cfg(self):
        pending_rules = list(self.rules) if self._dirty else []

        disk_cfg = self._read_disk_config()

        merged = {}
        if isinstance(self.config, dict):
            merged.update(self.config)
        if isinstance(disk_cfg, dict):
            merged.update(disk_cfg)

        self.must_at_bot = bool(merged.get("must_at_bot", False))
        self.default_key = to_str(
            merged.get("default_key", "dd13536f0b5756d4")
        ).strip() or "dd13536f0b5756d4"

        self.cmd_main_name = to_str(merged.get("cmd_main", "鸡鸡娱乐系统")).strip() or "鸡鸡娱乐系统"
        self.cmd_admin_name = to_str(merged.get("cmd_admin", "管理员指令")).strip() or "管理员指令"
        self.cmd_list_name = to_str(merged.get("cmd_list", "表情包列表")).strip() or "表情包列表"
        self.cmd_greeting_morning_raw = to_str(merged.get("cmd_greeting_morning", "早安,早上好,起床")).strip() or "早安,早上好,起床"
        self.cmd_greeting_night_raw = to_str(merged.get("cmd_greeting_night", "晚安,睡觉,睡了")).strip() or "晚安,睡觉,睡了"
        self.cmd_minecraft_name = to_str(merged.get("cmd_minecraft", "MC版本")).strip() or "MC版本"
        self.cmd_mc_auto_name = to_str(merged.get("cmd_mc_auto", "MC自动检测")).strip() or "MC自动检测"
        self.cmd_mc_test_name = to_str(merged.get("cmd_mc_test", "MC测试推送")).strip() or "MC测试推送"
        self.cmd_add_name = to_str(merged.get("cmd_add", "添加表情")).strip() or "添加表情"
        self.cmd_del_name = to_str(merged.get("cmd_del", "删除规则")).strip() or "删除规则"
        self.cmd_save_name = to_str(merged.get("cmd_save", "保存规则")).strip() or "保存规则"
        self.cmd_word_add_name = to_str(merged.get("cmd_word_add", "加词")).strip() or "加词"
        self.cmd_word_del_name = to_str(merged.get("cmd_word_del", "删词")).strip() or "删词"
        self.cmd_word_list_name = to_str(merged.get("cmd_word_list", "词库列表")).strip() or "词库列表"
        self.cmd_enable_name = to_str(merged.get("cmd_enable", "娱乐系统开")).strip() or "娱乐系统开"
        self.cmd_disable_name = to_str(merged.get("cmd_disable", "娱乐系统关")).strip() or "娱乐系统关"
        self.cmd_view_admin_name = to_str(merged.get("cmd_view_admin", "查看管理员")).strip() or "查看管理员"
        self.cmd_refresh_admin_name = to_str(merged.get("cmd_refresh_admin", "刷新群管")).strip() or "刷新群管"
        self.cmd_add_admin_name = to_str(merged.get("cmd_add_admin", "加管理员")).strip() or "加管理员"
        self.cmd_del_admin_name = to_str(merged.get("cmd_del_admin", "删管理员")).strip() or "删管理员"
        self.cmd_admin_list_name = to_str(merged.get("cmd_admin_list", "管理员列表")).strip() or "管理员列表"
        self.cmd_enable_feature_name = to_str(merged.get("cmd_enable_feature", "开启功能")).strip() or "开启功能"
        self.cmd_disable_feature_name = to_str(merged.get("cmd_disable_feature", "关闭功能")).strip() or "关闭功能"
        self.cmd_feature_status_name = to_str(merged.get("cmd_feature_status", "功能状态")).strip() or "功能状态"
        self.cmd_greeting_rank_name = to_str(merged.get("cmd_greeting_rank", "打卡排行")).strip() or "打卡排行"
        self.cmd_greeting_stats_name = to_str(merged.get("cmd_greeting_stats", "打卡统计")).strip() or "打卡统计"
        self.cmd_job_add_name = to_str(merged.get("cmd_job_add_names", "添加工种")).strip() or "添加工种"
        self.cmd_job_del_name = to_str(merged.get("cmd_job_del_names", "删除工种")).strip() or "删除工种"
        self.cmd_mount_add_name = to_str(merged.get("cmd_mount_add_names", "添加坐骑")).strip() or "添加坐骑"
        self.cmd_mount_del_name = to_str(merged.get("cmd_mount_del_names", "删除坐骑,删坐骑")).strip() or "删除坐骑"

        self.cmd_must_at_bot_on_name = to_str(merged.get("cmd_must_at_bot_on", "必须艾特开")).strip() or "必须艾特开"
        self.cmd_must_at_bot_off_name = to_str(merged.get("cmd_must_at_bot_off", "必须艾特关")).strip() or "必须艾特关"
        self.cmd_must_at_bot_status_name = to_str(merged.get("cmd_must_at_bot_status", "必须艾特状态")).strip() or "必须艾特状态"

        gmb_raw = merged.get("group_must_at_bot", {})
        if isinstance(gmb_raw, dict):
            self.group_must_at_bot = {str(k): bool(v) for k, v in gmb_raw.items()}
        else:
            self.group_must_at_bot = {}

        self.cmd_meme_menu_name = to_str(merged.get("cmd_meme_menu", "接口系统")).strip() or "接口系统"
        self.cmd_meme_image_name = to_str(merged.get("cmd_meme_image", "图片接口")).strip() or "图片接口"
        self.cmd_meme_video_name = to_str(merged.get("cmd_meme_video", "视频接口")).strip() or "视频接口"
        self.cmd_mc_menu_name = to_str(merged.get("cmd_mc_menu", "MC系统")).strip() or "MC系统"
        self.cmd_greeting_menu_name = to_str(merged.get("cmd_greeting_menu", "打卡系统")).strip() or "打卡系统"
        self.cmd_checkin_menu_name = to_str(merged.get("cmd_checkin_menu", "签到系统")).strip() or "签到系统"
        self.cmd_daily_menu_name = to_str(merged.get("cmd_daily_menu", "每日系列")).strip() or "每日系列"

        self.cmd_chime_on_name = to_str(merged.get("cmd_chime_on", "整点报时开")).strip() or "整点报时开"
        self.cmd_chime_off_name = to_str(merged.get("cmd_chime_off", "整点报时关")).strip() or "整点报时关"
        self.cmd_chime_status_name = to_str(merged.get("cmd_chime_status", "整点报时状态")).strip() or "整点报时状态"
        self.cmd_chime_hours_name = to_str(merged.get("cmd_chime_hours", "整点报时时段")).strip() or "整点报时时段"
        self.cmd_chime_text_name = to_str(merged.get("cmd_chime_text", "整点报时文案")).strip() or "整点报时文案"
        self.cmd_chime_list_name = to_str(merged.get("cmd_chime_list", "整点报时列表")).strip() or "整点报时列表"
        self.cmd_chime_test_name = to_str(merged.get("cmd_chime_test", "整点报时测试")).strip() or "整点报时测试"

        self.cmd_daily_push_on_name = to_str(merged.get("cmd_daily_push_on", "状态推送开")).strip() or "状态推送开"
        self.cmd_daily_push_off_name = to_str(merged.get("cmd_daily_push_off", "状态推送关")).strip() or "状态推送关"
        self.cmd_daily_push_time_name = to_str(merged.get("cmd_daily_push_time", "状态推送间隔")).strip() or "状态推送间隔"
        self.cmd_daily_push_list_name = to_str(merged.get("cmd_daily_push_list", "状态推送列表")).strip() or "状态推送列表"

        self.cmd_blacklist_list_name = to_str(merged.get("cmd_blacklist_list", "黑名单列表")).strip() or "黑名单列表"

        # 群员管理：开关 / 黑名单 / 禁言时长 / 默认动作
        self.moderation_enable = bool(merged.get("moderation_enable", True))
        self._blacklist_raw = to_str(merged.get("member_blacklist", ""))
        self.member_blacklist = parse_blacklist(self._blacklist_raw)
        self.blacklist_default_action = (
            to_str(merged.get("blacklist_default_action", "ignore")).strip().lower()
            or "ignore"
        )
        if self.blacklist_default_action not in (ACTION_KICK, ACTION_MUTE, ACTION_IGNORE):
            self.blacklist_default_action = ACTION_IGNORE
        try:
            self.mute_duration = int(to_str(merged.get("mute_duration", "600")).strip() or "600")
        except Exception:
            self.mute_duration = 600
        if self.mute_duration < 60:
            self.mute_duration = 60

        self.cmd_daily_news_name = to_str(merged.get("cmd_daily_news", "每日读报")).strip() or "每日读报"
        self.cmd_daily_news_on_name = to_str(merged.get("cmd_daily_news_on", "读报推送开")).strip() or "读报推送开"
        self.cmd_daily_news_off_name = to_str(merged.get("cmd_daily_news_off", "读报推送关")).strip() or "读报推送关"
        self.cmd_daily_news_time_name = to_str(merged.get("cmd_daily_news_time", "读报推送时间")).strip() or "读报推送时间"
        self.cmd_daily_news_list_name = to_str(merged.get("cmd_daily_news_list", "读报推送列表")).strip() or "读报推送列表"

        if self.daily_news_module is not None:
            try:
                self.daily_news_module.reload(merged)
            except Exception:
                logger.exception("[apix-meme] 刷新每日读报模块失败")

        if self.status_push_module is not None:
            try:
                self.status_push_module.reload(merged)
            except Exception:
                logger.exception("[apix-meme] 刷新定时状态推送模块失败")

        status_raw = to_str(merged.get("cmd_status", "电脑状态")).strip() or "电脑状态"
        self.cmd_status_names = [s.strip() for s in status_raw.split(",") if s.strip()]
        if not self.cmd_status_names:
            self.cmd_status_names = ["电脑状态"]
        self.cmd_status_name = self.cmd_status_names[0]

        self.plugin_admins = [
            x.strip() for x in to_str(merged.get("plugin_admins", "")).splitlines()
            if x.strip()
        ]

        # 写操作令牌（可选）：留空时仅依赖同源 + 面板登录防护
        self.web_admin_token = to_str(merged.get("web_admin_token", "")).strip()

        self.minecraft_auto_groups = [
            x.strip() for x in to_str(merged.get("minecraft_auto_groups", "")).splitlines()
            if x.strip()
        ]
        # MC 测试推送的指定群：留空则回退到所有开启自动检测的群
        self.minecraft_test_groups = [
            x.strip() for x in to_str(merged.get("minecraft_test_groups", "")).splitlines()
            if x.strip()
        ]
        if self.minecraft_module is not None:
            merged_groups = list(dict.fromkeys(
                list(self.minecraft_module.auto_groups) + list(self.minecraft_auto_groups)
            ))
            self.minecraft_module.auto_groups = merged_groups
            self.minecraft_auto_groups = merged_groups

        self.feature_switch = {k: True for k in self.feature_switch.keys()}

        gfs_raw = merged.get("group_feature_switches", {})
        if isinstance(gfs_raw, dict):
            self.group_feature_switches = gfs_raw
        else:
            self.group_feature_switches = {}

        try:
            ttl = int(to_str(merged.get("group_admin_cache_ttl", "600")).strip() or "600")
        except Exception:
            ttl = 600
        if self.group_admin_module is not None:
            self.group_admin_module.set_ttl(ttl)

        self.group_mode = to_str(merged.get("group_mode", "off")).strip().lower() or "off"
        if self.group_mode not in ("off", "whitelist", "blacklist"):
            self.group_mode = "off"
        self.group_whitelist = parse_line_list(merged.get("group_whitelist", ""))
        self.group_blacklist = parse_line_list(merged.get("group_blacklist", ""))
        # ★ 全局群白名单：填了群号则只有这些群能用本插件；留空 = 不限制群聊
        self.allowed_groups = parse_gid_whitelist(merged.get("global_groups", ""))
        # ★ 电脑状态：单独群开关（填了则只有这些群能查电脑状态）
        self.status_groups = parse_gid_whitelist(merged.get("status_groups", ""))
        # ★ 电脑状态功能总开关：控制查询与定时推送
        #   兼容旧的 daily_status_push_enable：未配置新开关时沿用旧值，升级不丢推送
        if "status_enable" in merged:
            self.status_enable = bool(merged.get("status_enable"))
        else:
            self.status_enable = bool(merged.get("daily_status_push_enable", True))
        # 同步给定时推送模块（推送也受这个总开关控制）
        if self.status_push_module is not None:
            try:
                self.status_push_module.set_enable(self.status_enable)
            except Exception:
                logger.exception("[apix-meme] 同步电脑状态总开关失败")

        # ★ 接口系统：功能总开关 + 允许使用的群号（留空 = 不限制群聊）
        if "meme_enable" in merged:
            self.meme_enable = bool(merged.get("meme_enable"))
        else:
            self.meme_enable = True
        self.meme_groups = parse_gid_whitelist(merged.get("meme_groups", ""))
        _block_map = parse_group_block_keywords(merged.get("group_block_keywords", ""))
        self.group_block_map = _block_map if isinstance(_block_map, dict) else {}
        self.disabled_groups = self._parse_disabled_groups(merged.get("disabled_groups", ""))

        if self.fortune_module is not None:
            try:
                self.fortune_module.reload(merged)
            except Exception:
                logger.exception("[apix-meme] 刷新运势模块失败")
        if self.husband_module is not None:
            try:
                self.husband_module.reload(merged)
            except Exception:
                logger.exception("[apix-meme] 刷新老公模块失败")
        if self.luck_module is not None:
            try:
                self.luck_module.reload(merged)
            except Exception:
                logger.exception("[apix-meme] 刷新人品模块失败")
        if self.word_reply_module is not None:
            try:
                self.word_reply_module.reload(merged)
            except Exception:
                logger.exception("[apix-meme] 刷新词库模块失败")
        if self.greeting_module is not None:
            try:
                self.greeting_module.reload(merged)
            except Exception:
                logger.exception("[apix-meme] 刷新早安晚安模块失败")
        if self.minecraft_module is not None:
            try:
                self.minecraft_module.reload(merged)
            except Exception:
                logger.exception("[apix-meme] 刷新 MC 版本模块失败")
        if self.checkin_module is not None:
            try:
                self.checkin_module.reload(merged)
            except Exception:
                logger.exception("[apix-meme] 刷新签到模块失败")
        if self.hourly_chime_module is not None:
            try:
                self.hourly_chime_module.reload(merged)
            except Exception:
                logger.exception("[apix-meme] 刷新整点报时模块失败")

        api_list_raw = merged.get("api_list", [])
        disk_rules = []
        if isinstance(api_list_raw, list):
            for item in api_list_raw:
                if not isinstance(item, dict):
                    continue
                kw = to_str(item.get("keywords", "")).strip()
                url_template = to_str(item.get("url_template", "")).strip()
                param_count = to_str(item.get("param_count", "1")).strip() or "1"
                old_meme = to_str(item.get("meme", "")).strip()
                if not url_template and old_meme:
                    url_template = (
                        f"{self.BASE_URL}?meme={old_meme}"
                        f"&key={self.default_key}&pic={{pic}}"
                    )
                if url_template and "meme=&" in url_template and old_meme:
                    url_template = url_template.replace(
                        "meme=&", f"meme={old_meme}&"
                    )
                if not kw or not url_template:
                    continue
                keywords = [k.strip() for k in kw.split(",") if k.strip()]
                if not keywords:
                    continue
                disk_rules.append({
                    "keywords": keywords,
                    "url_template": url_template,
                    "param_count": param_count,
                    "media_type": to_str(item.get("media_type", "image")).strip().lower() or "image",
                    "json_field": to_str(item.get("json_field", "")).strip(),
                    "meme": old_meme,
                })
        elif isinstance(api_list_raw, str):
            for line in api_list_raw.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.rsplit(",", 1)]
                if len(parts) != 2 or not parts[0] or not parts[1]:
                    continue
                kw_str, meme_id = parts
                keywords = [k.strip() for k in kw_str.split(",") if k.strip()]
                if not keywords:
                    continue
                url_template = (
                    f"{self.BASE_URL}?meme={meme_id}"
                    f"&key={self.default_key}&pic={{pic}}"
                )
                disk_rules.append({
                    "keywords": keywords,
                    "url_template": url_template,
                    "param_count": "1",
                    "meme": meme_id,
                })

        if pending_rules:
            existing_keys = set()
            for r in disk_rules:
                existing_keys.add(",".join(r["keywords"]) + "|" + r.get("url_template", ""))
            for r in pending_rules:
                key = ",".join(r["keywords"]) + "|" + r.get("url_template", "")
                if key not in existing_keys:
                    disk_rules.append(r)
                    existing_keys.add(key)

        self.rules = disk_rules

        logger.info(
            f"[apix-meme] 已加载 {len(self.rules)} 条规则，"
            f"群模式={self.group_mode}，屏蔽群数={len(self.group_block_map)}，"
            f"关闭群数={len(self.disabled_groups)}，插件专属管理员={len(self.plugin_admins)}"
        )

    @staticmethod
    def _parse_disabled_groups(raw) -> list:
        if not raw:
            return []
        if isinstance(raw, list):
            return [str(x).strip() for x in raw if str(x).strip()]
        return [x.strip() for x in str(raw).splitlines() if x.strip()]

    # ============================================================
    # 保存配置
    # ============================================================
    def save_rules_to_config(self):
        try:
            new_list = []
            for rule in self.rules:
                new_list.append({
                    "__template_key": "meme_rule",
                    "keywords": ",".join(rule["keywords"]),
                    "url_template": rule.get("url_template", ""),
                    "param_count": rule.get("param_count", "1"),
                    "media_type": rule.get("media_type", "image") or "image",
                    "json_field": rule.get("json_field", "") or "",
                })

            block_lines = []
            if isinstance(self.group_block_map, dict):
                for gid, kws in self.group_block_map.items():
                    if kws:
                        block_lines.append(f"{gid}: {','.join(kws)}")
            block_text = "\n".join(block_lines)

            word_reply_list = []
            if self.word_reply_module is not None:
                for rule in self.word_reply_module.rules:
                    word_reply_list.append({
                        "__template_key": "word_reply_item",
                        "keywords": ",".join(rule["keywords"]),
                        "reply": rule["reply"],
                    })

            if self.minecraft_module is not None:
                self.minecraft_auto_groups = list(self.minecraft_module.auto_groups)

            existing = self._read_disk_config() or {}
            if not isinstance(existing, dict):
                existing = {}

            existing["default_key"] = self.default_key
            existing["must_at_bot"] = self.must_at_bot
            existing["api_list"] = new_list

            existing["cmd_main"] = self.cmd_main_name
            existing["cmd_admin"] = self.cmd_admin_name
            existing["cmd_list"] = self.cmd_list_name
            existing["cmd_greeting_morning"] = self.cmd_greeting_morning_raw
            existing["cmd_greeting_night"] = self.cmd_greeting_night_raw
            existing["cmd_minecraft"] = self.cmd_minecraft_name
            existing["cmd_mc_auto"] = self.cmd_mc_auto_name
            existing["cmd_mc_test"] = self.cmd_mc_test_name
            existing["cmd_add"] = self.cmd_add_name
            existing["cmd_del"] = self.cmd_del_name
            existing["cmd_save"] = self.cmd_save_name
            existing["cmd_status"] = ",".join(self.cmd_status_names)
            existing["cmd_word_add"] = self.cmd_word_add_name
            existing["cmd_word_del"] = self.cmd_word_del_name
            existing["cmd_word_list"] = self.cmd_word_list_name
            existing["cmd_enable"] = self.cmd_enable_name
            existing["cmd_disable"] = self.cmd_disable_name
            existing["cmd_view_admin"] = self.cmd_view_admin_name
            existing["cmd_refresh_admin"] = self.cmd_refresh_admin_name
            existing["cmd_add_admin"] = self.cmd_add_admin_name
            existing["cmd_del_admin"] = self.cmd_del_admin_name
            existing["cmd_admin_list"] = self.cmd_admin_list_name
            existing["cmd_enable_feature"] = self.cmd_enable_feature_name
            existing["cmd_disable_feature"] = self.cmd_disable_feature_name
            existing["cmd_feature_status"] = self.cmd_feature_status_name
            existing["cmd_greeting_rank"] = self.cmd_greeting_rank_name
            existing["cmd_greeting_stats"] = self.cmd_greeting_stats_name
            existing["cmd_job_add_names"] = self.cmd_job_add_name
            existing["cmd_job_del_names"] = self.cmd_job_del_name
            existing["cmd_mount_add_names"] = self.cmd_mount_add_name
            existing["cmd_mount_del_names"] = self.cmd_mount_del_name

            existing["cmd_must_at_bot_on"] = self.cmd_must_at_bot_on_name
            existing["cmd_must_at_bot_off"] = self.cmd_must_at_bot_off_name
            existing["cmd_must_at_bot_status"] = self.cmd_must_at_bot_status_name
            existing["group_must_at_bot"] = self.group_must_at_bot

            existing["cmd_meme_menu"] = self.cmd_meme_menu_name
            existing["cmd_meme_image"] = self.cmd_meme_image_name
            existing["cmd_meme_video"] = self.cmd_meme_video_name
            existing["cmd_mc_menu"] = self.cmd_mc_menu_name
            existing["cmd_greeting_menu"] = self.cmd_greeting_menu_name
            existing["cmd_checkin_menu"] = self.cmd_checkin_menu_name
            existing["cmd_daily_menu"] = self.cmd_daily_menu_name

            existing["cmd_chime_on"] = self.cmd_chime_on_name
            existing["cmd_chime_off"] = self.cmd_chime_off_name
            existing["cmd_chime_status"] = self.cmd_chime_status_name
            existing["cmd_chime_hours"] = self.cmd_chime_hours_name
            existing["cmd_chime_text"] = self.cmd_chime_text_name
            existing["cmd_chime_list"] = self.cmd_chime_list_name
            existing["cmd_chime_test"] = self.cmd_chime_test_name
            existing["cmd_daily_push_on"] = self.cmd_daily_push_on_name
            existing["cmd_daily_push_off"] = self.cmd_daily_push_off_name
            existing["cmd_daily_push_time"] = self.cmd_daily_push_time_name
            existing["cmd_daily_push_list"] = self.cmd_daily_push_list_name
            existing["cmd_blacklist_list"] = self.cmd_blacklist_list_name
            existing["member_blacklist"] = self._blacklist_raw
            existing["cmd_daily_news"] = self.cmd_daily_news_name
            existing["cmd_daily_news_on"] = self.cmd_daily_news_on_name
            existing["cmd_daily_news_off"] = self.cmd_daily_news_off_name
            existing["cmd_daily_news_time"] = self.cmd_daily_news_time_name
            existing["cmd_daily_news_list"] = self.cmd_daily_news_list_name

            existing["plugin_admins"] = "\n".join(self.plugin_admins)
            existing["web_admin_token"] = self.web_admin_token
            existing["feature_switch"] = {k: True for k in self.feature_switch.keys()}
            existing["group_feature_switches"] = self.group_feature_switches
            existing["group_admin_cache_ttl"] = str(
                self.group_admin_module.cache_ttl if self.group_admin_module else 600
            )
            existing["group_mode"] = self.group_mode
            existing["group_whitelist"] = "\n".join(self.group_whitelist)
            existing["group_blacklist"] = "\n".join(self.group_blacklist)
            existing["global_groups"] = ",".join(self.allowed_groups)
            existing["status_groups"] = ",".join(self.status_groups)
            existing["status_enable"] = self.status_enable
            existing["meme_enable"] = self.meme_enable
            existing["meme_groups"] = ",".join(self.meme_groups)
            if self.status_push_module is not None:
                # 定时推送群配置由后台填写，这里保持一致，避免内存与磁盘不同步
                existing.setdefault("daily_status_push_groups", "")
            existing["group_block_keywords"] = block_text
            existing["disabled_groups"] = "\n".join(self.disabled_groups)
            existing["word_reply_list"] = word_reply_list
            existing["minecraft_auto_groups"] = "\n".join(self.minecraft_auto_groups)
            existing["minecraft_test_groups"] = "\n".join(self.minecraft_test_groups)

            json.dumps(existing, ensure_ascii=False)

            ok = self._write_disk_config(existing)
            if not ok:
                return False

            self.config.update(existing)
            self._dirty = False
            logger.info(f"[apix-meme] 保存成功，共 {len(new_list)} 条表情包规则")
            return True
        except Exception:
            logger.exception("[apix-meme] 保存规则失败（未知错误）")
            return False

    # ============================================================
    # 判定辅助
    # ============================================================
    def _extract_multi_arg(self, text: str, cmd_name: str):
        variants = [cmd_name, f"/{cmd_name}"]
        for v in variants:
            if text.startswith(v + " "):
                rest = text[len(v) + 1:].strip()
                parts = rest.split(maxsplit=1)
                a1 = parts[0] if len(parts) >= 1 else ""
                a2 = parts[1] if len(parts) >= 2 else None
                return a1, a2
        return None, None

    def _extract_arg(self, text: str, cmd_name: str):
        n2 = f"/{cmd_name}"
        if text.startswith(n2 + " "):
            return text[len(n2) + 1:].strip()
        if text.startswith(cmd_name + " "):
            return text[len(cmd_name) + 1:].strip()
        return None

    def _is_disable_feature(self, text: str):
        return self._extract_multi_arg(text, self.cmd_disable_feature_name)

    def _is_enable_feature(self, text: str):
        return self._extract_multi_arg(text, self.cmd_enable_feature_name)

    def _is_feature_status_cmd(self, text: str):
        variants = [self.cmd_feature_status_name, f"/{self.cmd_feature_status_name}"]
        for v in variants:
            if text == v:
                return True, None
            if text.startswith(v + " "):
                tg = text[len(v) + 1:].strip()
                return True, tg
        return False, None

    def _is_greeting_rank_cmd(self, text: str) -> bool:
        n1 = self.cmd_greeting_rank_name
        return text in (n1, f"/{n1}")

    def _is_greeting_stats_cmd(self, text: str):
        """打卡统计：不跟参数查自己，可跟 @某人 / QQ号 查他人。"""
        n1 = self.cmd_greeting_stats_name
        n2 = f"/{n1}"
        if text == n1 or text == n2:
            return ("self",)
        for prefix in (n1 + " ", n2 + " "):
            if text.startswith(prefix):
                arg = text[len(prefix):].strip()
                if arg:
                    return ("target", arg)
                return ("self",)
        return None

    # ============================================================
    # 接口列表渲染（供图片/视频子菜单与接口列表指令共用）
    # ============================================================
    def _interface_media_of(self, rule: dict) -> str:
        """取规则的媒体类型：video 或 image（缺省视为 image）。"""
        media = str(rule.get("media_type", "") or "").strip().lower()
        return "video" if media == "video" else "image"

    def _render_interface_list(self, page: int, media: str = "") -> str:
        """
        渲染接口规则列表。返回空串表示没有可展示的规则。
        media: ""=全部 / "image"=只看图片 / "video"=只看视频
        """
        media = str(media or "").strip().lower()
        if media in ("image", "video"):
            pool = [r for r in self.rules if self._interface_media_of(r) == media]
            title = "图片接口列表" if media == "image" else "视频接口列表"
        else:
            pool = list(self.rules)
            media = ""
            title = "接口列表"

        total = len(pool)
        if total == 0:
            return ""

        page_size = self.PAGE_SIZE
        max_page = max(1, (total + page_size - 1) // page_size)
        page = max(1, min(int(page or 1), max_page))
        start = (page - 1) * page_size
        end = start + page_size

        lines = [f"======{title}（第 {page}/{max_page} 页，共 {total} 条）======"]
        for i, rule in enumerate(pool[start:end], start=start + 1):
            kw = " / ".join(rule["keywords"])
            pc = rule.get("param_count", "1")
            try:
                ptypes = detect_param_types(rule.get("url_template", ""), int(pc))
            except Exception:
                ptypes = ["any"] * int(pc) if str(pc).isdigit() else []

            if str(pc) == "0":
                type_desc = "无参数"
            else:
                labels = []
                for t in ptypes:
                    if t == "qq":
                        labels.append("QQ号或@")
                    elif t == "text":
                        labels.append("文本")
                    else:
                        labels.append("参数")
                type_desc = " + ".join(labels) if labels else "参数"

            # 参数说明后面再标注返回的是图片还是视频
            media_desc = "视频" if self._interface_media_of(rule) == "video" else "图片"
            lines.append(f"{i}. {kw}（{type_desc}｜{media_desc}）")

        return "\n".join(lines)

    def _interface_menu_hint(self, media: str) -> str:
        """翻页提示里用的指令名：按媒体类型取对应配置的指令。"""
        media = str(media or "").strip().lower()
        if media == "video":
            return getattr(self, "cmd_meme_video_name", "") or "视频接口"
        if media == "image":
            return getattr(self, "cmd_meme_image_name", "") or "图片接口"
        return self.cmd_list_name

    def _interface_usage_lines(self, media: str = "") -> list:
        """
        根据该分类下的实际规则，生成「怎么调用」的示例。
        全部是无参数接口时只提示发关键词；含带参数接口时才给参数示例。
        """
        media = str(media or "").strip().lower()
        if media in ("image", "video"):
            pool = [r for r in self.rules if self._interface_media_of(r) == media]
        else:
            pool = list(self.rules)

        def _first_kw(rules):
            for r in rules:
                kws = r.get("keywords") or []
                for k in kws:
                    if str(k).strip():
                        return str(k).strip()
            return ""

        # 按参数个数把规则分成两类，示例只从对应类别里取，避免文不对题
        no_param, with_param = [], []
        for r in pool:
            pc = str(r.get("param_count", "1") or "1").strip()
            if pc.isdigit() and int(pc) > 0:
                with_param.append(r)
            else:
                no_param.append(r)

        # 该分类下全都是无参数接口：只提示发关键词
        if not with_param:
            kw = _first_kw(no_param)
            if not kw:
                return []
            return [
                "发送「关键词」即可调用接口",
                f"例：{kw}",
            ]

        # 该分类下全都是带参数接口：给出参数示例
        if not no_param:
            lines = [
                "发送「关键词 + 参数」即可调用接口",
                "例：上香@某人",
                "例：鞭打 QQ号 QQ号",
                "例：报悲 任意文本",
            ]
            kw = _first_kw(with_param)
            if kw:
                lines.append(f"例：{kw}")
            return lines

        # 两者都有：分别举例说明
        lines = ["发送「关键词」调用无参数接口，发送「关键词 + 参数」调用带参数接口"]
        kw_np = _first_kw(no_param)
        if kw_np:
            lines.append(f"例：{kw_np}")
        kw_wp = _first_kw(with_param)
        if kw_wp:
            lines.append(f"例：{kw_wp} + 参数（如 @某人 或 QQ号）")
        return lines

    # ---------- 签到系统指令：统一走 checkin_module 的触发词匹配 ----------
    # 触发词由 checkin_trigger_names / checkin_rank_trigger_names /
    # checkin_info_trigger_names 配置，均支持英文逗号分隔多个。
    def _is_checkin_cmd(self, text: str) -> bool:
        if self.checkin_module is None:
            return False
        try:
            return self.checkin_module.match_trigger(text)
        except Exception:
            return False

    def _is_checkin_rank_cmd(self, text: str) -> bool:
        if self.checkin_module is None:
            return False
        try:
            return self.checkin_module.match_rank_trigger(text)
        except Exception:
            return False

    def _is_checkin_info_cmd(self, text: str):
        if self.checkin_module is None:
            return None
        try:
            return self.checkin_module.match_info_trigger(text)
        except Exception:
            return None

    def _checkin_first_trigger(self) -> str:
        """取签到统计的第一个触发词，用于提示文案。"""
        if self.checkin_module is None:
            return "签到统计"
        try:
            names = self.checkin_module.info_trigger_names
            if names:
                return str(names[0])
        except Exception:
            pass
        return "签到统计"

    def _match_status_cmd(self, text: str) -> bool:
        for name in self.cmd_status_names:
            if not name:
                continue
            if text == name or text == f"/{name}":
                return True
        return False

    def _is_main_menu(self, text: str) -> bool:
        return text in (self.cmd_main_name, f"/{self.cmd_main_name}")

    def _is_admin_menu(self, text: str) -> bool:
        return text in (self.cmd_admin_name, f"/{self.cmd_admin_name}")

    def _is_meme_menu(self, text: str) -> bool:
        """接口系统二级菜单入口，指令名支持英文逗号分隔多个。"""
        for n in self._split_names(self.cmd_meme_menu_name):
            if text == n or text == f"/{n}":
                return True
        return False

    def _is_mc_menu(self, text: str) -> bool:
        return text in (self.cmd_mc_menu_name, f"/{self.cmd_mc_menu_name}")

    def _is_greeting_menu(self, text: str) -> bool:
        return text in (self.cmd_greeting_menu_name, f"/{self.cmd_greeting_menu_name}")

    def _is_checkin_menu(self, text: str) -> bool:
        return text in (self.cmd_checkin_menu_name, f"/{self.cmd_checkin_menu_name}")

    def _is_daily_menu(self, text: str) -> bool:
        return text in (self.cmd_daily_menu_name, f"/{self.cmd_daily_menu_name}")

    def _is_meme_feature_menu(self, text: str):
        """
        接口系统三级子菜单识别。
        返回 (media, page)：media 为 "image" / "video" / ""（全部）。
        图片、视频各自使用可后台自定义的指令名（支持英文逗号分隔多个）。
        """
        groups = [
            ("image", self._split_names(getattr(self, "cmd_meme_image_name", "") or "图片接口")),
            ("video", self._split_names(getattr(self, "cmd_meme_video_name", "") or "视频接口")),
        ]
        for media, names in groups:
            for n in names:
                if not n:
                    continue
                if text == n or text == f"/{n}":
                    return (media, 1)
                for prefix in (n + " ", f"/{n} "):
                    if text.startswith(prefix):
                        arg = text[len(prefix):].strip()
                        if arg.isdigit():
                            return (media, int(arg))
                        return (media, 1)
        return None

    @staticmethod
    def _split_names(raw) -> list:
        """把「多个用英文逗号分隔」的指令名拆成列表。"""
        return [x.strip() for x in str(raw or "").split(",") if x.strip()]

    def _is_mc_version_menu(self, text: str) -> bool:
        return text in ("MC版本功能", "/MC版本功能")

    def _is_greeting_morning_menu(self, text: str) -> bool:
        return text in ("早安打卡", "/早安打卡")

    def _is_greeting_night_menu(self, text: str) -> bool:
        return text in ("晚安打卡", "/晚安打卡")

    def _is_greeting_rank_menu(self, text: str) -> bool:
        return text in ("打卡排行功能", "/打卡排行功能")

    def _is_checkin_signin_menu(self, text: str) -> bool:
        return text in ("签到指令", "/签到指令")

    def _is_checkin_query_menu(self, text: str) -> bool:
        return text in ("查询指令", "/查询指令")

    def _is_checkin_bank_menu(self, text: str) -> bool:
        return text in ("银行功能", "/银行功能")

    def _is_checkin_steal_menu(self, text: str) -> bool:
        return text in ("神偷功能", "/神偷功能")

    def _is_checkin_mount_menu(self, text: str) -> bool:
        return text in ("坐骑功能", "/坐骑功能")

    def _is_checkin_job_menu(self, text: str) -> bool:
        return text in ("打工功能", "/打工功能")

    def _is_meme_admin_menu(self, text: str) -> bool:
        return text in ("接口管理", "/接口管理", "表情管理", "/表情管理")

    def _is_word_admin_menu(self, text: str) -> bool:
        return text in ("词库管理", "/词库管理")

    def _is_checkin_admin_menu(self, text: str) -> bool:
        return text in ("签到管理", "/签到管理")

    def _is_status_admin_menu(self, text: str) -> bool:
        return text in ("状态管理", "/状态管理")

    def _is_switch_admin_menu(self, text: str) -> bool:
        return text in ("开关管理", "/开关管理")

    def _is_chime_admin_menu(self, text: str) -> bool:
        return text in ("整点管理", "/整点管理")

    def _is_must_at_admin_menu(self, text: str) -> bool:
        return text in ("艾特设置", "/艾特设置")

    def _is_super_admin_menu(self, text: str) -> bool:
        return text in ("超管设置", "/超管设置")

    def _is_list_menu(self, text: str):
        candidates = [self.cmd_list_name, f"/{self.cmd_list_name}"]
        for cmd in candidates:
            if text == cmd:
                return 1
            if text.startswith(cmd + " "):
                arg = text[len(cmd) + 1:].strip()
                if arg.isdigit():
                    return int(arg)
        return None

    def _is_minecraft_cmd(self, text: str):
        n1 = self.cmd_minecraft_name
        n2 = f"/{n1}"
        if text == n1 or text == n2:
            return (False,)
        for prefix in (n1 + " ", n2 + " "):
            if text.startswith(prefix):
                arg = text[len(prefix):].strip().lower()
                if arg in ("刷新", "更新", "refresh", "reload"):
                    return (True,)
                return (False,)
        return None

    def _is_mc_auto_cmd(self, text: str) -> bool:
        n1 = self.cmd_mc_auto_name
        return text in (n1, f"/{n1}")

    def _is_mc_test_cmd(self, text: str) -> bool:
        n1 = self.cmd_mc_test_name
        return text in (n1, f"/{n1}")

    def _is_enable_cmd(self, text: str) -> bool:
        return text in (self.cmd_enable_name, f"/{self.cmd_enable_name}")

    def _is_disable_cmd(self, text: str) -> bool:
        return text in (self.cmd_disable_name, f"/{self.cmd_disable_name}")

    def _is_view_admin_cmd(self, text: str) -> bool:
        return text in (self.cmd_view_admin_name, f"/{self.cmd_view_admin_name}")

    def _is_refresh_admin_cmd(self, text: str) -> bool:
        return text in (self.cmd_refresh_admin_name, f"/{self.cmd_refresh_admin_name}")

    def _is_admin_list_cmd(self, text: str) -> bool:
        return text in (self.cmd_admin_list_name, f"/{self.cmd_admin_list_name}")

    def _is_word_add(self, text: str):
        return self._extract_arg(text, self.cmd_word_add_name)

    def _is_word_del(self, text: str):
        return self._extract_arg(text, self.cmd_word_del_name)

    def _is_add_admin(self, text: str):
        return self._extract_arg(text, self.cmd_add_admin_name)

    def _is_del_admin(self, text: str):
        return self._extract_arg(text, self.cmd_del_admin_name)

    def _is_word_list(self, text: str) -> bool:
        return text in (self.cmd_word_list_name, f"/{self.cmd_word_list_name}")

    def _is_chime_on_cmd(self, text: str):
        n = self.cmd_chime_on_name
        if text == n or text == f"/{n}":
            return ("self",)
        for prefix in (n + " ", f"/{n} "):
            if text.startswith(prefix):
                arg = text[len(prefix):].strip()
                return ("target", arg) if arg else ("self",)
        return None

    def _is_chime_off_cmd(self, text: str):
        n = self.cmd_chime_off_name
        if text == n or text == f"/{n}":
            return ("self",)
        for prefix in (n + " ", f"/{n} "):
            if text.startswith(prefix):
                arg = text[len(prefix):].strip()
                return ("target", arg) if arg else ("self",)
        return None

    def _is_chime_status_cmd(self, text: str):
        n = self.cmd_chime_status_name
        if text == n or text == f"/{n}":
            return ("self",)
        for prefix in (n + " ", f"/{n} "):
            if text.startswith(prefix):
                arg = text[len(prefix):].strip()
                return ("target", arg) if arg else ("self",)
        return None

    def _is_chime_hours_cmd(self, text: str):
        n = self.cmd_chime_hours_name
        if text == n or text == f"/{n}":
            return ("query",)
        for prefix in (n + " ", f"/{n} "):
            if text.startswith(prefix):
                arg = text[len(prefix):].strip()
                return ("set", arg) if arg else ("query",)
        return None

    def _is_chime_text_cmd(self, text: str):
        n = self.cmd_chime_text_name
        if text == n or text == f"/{n}":
            return ("query",)
        for prefix in (n + " ", f"/{n} "):
            if text.startswith(prefix):
                arg = text[len(prefix):].strip()
                return ("set", arg) if arg else ("query",)
        return None

    def _is_chime_list_cmd(self, text: str) -> bool:
        n = self.cmd_chime_list_name
        return text in (n, f"/{n}")

    # ---------- 定时状态推送指令识别 ----------
    @staticmethod
    def _reshape_time_args(arg: str):
        """
        解析「时间」类参数，兼容两种顺序：
          状态推送间隔 60 123456   -> (123456, "60")
          状态推送间隔 123456 60   -> (123456, "60")
          状态推送间隔 60             -> ("", "60")
        返回的时间统一规范化为 HH:MM；无法识别为时间时返回空串，
        由调用方给出用法提示。若两个 token 都不是时间，则把第一个当群号、
        第二个当非法时间输入，以便提示用户格式错误。
        """
        from .core.status_push import parse_hhmm
        parts = str(arg or "").split()
        if len(parts) >= 2:
            first, second = parse_hhmm(parts[0]), parse_hhmm(parts[1])
            if first:
                return parts[1], first
            if second:
                return parts[0], second
            # 都不是合法时间：第一个当群号，时间留空触发格式提示
            return parts[0], ""
        if parts:
            only = parse_hhmm(parts[0])
            if only:
                return "", only
            return "", ""
        return "", ""

    def _is_daily_push_on_cmd(self, text: str):
        return self._extract_arg(text, self.cmd_daily_push_on_name)

    def _is_daily_push_off_cmd(self, text: str):
        return self._extract_arg(text, self.cmd_daily_push_off_name)

    def _is_daily_push_time_cmd(self, text: str):
        n = self.cmd_daily_push_time_name
        if text == n or text == f"/{n}":
            return ("self",)
        for prefix in (n + " ", f"/{n} "):
            if text.startswith(prefix):
                arg = text[len(prefix):].strip()
                if not arg:
                    return ("self",)
                gid, hhmm = self._reshape_time_args(arg)
                return ("set", gid, hhmm)
        return None

    def _is_daily_push_list_cmd(self, text: str) -> bool:
        n = self.cmd_daily_push_list_name
        return text in (n, f"/{n}")

    # ---------- 群员管理指令识别 ----------
    def _is_kick_cmd(self, text: str):
        n = self.cmd_kick_name
        if text == n or text == f"/{n}":
            return ""
        for prefix in (n + " ", f"/{n} "):
            if text.startswith(prefix):
                return text[len(prefix):].strip()
        return None

    def _is_mute_cmd(self, text: str):
        n = self.cmd_mute_name
        if text == n or text == f"/{n}":
            return ""
        for prefix in (n + " ", f"/{n} "):
            if text.startswith(prefix):
                return text[len(prefix):].strip()
        return None

    def _is_unmute_cmd(self, text: str):
        n = self.cmd_unmute_name
        if text == n or text == f"/{n}":
            return ""
        for prefix in (n + " ", f"/{n} "):
            if text.startswith(prefix):
                return text[len(prefix):].strip()
        return None

    def _is_blacklist_cmd(self, text: str):
        """拉黑成员 QQ号 [kick|mute|ignore]"""
        n = self.cmd_blacklist_name
        if text == n or text == f"/{n}":
            return ""
        for prefix in (n + " ", f"/{n} "):
            if text.startswith(prefix):
                return text[len(prefix):].strip()
        return None

    def _is_unblacklist_cmd(self, text: str):
        n = self.cmd_unblacklist_name
        if text == n or text == f"/{n}":
            return ""
        for prefix in (n + " ", f"/{n} "):
            if text.startswith(prefix):
                return text[len(prefix):].strip()
        return None

    def _is_blacklist_list_cmd(self, text: str) -> bool:
        n = self.cmd_blacklist_list_name
        return text in (n, f"/{n}")

    # ---------- 每日读报指令识别 ----------
    def _is_daily_news_cmd(self, text: str) -> bool:
        """手动读报指令，支持逗号分隔多个。"""
        for n in self._split_names(self.cmd_daily_news_name):
            if text == n or text == f"/{n}":
                return True
        return False

    def _is_daily_news_on_cmd(self, text: str):
        for n in self._split_names(self.cmd_daily_news_on_name):
            r = self._extract_arg(text, n)
            if r is not None:
                return r
            if text in (n, f"/{n}"):
                return ""
        return None

    def _is_daily_news_off_cmd(self, text: str):
        for n in self._split_names(self.cmd_daily_news_off_name):
            r = self._extract_arg(text, n)
            if r is not None:
                return r
            if text in (n, f"/{n}"):
                return ""
        return None

    def _is_daily_news_time_cmd(self, text: str):
        n = self.cmd_daily_news_time_name
        if text == n or text == f"/{n}":
            return ("self",)
        for prefix in (n + " ", f"/{n} "):
            if text.startswith(prefix):
                arg = text[len(prefix):].strip()
                if not arg:
                    return ("self",)
                gid, hhmm = self._reshape_time_args(arg)
                return ("set", gid, hhmm)
        return None

    def _is_daily_news_list_cmd(self, text: str) -> bool:
        n = self.cmd_daily_news_list_name
        return text in (n, f"/{n}")

    def _is_chime_test_cmd(self, text: str):
        n = self.cmd_chime_test_name
        if text == n or text == f"/{n}":
            return ("self",)
        for prefix in (n + " ", f"/{n} "):
            if text.startswith(prefix):
                arg = text[len(prefix):].strip()
                return ("target", arg) if arg else ("self",)
        return None

    def _is_must_at_on_cmd(self, text: str):
        n = self.cmd_must_at_bot_on_name
        if text == n or text == f"/{n}":
            return ("self",)
        for prefix in (n + " ", f"/{n} "):
            if text.startswith(prefix):
                arg = text[len(prefix):].strip()
                return ("target", arg) if arg else ("self",)
        return None

    def _is_must_at_off_cmd(self, text: str):
        n = self.cmd_must_at_bot_off_name
        if text == n or text == f"/{n}":
            return ("self",)
        for prefix in (n + " ", f"/{n} "):
            if text.startswith(prefix):
                arg = text[len(prefix):].strip()
                return ("target", arg) if arg else ("self",)
        return None

    def _is_must_at_status_cmd(self, text: str):
        n = self.cmd_must_at_bot_status_name
        if text == n or text == f"/{n}":
            return ("self",)
        for prefix in (n + " ", f"/{n} "):
            if text.startswith(prefix):
                arg = text[len(prefix):].strip()
                return ("target", arg) if arg else ("self",)
        return None

    # ============================================================
    # 菜单 wrapper
    # ============================================================
    def _build_main_menu(self): return build_main_menu(self)
    def _build_meme_menu(self): return build_meme_menu(self)
    def _build_mc_menu(self): return build_mc_menu(self)
    def _build_greeting_menu(self): return build_greeting_menu(self)
    def _build_checkin_menu(self): return build_checkin_menu(self)
    def _build_daily_menu(self): return build_daily_menu(self)
    def _build_admin_menu(self): return build_admin_menu(self)
    def _build_meme_feature_menu(self): return build_meme_feature_menu(self)
    def _build_mc_version_menu(self): return build_mc_version_menu(self)
    def _build_greeting_morning_menu(self): return build_greeting_morning_menu(self)
    def _build_greeting_night_menu(self): return build_greeting_night_menu(self)
    def _build_greeting_rank_menu(self): return build_greeting_rank_menu(self)
    def _build_checkin_signin_menu(self): return build_checkin_signin_menu(self)
    def _build_checkin_query_menu(self): return build_checkin_query_menu(self)
    def _build_checkin_bank_menu(self): return build_checkin_bank_menu(self)
    def _build_checkin_steal_menu(self): return build_checkin_steal_menu(self)
    def _build_checkin_mount_menu(self): return build_checkin_mount_menu(self)
    def _build_checkin_job_menu(self): return build_checkin_job_menu(self)
    def _build_meme_admin_menu(self): return build_meme_admin_menu(self)
    def _build_word_admin_menu(self): return build_word_admin_menu(self)
    def _build_checkin_admin_menu(self): return build_checkin_admin_menu(self)
    def _build_status_admin_menu(self): return build_status_admin_menu(self)
    def _build_switch_admin_menu(self): return build_switch_admin_menu(self)
    def _build_chime_admin_menu(self): return build_chime_admin_menu(self)

    def _is_news_admin_menu(self, text: str) -> bool:
        return text in ("读报管理", "/读报管理")

    def _build_news_admin_menu(self): return build_news_admin_menu(self)

    def _is_member_admin_menu(self, text: str) -> bool:
        return text in ("成员管理", "/成员管理")

    def _build_member_admin_menu(self): return build_member_admin_menu(self)
    def _build_must_at_admin_menu(self): return build_must_at_admin_menu(self)
    def _build_super_admin_menu(self): return build_super_admin_menu(self)

    async def _build_admin_list_text(self, event) -> str:
        lines = ["======管理员列表======"]
        lines.append("【AstrBot 全局管理员】")
        try:
            if event.is_admin():
                lines.append(f"  · {to_str(event.get_sender_id())}（你）")
            lines.append("  · 具体名单请在 AstrBot 管理面板查看")
        except Exception:
            lines.append("  · （读取失败）")
        lines.append("")
        lines.append("【插件专属管理员】")
        if self.plugin_admins:
            for a in self.plugin_admins:
                lines.append(f"  · {a}")
        else:
            lines.append("  · （无）")
        if self.group_admin_module is not None:
            try:
                info = await self.group_admin_module.get_group_admins(event)
                owner = info.get("owner", "")
                admins = info.get("admins", [])
                lines.append("")
                lines.append("【本群群主】")
                lines.append(f"  · {owner}" if owner else "  · （无）")
                lines.append("")
                lines.append("【本群管理员】")
                if admins:
                    for a in admins:
                        lines.append(f"  · {a}")
                else:
                    lines.append("  · （无）")
                ts = info.get("ts", 0)
                if ts:
                    age = int(time.time() - ts)
                    lines.append("")
                    lines.append(f"（缓存时间：{age} 秒前，输入「{self.cmd_refresh_admin_name}」可刷新）")
            except Exception:
                logger.exception("[apix-meme] 读取群管失败")
                lines.append("")
                lines.append("【本群群主/管理员】读取失败")
        else:
            lines.append("")
            lines.append("（群管识别模块未加载）")
        return "\n".join(lines)

    # ============================================================
    # 主入口
    # ============================================================
    @filter.event_message_type(EventMessageType.ALL)
    async def on_msg(self, event: AstrMessageEvent):
        GLOBAL_STATS["recv"] += 1
        try:
            await ensure_mc_checker(self)
        except Exception:
            logger.exception("[apix-meme] ensure_mc_checker 调用失败")
        try:
            await ensure_hourly_chime(self)
        except Exception:
            logger.exception("[apix-meme] ensure_hourly_chime 调用失败")
        try:
            await ensure_status_push(self)
        except Exception:
            logger.exception("[apix-meme] ensure_status_push 调用失败")
        try:
            await ensure_daily_news(self)
        except Exception:
            logger.exception("[apix-meme] ensure_daily_news 调用失败")

        if not self._dirty:
            self.reload_cfg()

        msg_str = to_str(event.message_str).strip()
        bot_id = to_str(event.get_self_id())
        sender_id = to_str(event.get_sender_id())
        if sender_id == bot_id:
            return

        # ★ 全局昵称缓存更新
        try:
            sender_name = get_sender_name(event)
            if sender_id and sender_name:
                self._nickname_cache.update(sender_id, sender_name)
        except Exception:
            logger.exception("[apix-meme] 更新昵称缓存失败")

        group_id = _get_group_id_from_event(event)

        # ============ 黑名单拦截（最先判定，早于所有功能）============
        if sender_id and self.moderation_enable and self.member_blacklist:
            bl_action = get_blacklist_action(
                self.member_blacklist, sender_id, self.blacklist_default_action
            )
            if bl_action:
                # 有权限才处罚；没权限时降级为「无视」，避免报错刷屏
                if bl_action in (ACTION_KICK, ACTION_MUTE) and self.moderation_module is not None:
                    can, role = await self.moderation_module.bot_can_moderate(event)
                    if can:
                        ok = await self.moderation_module.apply_action(
                            event, sender_id, bl_action, self.mute_duration
                        )
                        label = ACTION_LABEL.get(bl_action, bl_action)
                        logger.info(
                            f"[moderation] 黑名单成员 {sender_id} 发言触发{label}，结果 ok={ok}"
                        )
                    else:
                        logger.warning(
                            f"[moderation] 机器人无管理权限（{role}），"
                            f"黑名单成员 {sender_id} 的 {bl_action} 动作被跳过，仅无视"
                        )
                # 无论处罚是否成功，都不再响应其指令
                return

        # ============ 记录 UMO 供主动推送 ============
        if group_id:
            try:
                umo = get_event_umo(event)
                if umo:
                    logger.info(f"[apix-meme] 记录 UMO: 群 {group_id} -> {umo}")
                    if self.hourly_chime_module is not None:
                        self.hourly_chime_module.record_umo(group_id, umo)
                    if self.minecraft_module is not None:
                        self.minecraft_module.record_umo(group_id, umo)
                    if self.status_push_module is not None:
                        self.status_push_module.record_context(group_id, umo)
                    if self.daily_news_module is not None:
                        self.daily_news_module.record_context(group_id, umo)
                else:
                    logger.warning(f"[apix-meme] 群 {group_id} 未取到 UMO")
            except Exception:
                logger.exception("[apix-meme] 记录 UMO 失败")

        ac = self.admin_commands

        try:
            if self.checkin_module is not None and sender_id:
                self.checkin_module.record_speak(sender_id)
                self.checkin_module.settle_interest_if_needed()
        except Exception:
            pass

        # ============ 群总开关：关 ============
        if group_id and group_id in self.disabled_groups:
            if self._is_enable_cmd(msg_str):
                if not await self._check_admin(event):
                    yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                    GLOBAL_STATS["send"] += 1
                    return
                if ac is not None:
                    yield event.plain_result(ac.group_enable(group_id))
                else:
                    try:
                        self.disabled_groups.remove(group_id)
                        self.save_rules_to_config()
                        yield event.plain_result("✅本群娱乐系统已开启")
                    except Exception:
                        yield event.plain_result("❌操作失败")
                GLOBAL_STATS["send"] += 1
                return
            return

        if self._is_disable_cmd(msg_str):
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if ac is not None:
                yield event.plain_result(ac.group_disable(group_id))
            else:
                if group_id:
                    if group_id not in self.disabled_groups:
                        self.disabled_groups.append(group_id)
                        self.save_rules_to_config()
                        yield event.plain_result("✅本群娱乐系统已关闭")
                    else:
                        yield event.plain_result("本群已经处于关闭状态")
                else:
                    yield event.plain_result("私聊无法关闭")
            GLOBAL_STATS["send"] += 1
            return

        # ============ 管理员管理指令 ============
        arg_add_admin = self._is_add_admin(msg_str)
        if arg_add_admin is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if ac is None:
                yield event.plain_result("❌管理指令模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            yield event.plain_result(
                f"✅已添加插件专属管理员：{arg_add_admin}" if ac.add_plugin_admin(arg_add_admin)
                else "⚠️参数无效"
            )
            GLOBAL_STATS["send"] += 1
            return

        arg_del_admin = self._is_del_admin(msg_str)
        if arg_del_admin is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if ac is None:
                yield event.plain_result("❌管理指令模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            yield event.plain_result(
                f"✅已删除插件专属管理员：{arg_del_admin}" if ac.del_plugin_admin(arg_del_admin)
                else f"⚠️未找到该管理员：{arg_del_admin}"
            )
            GLOBAL_STATS["send"] += 1
            return

        if self._is_admin_list_cmd(msg_str):
            if ac is None:
                yield event.plain_result("❌管理指令模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            admins = ac.list_plugin_admins()
            if not admins:
                yield event.plain_result("======插件专属管理员======\n（无）")
            else:
                lines = [f"======插件专属管理员（{len(admins)} 人）======"]
                for i, a in enumerate(admins, start=1):
                    lines.append(f"{i}：{a}")
                yield event.plain_result("\n".join(lines))
            GLOBAL_STATS["send"] += 1
            return

        # ============ 单功能开关 ============
        arg_disable_feature, target_gid_dis = self._is_disable_feature(msg_str)
        if arg_disable_feature is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管/插件管理员可执行")
                GLOBAL_STATS["send"] += 1
                return
            if ac is None:
                yield event.plain_result("❌管理指令模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            cur_group_id = _get_group_id_from_event(event)
            yield event.plain_result(
                ac.disable_feature(arg_disable_feature, group_id=cur_group_id, target_group=target_gid_dis)
            )
            GLOBAL_STATS["send"] += 1
            return

        arg_enable_feature, target_gid_en = self._is_enable_feature(msg_str)
        if arg_enable_feature is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管/插件管理员可执行")
                GLOBAL_STATS["send"] += 1
                return
            if ac is None:
                yield event.plain_result("❌管理指令模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            cur_group_id = _get_group_id_from_event(event)
            yield event.plain_result(
                ac.enable_feature(arg_enable_feature, group_id=cur_group_id, target_group=target_gid_en)
            )
            GLOBAL_STATS["send"] += 1
            return

        is_status_cmd, target_gid_status = self._is_feature_status_cmd(msg_str)
        if is_status_cmd:
            if ac is None:
                yield event.plain_result("❌管理指令模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            cur_group_id = _get_group_id_from_event(event)
            yield event.plain_result(
                ac.feature_status_text(group_id=cur_group_id, target_group=target_gid_status)
            )
            GLOBAL_STATS["send"] += 1
            return

        # ============ 必须艾特机器人开关 ============
        must_at_on_args = self._is_must_at_on_cmd(msg_str)
        if must_at_on_args is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if ac is None:
                yield event.plain_result("❌管理指令模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            target_gid = group_id
            if must_at_on_args[0] == "target":
                target_gid = must_at_on_args[1]
            if not target_gid or not str(target_gid).isdigit():
                yield event.plain_result(
                    f"⚠️ 请在群聊中使用，或指定群号：{self.cmd_must_at_bot_on_name} 群号"
                )
                GLOBAL_STATS["send"] += 1
                return
            yield event.plain_result(ac.set_group_must_at_bot(target_gid, True))
            GLOBAL_STATS["send"] += 1
            return

        must_at_off_args = self._is_must_at_off_cmd(msg_str)
        if must_at_off_args is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if ac is None:
                yield event.plain_result("❌管理指令模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            target_gid = group_id
            if must_at_off_args[0] == "target":
                target_gid = must_at_off_args[1]
            if not target_gid or not str(target_gid).isdigit():
                yield event.plain_result(
                    f"⚠️ 请在群聊中使用，或指定群号：{self.cmd_must_at_bot_off_name} 群号"
                )
                GLOBAL_STATS["send"] += 1
                return
            yield event.plain_result(ac.set_group_must_at_bot(target_gid, False))
            GLOBAL_STATS["send"] += 1
            return

        must_at_status_args = self._is_must_at_status_cmd(msg_str)
        if must_at_status_args is not None:
            if ac is None:
                yield event.plain_result("❌管理指令模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            cur_group_id = _get_group_id_from_event(event)
            target_gid = None
            if must_at_status_args[0] == "target":
                target_gid = must_at_status_args[1]
            yield event.plain_result(
                ac.must_at_bot_status_text(group_id=cur_group_id, target_group=target_gid)
            )
            GLOBAL_STATS["send"] += 1
            return

        # ============ 全局「必须艾特机器人」拦截 ============
        if self._should_require_at(group_id):
            if not has_at_bot(event, bot_id):
                return

        # ============ 打卡排行榜 ============
        if self._is_greeting_rank_cmd(msg_str):
            if self.greeting_module is None:
                yield event.plain_result("❌ 早安晚安模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            try:
                yield event.plain_result(self.greeting_module.build_rank_text())
            except Exception:
                logger.exception("[apix-meme] 打卡排行失败")
                yield event.plain_result("❌ 查询失败")
            GLOBAL_STATS["send"] += 1
            return

        # ============ 打卡统计 ============
        gstats_args = self._is_greeting_stats_cmd(msg_str)
        if gstats_args is not None:
            if self.greeting_module is None:
                yield event.plain_result("❌ 早安晚安模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            try:
                if gstats_args[0] == "self":
                    target_uid = to_str(event.get_sender_id())
                    target_name = get_sender_name(event)
                    text = self.greeting_module.build_stats_text(target_uid, target_name)
                else:
                    raw = gstats_args[1]
                    target_uid = ""
                    try:
                        at_list = get_ats_from_msg(event)
                        if at_list:
                            target_uid = at_list[0]
                    except Exception:
                        pass
                    if not target_uid and raw.isdigit():
                        target_uid = raw
                    if not target_uid:
                        cleaned = raw.lstrip("@").strip()
                        if cleaned.isdigit():
                            target_uid = cleaned
                    if not target_uid:
                        yield event.plain_result(
                            f"⚠️ 请用「{self.cmd_greeting_stats_name} @某人」"
                            f"或「{self.cmd_greeting_stats_name} QQ号」查询"
                        )
                        GLOBAL_STATS["send"] += 1
                        return
                    text = self.greeting_module.build_stats_text(target_uid)
                yield event.plain_result(text)
            except Exception:
                logger.exception("[apix-meme] 打卡统计失败")
                yield event.plain_result("❌ 查询失败")
            GLOBAL_STATS["send"] += 1
            return

        # ============ 签到 ============
        if self._is_checkin_cmd(msg_str):
            if not self._is_group_feature_enable(group_id, "checkin"):
                yield event.plain_result("⚠️ 签到功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            if self.checkin_module is None:
                yield event.plain_result("❌ 签到模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            try:
                self.checkin_module.settle_interest_if_needed()
                text = self.checkin_module.do_checkin(event)
                if text:
                    yield event.plain_result(text)
                    GLOBAL_STATS["send"] += 1
            except Exception:
                logger.exception("[apix-meme] 签到失败")
                yield event.plain_result("❌ 签到失败")
            return

        # ============ 签到排行榜 ============
        if self._is_checkin_rank_cmd(msg_str):
            if self.checkin_module is None:
                yield event.plain_result("❌ 签到模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            try:
                yield event.plain_result(self.checkin_module.build_rank_text())
            except Exception:
                logger.exception("[apix-meme] 签到排行失败")
                yield event.plain_result("❌ 查询失败")
            GLOBAL_STATS["send"] += 1
            return

        # ============ 签到统计 ============
        info_args = self._is_checkin_info_cmd(msg_str)
        if info_args is not None:
            if self.checkin_module is None:
                yield event.plain_result("❌ 签到模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            try:
                if info_args[0] == "self":
                    target_uid = to_str(event.get_sender_id())
                    target_name = get_sender_name(event)
                    text = self.checkin_module.build_user_info_text(target_uid, target_name)
                else:
                    raw = info_args[1]
                    target_uid = ""
                    try:
                        at_list = get_ats_from_msg(event)
                        if at_list:
                            target_uid = at_list[0]
                    except Exception:
                        pass
                    if not target_uid and raw.isdigit():
                        target_uid = raw
                    if not target_uid:
                        cleaned = raw.lstrip("@").strip()
                        if cleaned.isdigit():
                            target_uid = cleaned
                    if not target_uid:
                        _hint = self._checkin_first_trigger()
                        yield event.plain_result(
                            f"⚠️ 请用「{_hint} @某人」或「{_hint} QQ号」查询"
                        )
                        GLOBAL_STATS["send"] += 1
                        return
                    text = self.checkin_module.build_user_info_text(target_uid)
                yield event.plain_result(text)
            except Exception:
                logger.exception("[apix-meme] 签到统计失败")
                yield event.plain_result("❌ 查询失败")
            GLOBAL_STATS["send"] += 1
            return

        # ============ 偷积分 ============
        steal_args = self.checkin_module.match_steal_trigger(msg_str) if self.checkin_module else None
        if steal_args is not None:
            if not self._is_group_feature_enable(group_id, "checkin"):
                yield event.plain_result("⚠️ 签到功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            if not self._is_group_feature_enable(group_id, "steal"):
                yield event.plain_result("⚠️ 偷积分功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            try:
                self.checkin_module.settle_interest_if_needed()
                target_raw = ""
                if steal_args[0] == "target":
                    target_raw = steal_args[1]
                    try:
                        at_list = get_ats_from_msg(event)
                        if at_list:
                            target_raw = at_list[0]
                    except Exception:
                        pass
                if not target_raw:
                    yield event.plain_result(
                        f"⚠️ 请指定要偷的人\n"
                        f"用法：「{self.checkin_module.steal_trigger_names[0]} @某人」"
                        f"或「{self.checkin_module.steal_trigger_names[0]} QQ号」"
                    )
                    GLOBAL_STATS["send"] += 1
                    return
                text = self.checkin_module.do_steal(event, target_raw)
                if text:
                    yield event.plain_result(text)
                    GLOBAL_STATS["send"] += 1
            except Exception:
                logger.exception("[apix-meme] 偷积分失败")
                yield event.plain_result("❌ 偷取失败")
            return

        # ============ 银行信息 ============
        if self.checkin_module is not None and self.checkin_module.match_bank_trigger(msg_str):
            if not self._is_group_feature_enable(group_id, "checkin"):
                yield event.plain_result("⚠️ 签到功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            if not self._is_group_feature_enable(group_id, "bank"):
                yield event.plain_result("⚠️ 银行功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            try:
                self.checkin_module.settle_interest_if_needed()
                text = self.checkin_module.do_bank_info(event)
                if text:
                    yield event.plain_result(text)
                    GLOBAL_STATS["send"] += 1
            except Exception:
                logger.exception("[apix-meme] 银行查询失败")
                yield event.plain_result("❌ 查询失败")
            return

        # ============ 存钱 ============
        deposit_args = self.checkin_module.match_deposit_trigger(msg_str) if self.checkin_module else None
        if deposit_args is not None:
            if not self._is_group_feature_enable(group_id, "checkin"):
                yield event.plain_result("⚠️ 签到功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            if not self._is_group_feature_enable(group_id, "bank"):
                yield event.plain_result("⚠️ 银行功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            try:
                self.checkin_module.settle_interest_if_needed()
                text = self.checkin_module.do_deposit(event, deposit_args[1])
                if text:
                    yield event.plain_result(text)
                    GLOBAL_STATS["send"] += 1
            except Exception:
                logger.exception("[apix-meme] 存钱失败")
                yield event.plain_result("❌ 操作失败")
            return

        # ============ 取钱 ============
        withdraw_args = self.checkin_module.match_withdraw_trigger(msg_str) if self.checkin_module else None
        if withdraw_args is not None:
            if not self._is_group_feature_enable(group_id, "checkin"):
                yield event.plain_result("⚠️ 签到功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            if not self._is_group_feature_enable(group_id, "bank"):
                yield event.plain_result("⚠️ 银行功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            try:
                self.checkin_module.settle_interest_if_needed()
                text = self.checkin_module.do_withdraw(event, withdraw_args[1])
                if text:
                    yield event.plain_result(text)
                    GLOBAL_STATS["send"] += 1
            except Exception:
                logger.exception("[apix-meme] 取钱失败")
                yield event.plain_result("❌ 操作失败")
            return

        # ============ 坐骑信息 ============
        mount_args = self.checkin_module.match_mount_trigger(msg_str) if self.checkin_module else None
        if mount_args is not None:
            if not self._is_group_feature_enable(group_id, "checkin"):
                yield event.plain_result("⚠️ 签到功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            if not self._is_group_feature_enable(group_id, "mount"):
                yield event.plain_result("⚠️ 坐骑功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            try:
                text = self.checkin_module.do_mount_info(event)
                if text:
                    yield event.plain_result(text)
                    GLOBAL_STATS["send"] += 1
            except Exception:
                logger.exception("[apix-meme] 坐骑查询失败")
                yield event.plain_result("❌ 查询失败")
            return

        # ============ 坐骑商店 ============
        if self.checkin_module is not None and self.checkin_module.match_mount_list_trigger(msg_str):
            if not self._is_group_feature_enable(group_id, "checkin"):
                yield event.plain_result("⚠️ 签到功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            if not self._is_group_feature_enable(group_id, "mount"):
                yield event.plain_result("⚠️ 坐骑功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            try:
                yield event.plain_result(self.checkin_module.do_mount_list())
                GLOBAL_STATS["send"] += 1
            except Exception:
                logger.exception("[apix-meme] 坐骑列表失败")
                yield event.plain_result("❌ 查询失败")
            return

        # ============ 购买坐骑 ============
        mount_buy_args = self.checkin_module.match_mount_buy_trigger(msg_str) if self.checkin_module else None
        if mount_buy_args is not None:
            if not self._is_group_feature_enable(group_id, "checkin"):
                yield event.plain_result("⚠️ 签到功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            try:
                text = self.checkin_module.do_mount_buy(event, mount_buy_args[1])
                if text:
                    yield event.plain_result(text)
                    GLOBAL_STATS["send"] += 1
            except Exception:
                logger.exception("[apix-meme] 购买坐骑失败")
                yield event.plain_result("❌ 操作失败")
            return

        # ============ 打工列表 ============
        if self.checkin_module is not None and self.checkin_module.match_job_info_trigger(msg_str):
            if not self._is_group_feature_enable(group_id, "checkin"):
                yield event.plain_result("⚠️ 签到功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            try:
                yield event.plain_result(self.checkin_module.do_job_list())
                GLOBAL_STATS["send"] += 1
            except Exception:
                logger.exception("[apix-meme] 打工列表失败")
                yield event.plain_result("❌ 查询失败")
            return

        # ============ 打工 ============
        job_args = self.checkin_module.match_job_trigger(msg_str) if self.checkin_module else None
        if job_args is not None:
            if not self._is_group_feature_enable(group_id, "checkin"):
                yield event.plain_result("⚠️ 签到功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            if not self._is_group_feature_enable(group_id, "job"):
                yield event.plain_result("⚠️ 打工功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            try:
                if job_args[0] == "list":
                    text = self.checkin_module.do_job_list()
                else:
                    text = self.checkin_module.do_job_work(event, job_args[1])
                if text:
                    yield event.plain_result(text)
                    GLOBAL_STATS["send"] += 1
            except Exception:
                logger.exception("[apix-meme] 打工失败")
                yield event.plain_result("❌ 操作失败")
            return

        # ============ 添加工种（管理员） ============
        job_add_arg = self.checkin_module.match_job_add_cmd(msg_str) if self.checkin_module else None
        if job_add_arg is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            try:
                yield event.plain_result(self.checkin_module.do_job_add(job_add_arg))
                try:
                    existing = self._read_disk_config() or {}
                    existing["job_list"] = [
                        {
                            "__template_key": "job_item",
                            "name": j["name"],
                            "duration_hours": str(j["duration_hours"]),
                            "reward_min": str(j["reward_min"]),
                            "reward_max": str(j["reward_max"]),
                        }
                        for j in self.checkin_module.job_list
                    ]
                    self._write_disk_config(existing)
                except Exception:
                    logger.exception("[apix-meme] 保存工种失败")
                GLOBAL_STATS["send"] += 1
            except Exception:
                logger.exception("[apix-meme] 添加工种失败")
                yield event.plain_result("❌ 操作失败")
            return

        # ============ 删除工种（管理员） ============
        job_del_arg = self.checkin_module.match_job_del_cmd(msg_str) if self.checkin_module else None
        if job_del_arg is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            try:
                yield event.plain_result(self.checkin_module.do_job_del(job_del_arg))
                try:
                    existing = self._read_disk_config() or {}
                    existing["job_list"] = [
                        {
                            "__template_key": "job_item",
                            "name": j["name"],
                            "duration_hours": str(j["duration_hours"]),
                            "reward_min": str(j["reward_min"]),
                            "reward_max": str(j["reward_max"]),
                        }
                        for j in self.checkin_module.job_list
                    ]
                    self._write_disk_config(existing)
                except Exception:
                    logger.exception("[apix-meme] 保存工种失败")
                GLOBAL_STATS["send"] += 1
            except Exception:
                logger.exception("[apix-meme] 删除工种失败")
                yield event.plain_result("❌ 操作失败")
            return

        # ============ 添加坐骑（管理员） ============
        mount_add_arg = self.checkin_module.match_mount_add_cmd(msg_str) if self.checkin_module else None
        if mount_add_arg is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            try:
                yield event.plain_result(self.checkin_module.do_mount_add(mount_add_arg))
                try:
                    existing = self._read_disk_config() or {}
                    existing["mount_list"] = [
                        {
                            "__template_key": "mount_item",
                            "name": m["name"],
                            "price": str(m["price"]),
                            "desc": m["desc"],
                        }
                        for m in self.checkin_module.mount_list
                    ]
                    self._write_disk_config(existing)
                except Exception:
                    logger.exception("[apix-meme] 保存坐骑失败")
                GLOBAL_STATS["send"] += 1
            except Exception:
                logger.exception("[apix-meme] 添加坐骑失败")
                yield event.plain_result("❌ 操作失败")
            return

        # ============ 删除坐骑（管理员） ============
        mount_del_arg = self.checkin_module.match_mount_del_cmd(msg_str) if self.checkin_module else None
        if mount_del_arg is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            try:
                yield event.plain_result(self.checkin_module.do_mount_del(mount_del_arg))
                try:
                    existing = self._read_disk_config() or {}
                    existing["mount_list"] = [
                        {
                            "__template_key": "mount_item",
                            "name": m["name"],
                            "price": str(m["price"]),
                            "desc": m["desc"],
                        }
                        for m in self.checkin_module.mount_list
                    ]
                    self._write_disk_config(existing)
                except Exception:
                    logger.exception("[apix-meme] 保存坐骑失败")
                GLOBAL_STATS["send"] += 1
            except Exception:
                logger.exception("[apix-meme] 删除坐骑失败")
                yield event.plain_result("❌ 操作失败")
            return

        # ============ 查看管理员 ============
        if self._is_view_admin_cmd(msg_str):
            try:
                yield event.plain_result(await self._build_admin_list_text(event))
            except Exception:
                logger.exception("[apix-meme] 查看管理员失败")
                yield event.plain_result("❌查询失败")
            GLOBAL_STATS["send"] += 1
            return

        # ============ 刷新群管 ============
        if self._is_refresh_admin_cmd(msg_str):
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if self.group_admin_module is None:
                yield event.plain_result("❌群管模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            try:
                info = await self.group_admin_module.get_group_admins(event, force=True)
                owner = info.get("owner", "")
                admins = info.get("admins", [])
                yield event.plain_result(
                    f"✅本群群管缓存已刷新\n群主：{owner or '（无）'}\n管理员：{len(admins)} 人"
                )
            except Exception:
                logger.exception("[apix-meme] 刷新群管失败")
                yield event.plain_result("❌刷新失败")
            GLOBAL_STATS["send"] += 1
            return

        # ============ 整点报时开 ============
        chime_on_args = self._is_chime_on_cmd(msg_str)
        if chime_on_args is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if self.hourly_chime_module is None:
                yield event.plain_result("❌ 整点报时模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            target_gid = group_id
            if chime_on_args[0] == "target":
                target_gid = chime_on_args[1]
            if not target_gid or not str(target_gid).isdigit():
                yield event.plain_result(f"⚠️ 请在群聊中使用，或指定群号：{self.cmd_chime_on_name} 群号")
                GLOBAL_STATS["send"] += 1
                return
            self.hourly_chime_module.set_group_on(target_gid, True)
            yield event.plain_result(
                f"✅ 已远程开启群【{target_gid}】的整点报时" if chime_on_args[0] == "target"
                else "✅ 本群整点报时已开启"
            )
            GLOBAL_STATS["send"] += 1
            return

        # ============ 整点报时关 ============
        chime_off_args = self._is_chime_off_cmd(msg_str)
        if chime_off_args is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if self.hourly_chime_module is None:
                yield event.plain_result("❌ 整点报时模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            target_gid = group_id
            if chime_off_args[0] == "target":
                target_gid = chime_off_args[1]
            if not target_gid or not str(target_gid).isdigit():
                yield event.plain_result(f"⚠️ 请在群聊中使用，或指定群号：{self.cmd_chime_off_name} 群号")
                GLOBAL_STATS["send"] += 1
                return
            self.hourly_chime_module.set_group_on(target_gid, False)
            yield event.plain_result(
                f"✅ 已远程关闭群【{target_gid}】的整点报时" if chime_off_args[0] == "target"
                else "✅ 本群整点报时已关闭"
            )
            GLOBAL_STATS["send"] += 1
            return

        # ============ 整点报时状态 ============
        chime_status_args = self._is_chime_status_cmd(msg_str)
        if chime_status_args is not None:
            if self.hourly_chime_module is None:
                yield event.plain_result("❌ 整点报时模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            target_gid = group_id
            if chime_status_args[0] == "target":
                target_gid = chime_status_args[1]
            if not target_gid:
                yield event.plain_result(f"⚠️ 请在群聊中使用，或指定群号：{self.cmd_chime_status_name} 群号")
                GLOBAL_STATS["send"] += 1
                return
            on = self.hourly_chime_module.is_group_on(target_gid)
            hours = self.hourly_chime_module.get_group_hours(target_gid)
            tpl = self.hourly_chime_module.get_group_template(target_gid) or self.hourly_chime_module.default_template
            umo = self.hourly_chime_module.get_umo(target_gid)
            yield event.plain_result("\n".join([
                f"======群 {target_gid} 整点报时状态======",
                f"开关：{'✅ 开启' if on else '❌ 关闭'}",
                f"报时整点：{'全部整点' if not hours else ', '.join(f'{h:02d}:00' for h in hours)}",
                f"文案：{tpl}",
                f"推送通道：{'✅ 已就绪' if umo else '⚠️ 尚未记录（本群发言一次后自动记录）'}",
            ]))
            GLOBAL_STATS["send"] += 1
            return

        # ============ 整点报时时段 ============
        chime_hours_args = self._is_chime_hours_cmd(msg_str)
        if chime_hours_args is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if self.hourly_chime_module is None:
                yield event.plain_result("❌ 整点报时模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            if not group_id:
                yield event.plain_result("⚠️ 请在群聊中使用该指令")
                GLOBAL_STATS["send"] += 1
                return
            if chime_hours_args[0] == "query":
                hours = self.hourly_chime_module.get_group_hours(group_id)
                if not hours:
                    yield event.plain_result(
                        f"本群当前报时时段：全部整点\n"
                        f"💡 用「{self.cmd_chime_hours_name} 8,12,20」改为指定整点\n"
                        f"💡 用「{self.cmd_chime_hours_name} all」恢复全部整点"
                    )
                else:
                    yield event.plain_result("本群当前报时时段：" + ", ".join(f"{h:02d}:00" for h in hours))
                GLOBAL_STATS["send"] += 1
                return
            raw = chime_hours_args[1]
            if raw.strip().lower() in ("all", "全部"):
                self.hourly_chime_module.set_group_hours(group_id, [])
                yield event.plain_result("✅ 已恢复为全部整点报时")
                GLOBAL_STATS["send"] += 1
                return
            parts = []
            for x in raw.replace("，", ",").split(","):
                x = x.strip()
                if x and x.isdigit():
                    parts.append(int(x))
            if not parts:
                yield event.plain_result(
                    f"⚠️ 参数无效\n用法：「{self.cmd_chime_hours_name} 8,12,20」\n"
                    f"或：「{self.cmd_chime_hours_name} all」恢复全部整点"
                )
                GLOBAL_STATS["send"] += 1
                return
            self.hourly_chime_module.set_group_hours(group_id, parts)
            yield event.plain_result("✅ 本群报时时段已更新：" + ", ".join(f"{h:02d}:00" for h in sorted(parts)))
            GLOBAL_STATS["send"] += 1
            return

        # ============ 整点报时文案 ============
        chime_text_args = self._is_chime_text_cmd(msg_str)
        if chime_text_args is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if self.hourly_chime_module is None:
                yield event.plain_result("❌ 整点报时模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            if not group_id:
                yield event.plain_result("⚠️ 请在群聊中使用该指令")
                GLOBAL_STATS["send"] += 1
                return
            if chime_text_args[0] == "query":
                tpl = self.hourly_chime_module.get_group_template(group_id) or self.hourly_chime_module.default_template
                yield event.plain_result(
                    f"本群当前报时文案：\n{tpl}\n\n"
                    f"💡 用「{self.cmd_chime_text_name} 自定义文案」修改\n"
                    f"💡 文案里可用 {{hour}} 占位符"
                )
                GLOBAL_STATS["send"] += 1
                return
            new_tpl = chime_text_args[1]
            if len(new_tpl) > 200:
                yield event.plain_result("⚠️ 文案过长（最多 200 字）")
                GLOBAL_STATS["send"] += 1
                return
            self.hourly_chime_module.set_group_template(group_id, new_tpl)
            yield event.plain_result(f"✅ 本群报时文案已更新：\n{new_tpl}")
            GLOBAL_STATS["send"] += 1
            return

        # ============ 整点报时列表 ============
        if self._is_chime_list_cmd(msg_str):
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if self.hourly_chime_module is None:
                yield event.plain_result("❌ 整点报时模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            items = self.hourly_chime_module.list_groups()
            if not items:
                yield event.plain_result("======整点报时列表======\n（暂无开启的群）")
                GLOBAL_STATS["send"] += 1
                return
            lines = [f"======整点报时列表（{len(items)} 个群）======"]
            for it in items:
                gid = it["group_id"]
                hours = it["hours"]
                hstr = "全部整点" if not hours else ", ".join(f"{h:02d}" for h in hours)
                umo = self.hourly_chime_module.get_umo(gid)
                umo_tag = "✅" if umo else "⚠️"
                lines.append(f"· 群 {gid} — {hstr} {umo_tag}")
            lines.append("")
            lines.append("💡 ✅=推送通道已就绪，⚠️=该群还没有发过消息")
            yield event.plain_result("\n".join(lines))
            GLOBAL_STATS["send"] += 1
            return

        # ============ 整点报时测试 ============
        chime_test_args = self._is_chime_test_cmd(msg_str)
        if chime_test_args is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if self.hourly_chime_module is None:
                yield event.plain_result("❌ 整点报时模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            target_gid = group_id
            if chime_test_args[0] == "target":
                target_gid = chime_test_args[1]
            if not target_gid or not str(target_gid).isdigit():
                yield event.plain_result(
                    f"⚠️ 请在群聊中使用，或指定群号：{self.cmd_chime_test_name} 群号"
                )
                GLOBAL_STATS["send"] += 1
                return
            is_on = self.hourly_chime_module.is_group_on(target_gid)
            current_umo = get_event_umo(event)
            if current_umo:
                self.hourly_chime_module.record_umo(target_gid, current_umo)
            umo = self.hourly_chime_module.get_umo(target_gid)
            text = self.hourly_chime_module.build_manual_text(target_gid)
            ok = await self._push_mc_notification(str(target_gid), text, umo=umo)
            if ok:
                if chime_test_args[0] == "target":
                    yield event.plain_result(
                        f"✅ 已向群【{target_gid}】手动推送一条整点报时\n"
                        f"💡 该群开关状态：{'已开启' if is_on else '未开启'}"
                    )
                else:
                    yield event.plain_result(
                        "✅ 手动触发成功，已向本群推送一条整点报时\n"
                        "💡 本次为测试推送，不影响正常整点判重"
                    )
            else:
                yield event.plain_result(
                    "❌ 推送失败\n"
                    "可能原因：\n"
                    "  · 本群尚未记录 UMO（请先在本群发一条普通消息）\n"
                    "  · 平台实例 ID 未识别\n"
                    "请查看后台日志 [push] 相关信息"
                )
            GLOBAL_STATS["send"] += 1
            return

        # ============ 状态推送开 ============
        push_on_arg = self._is_daily_push_on_cmd(msg_str)
        if push_on_arg is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if self.status_push_module is None:
                yield event.plain_result("❌ 定时状态推送模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            target_gid = push_on_arg or group_id
            if not target_gid or not str(target_gid).isdigit():
                yield event.plain_result(
                    f"⚠️ 请在群聊中使用，或指定群号：{self.cmd_daily_push_on_name} 群号"
                )
                GLOBAL_STATS["send"] += 1
                return
            self.status_push_module.set_group_on(target_gid, True)
            iv = self.status_push_module.get_group_interval(target_gid)
            custom = self.status_push_module.get_group_raw_interval(target_gid)
            scope = f"群【{target_gid}】" if push_on_arg else "本群"
            yield event.plain_result(
                f"✅ 已开启{scope}的定时状态推送\n"
                f"⏱ 推送间隔：每 {iv} 分钟一次{'（本群自定义）' if custom else '（跟随全局默认）'}\n"
                f"💡 可用「{self.cmd_daily_push_time_name} {iv}」单独改间隔（单位分钟）"
            )
            GLOBAL_STATS["send"] += 1
            return

        # ============ 状态推送关 ============
        push_off_arg = self._is_daily_push_off_cmd(msg_str)
        if push_off_arg is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if self.status_push_module is None:
                yield event.plain_result("❌ 定时状态推送模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            target_gid = push_off_arg or group_id
            if not target_gid or not str(target_gid).isdigit():
                yield event.plain_result(
                    f"⚠️ 请在群聊中使用，或指定群号：{self.cmd_daily_push_off_name} 群号"
                )
                GLOBAL_STATS["send"] += 1
                return
            self.status_push_module.set_group_on(target_gid, False)
            scope = f"群【{target_gid}】" if push_off_arg else "本群"
            yield event.plain_result(f"✅ 已关闭{scope}的定时状态推送")
            GLOBAL_STATS["send"] += 1
            return

        # ============ 状态推送间隔 ============
        push_time_args = self._is_daily_push_time_cmd(msg_str)
        if push_time_args is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if self.status_push_module is None:
                yield event.plain_result("❌ 定时状态推送模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            m = self.status_push_module

            if push_time_args[0] == "self":
                # 查询本群当前生效间隔
                target_gid = group_id
                if not target_gid:
                    yield event.plain_result(
                        f"⏱ 全局默认推送间隔：每 {m.default_interval} 分钟一次\n"
                        f"💡 在群里用「{self.cmd_daily_push_time_name} 60」设置本群间隔"
                    )
                    GLOBAL_STATS["send"] += 1
                    return
                eff = m.get_group_interval(target_gid)
                raw_iv = m.get_group_raw_interval(target_gid)
                on = m.is_group_on(target_gid)
                last = m.get_last_push(target_gid)
                last_at = str(last.get("at", "") or "（尚未推送过）")
                yield event.plain_result(
                    f"⏱ 群【{target_gid}】推送间隔：每 {eff} 分钟一次\n"
                    f"· 来源：{'本群自定义' if raw_iv else '跟随全局默认（' + str(m.default_interval) + ' 分钟）'}\n"
                    f"· 开关：{'已开启' if on else '未开启'}\n"
                    f"· 上次推送：{last_at}\n"
                    f"💡 设置：{self.cmd_daily_push_time_name} 60\n"
                    f"💡 指定群：{self.cmd_daily_push_time_name} 群号 60"
                )
                GLOBAL_STATS["send"] += 1
                return

            _, arg_gid, arg_time = push_time_args
            target_gid = arg_gid or group_id
            if not target_gid or not str(target_gid).isdigit():
                yield event.plain_result(
                    f"⚠️ 无法确定群号\n"
                    f"用法：{self.cmd_daily_push_time_name} 60\n"
                    f"或：{self.cmd_daily_push_time_name} 群号 60"
                )
                GLOBAL_STATS["send"] += 1
                return
            if not arg_time:
                yield event.plain_result(
                    f"⚠️ 间隔无效\n"
                    f"用法：{self.cmd_daily_push_time_name} 60（单位分钟，例如 60 = 每 60 分钟一次）"
                )
                GLOBAL_STATS["send"] += 1
                return
            if not m.set_group_interval(target_gid, arg_time):
                yield event.plain_result(
                    f"⚠️ 间隔无效：{arg_time}\n"
                    f"请填分钟数（正整数），例如 30、60、120；也支持「1小时」"
                )
                GLOBAL_STATS["send"] += 1
                return
            eff = m.get_group_interval(target_gid)
            on = m.is_group_on(target_gid)
            tip = "" if on else f"\n💡 该群推送开关还没开，用「{self.cmd_daily_push_on_name}」开启"
            yield event.plain_result(
                f"✅ 群【{target_gid}】推送间隔已设为每 {eff} 分钟一次{tip}"
            )
            GLOBAL_STATS["send"] += 1
            return

        # ============ 状态推送列表 ============
        if self._is_daily_push_list_cmd(msg_str):
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if self.status_push_module is None:
                yield event.plain_result("❌ 定时状态推送模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            m = self.status_push_module
            head = (
                f"======定时状态推送列表======\n"
                f"总开关：{'✅ 已开启' if m.enable else '❌ 未开启（后台配置中打开）'}\n"
                f"全局默认间隔：每 {m.default_interval} 分钟一次"
            )
            items = m.list_groups()
            if not items:
                yield event.plain_result(head + "\n（暂无开启推送的群）")
                GLOBAL_STATS["send"] += 1
                return
            lines = [head, f"已开启的群：{len(items)} 个"]
            for it in items:
                gid = it["group_id"]
                umo_tag = "✅" if m.get_umo(gid) else "⚠️"
                src = "自定义" if it["custom"] else "默认"
                last = m.get_last_push(gid)
                push_info = ""
                if last:
                    last_ts = float(last.get("ts", 0) or 0)
                    if last.get("init") or last_ts <= 0:
                        push_info = "（尚未推送）"
                    else:
                        push_info = f"（上次 {fmt_seconds(time.time() - last_ts)}前）"
                lines.append(
                    f"· 群 {gid} — 每 {it['interval']} 分钟（{src}）{umo_tag} {push_info}"
                )
            lines.append("")
            lines.append("💡 ✅=推送通道已就绪，⚠️=该群还没有发过消息")
            yield event.plain_result("\n".join(lines))
            GLOBAL_STATS["send"] += 1
            return

        # ============ 每日读报（手动） ============
        if self._is_daily_news_cmd(msg_str):
            yield event.plain_result("⏳ 正在获取今日读报，请稍候...")
            GLOBAL_STATS["send"] += 1
            image_sent = False
            try:
                from .core.daily_news import NEWS_API_IMAGE
                media_path, kind = await download_media(NEWS_API_IMAGE, expect="image")
                if kind == "image":
                    yield event.chain_result([Image.fromFileSystem(media_path)])
                    GLOBAL_STATS["send"] += 1
                    image_sent = True
            except Exception:
                logger.exception("[apix-meme] 手动读报：获取图片失败")

            if not image_sent:
                try:
                    text = await _fetch_daily_news_text()
                    if text:
                        yield event.plain_result(text)
                        GLOBAL_STATS["send"] += 1
                    else:
                        yield event.plain_result("❌ 获取读报失败，请稍后重试或查看后台日志")
                except Exception:
                    logger.exception("[apix-meme] 手动读报：文字回退失败")
                    yield event.plain_result("❌ 获取读报失败，请查看后台日志")
            return

        # ============ 读报推送开 ============
        news_on_arg = self._is_daily_news_on_cmd(msg_str)
        if news_on_arg is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if self.daily_news_module is None:
                yield event.plain_result("❌ 每日读报模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            target_gid = news_on_arg or group_id
            if not target_gid or not str(target_gid).isdigit():
                yield event.plain_result(
                    f"⚠️ 请在群聊中使用，或指定群号：{self.cmd_daily_news_on_name} 群号"
                )
                GLOBAL_STATS["send"] += 1
                return
            self.daily_news_module.set_group_on(target_gid, True)
            t = self.daily_news_module.get_group_time(target_gid)
            custom = self.daily_news_module.get_group_raw_time(target_gid)
            scope = f"群【{target_gid}】" if news_on_arg else "本群"
            yield event.plain_result(
                f"✅ 已开启{scope}的每日读报推送\n"
                f"🕐 推送时间：{t}{'（本群自定义）' if custom else '（跟随全局默认）'}\n"
                f"💡 可用「{self.cmd_daily_news_time_name} {t}」单独改时间"
            )
            GLOBAL_STATS["send"] += 1
            return

        # ============ 读报推送关 ============
        news_off_arg = self._is_daily_news_off_cmd(msg_str)
        if news_off_arg is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if self.daily_news_module is None:
                yield event.plain_result("❌ 每日读报模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            target_gid = news_off_arg or group_id
            if not target_gid or not str(target_gid).isdigit():
                yield event.plain_result(
                    f"⚠️ 请在群聊中使用，或指定群号：{self.cmd_daily_news_off_name} 群号"
                )
                GLOBAL_STATS["send"] += 1
                return
            self.daily_news_module.set_group_on(target_gid, False)
            scope = f"群【{target_gid}】" if news_off_arg else "本群"
            yield event.plain_result(f"✅ 已关闭{scope}的每日读报推送")
            GLOBAL_STATS["send"] += 1
            return

        # ============ 读报推送时间 ============
        news_time_args = self._is_daily_news_time_cmd(msg_str)
        if news_time_args is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if self.daily_news_module is None:
                yield event.plain_result("❌ 每日读报模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            m = self.daily_news_module

            if news_time_args[0] == "self":
                target_gid = group_id
                if not target_gid:
                    yield event.plain_result(
                        f"🕐 全局默认读报时间：{m.default_time}\n"
                        f"💡 在群里用「{self.cmd_daily_news_time_name} 08:00」设置本群时间"
                    )
                    GLOBAL_STATS["send"] += 1
                    return
                eff = m.get_group_time(target_gid)
                raw_t = m.get_group_raw_time(target_gid)
                on = m.is_group_on(target_gid)
                yield event.plain_result(
                    f"🕐 群【{target_gid}】读报时间：{eff}\n"
                    f"· 来源：{'本群自定义' if raw_t else '跟随全局默认（' + m.default_time + '）'}\n"
                    f"· 开关：{'已开启' if on else '未开启'}\n"
                    f"💡 设置：{self.cmd_daily_news_time_name} 08:00\n"
                    f"💡 指定群：{self.cmd_daily_news_time_name} 群号 08:00"
                )
                GLOBAL_STATS["send"] += 1
                return

            _, arg_gid, arg_time = news_time_args
            target_gid = arg_gid or group_id
            if not target_gid or not str(target_gid).isdigit():
                yield event.plain_result(
                    f"⚠️ 无法确定群号\n"
                    f"用法：{self.cmd_daily_news_time_name} 08:00\n"
                    f"或：{self.cmd_daily_news_time_name} 群号 08:00"
                )
                GLOBAL_STATS["send"] += 1
                return
            if not arg_time:
                yield event.plain_result(
                    f"⚠️ 时间格式无效\n"
                    f"用法：{self.cmd_daily_news_time_name} 08:00（24 小时制，支持整点或精确到分钟）"
                )
                GLOBAL_STATS["send"] += 1
                return
            if not m.set_group_time(target_gid, arg_time):
                yield event.plain_result(
                    f"⚠️ 时间格式无效：{arg_time}\n"
                    f"请用 24 小时制 HH:MM，例如 08:00、07:30、21:15"
                )
                GLOBAL_STATS["send"] += 1
                return
            eff = m.get_group_time(target_gid)
            on = m.is_group_on(target_gid)
            tip = "" if on else f"\n💡 该群推送开关还没开，用「{self.cmd_daily_news_on_name}」开启"
            yield event.plain_result(f"✅ 群【{target_gid}】读报时间已设为 {eff}{tip}")
            GLOBAL_STATS["send"] += 1
            return

        # ============ 读报推送列表 ============
        if self._is_daily_news_list_cmd(msg_str):
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if self.daily_news_module is None:
                yield event.plain_result("❌ 每日读报模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            m = self.daily_news_module
            head = (
                f"======每日读报推送列表======\n"
                f"总开关：{'✅ 已开启' if m.enable else '❌ 未开启（后台配置中打开）'}\n"
                f"全局默认时间：{m.default_time}"
            )
            items = m.list_groups()
            if not items:
                yield event.plain_result(head + "\n（暂无开启读报推送的群）")
                GLOBAL_STATS["send"] += 1
                return
            lines = [head, f"已开启的群：{len(items)} 个"]
            for it in items:
                gid = it["group_id"]
                umo_tag = "✅" if m.get_umo(gid) else "⚠️"
                src = "自定义" if it["custom"] else "默认"
                lines.append(f"· 群 {gid} — {it['time']}（{src}）{umo_tag}")
            lines.append("")
            lines.append("💡 ✅=推送通道已就绪，⚠️=该群还没有发过消息")
            yield event.plain_result("\n".join(lines))
            GLOBAL_STATS["send"] += 1
            return

        # ============ 群员管理：踢出 / 禁言 / 解除禁言 / 拉黑 ============
        def _resolve_target_uid(raw: str) -> str:
            """从参数里解析目标 QQ：支持 @某人 或 纯数字。"""
            uid = ""
            try:
                at_list = get_ats_from_msg(event)
                if at_list:
                    uid = str(at_list[0])
            except Exception:
                pass
            if not uid and raw:
                cleaned = str(raw).lstrip("@").strip().split()[0] if str(raw).strip() else ""
                if cleaned.isdigit():
                    uid = cleaned
            return uid

        def _moderation_guard():
            """返回 (ok, 错误提示)。"""
            if not self.moderation_enable:
                return False, "⚠️ 群员管理功能已关闭（后台「群员管理」中开启）"
            if self.moderation_module is None:
                return False, "❌ 群员管理模块未加载"
            if not group_id:
                return False, "⚠️ 请在群聊中使用该指令"
            return True, ""

        # ---------- 踢出群员 ----------
        kick_raw = self._is_kick_cmd(msg_str)
        if kick_raw is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管/插件专属管理员可执行")
                GLOBAL_STATS["send"] += 1
                return
            ok, err = _moderation_guard()
            if not ok:
                yield event.plain_result(err)
                GLOBAL_STATS["send"] += 1
                return
            target = _resolve_target_uid(kick_raw)
            if not target:
                yield event.plain_result(f"⚠️ 请指定要踢出的成员\n用法：{self.cmd_kick_name} @某人 或 {self.cmd_kick_name} QQ号")
                GLOBAL_STATS["send"] += 1
                return
            if target == to_str(bot_id):
                yield event.plain_result("⚠️ 不能踢出机器人自己")
                GLOBAL_STATS["send"] += 1
                return
            can, role = await self.moderation_module.bot_can_moderate(event)
            if not can:
                yield event.plain_result(self.moderation_module.no_permission_tip(role))
                GLOBAL_STATS["send"] += 1
                return
            done = await self.moderation_module.do_kick(event, target)
            yield event.plain_result(
                f"✅ 已踢出成员 {target}" if done
                else f"❌ 踢出失败，请检查机器人权限或查看后台日志"
            )
            GLOBAL_STATS["send"] += 1
            return

        # ---------- 禁言群员 ----------
        mute_raw = self._is_mute_cmd(msg_str)
        if mute_raw is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管/插件专属管理员可执行")
                GLOBAL_STATS["send"] += 1
                return
            ok, err = _moderation_guard()
            if not ok:
                yield event.plain_result(err)
                GLOBAL_STATS["send"] += 1
                return
            # 支持「@某人 600」或「@某人」（用后台默认时长）
            parts = str(mute_raw).split()
            target = _resolve_target_uid(parts[0] if parts else "")
            dur = self.mute_duration
            if len(parts) >= 2 and parts[1].isdigit():
                dur = int(parts[1])
            if not target:
                yield event.plain_result(
                    f"⚠️ 请指定要禁言的成员\n"
                    f"用法：{self.cmd_mute_name} @某人 [秒数]\n"
                    f"💡 不填秒数用后台默认值（当前 {self.mute_duration} 秒）"
                )
                GLOBAL_STATS["send"] += 1
                return
            if target == to_str(bot_id):
                yield event.plain_result("⚠️ 不能禁言机器人自己")
                GLOBAL_STATS["send"] += 1
                return
            can, role = await self.moderation_module.bot_can_moderate(event)
            if not can:
                yield event.plain_result(self.moderation_module.no_permission_tip(role))
                GLOBAL_STATS["send"] += 1
                return
            done = await self.moderation_module.do_mute(event, target, dur)
            yield event.plain_result(
                f"✅ 已禁言成员 {target}，时长 {dur} 秒" if done
                else "❌ 禁言失败，请检查机器人权限或查看后台日志"
            )
            GLOBAL_STATS["send"] += 1
            return

        # ---------- 解除禁言 ----------
        unmute_raw = self._is_unmute_cmd(msg_str)
        if unmute_raw is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管/插件专属管理员可执行")
                GLOBAL_STATS["send"] += 1
                return
            ok, err = _moderation_guard()
            if not ok:
                yield event.plain_result(err)
                GLOBAL_STATS["send"] += 1
                return
            target = _resolve_target_uid(unmute_raw)
            if not target:
                yield event.plain_result(f"⚠️ 用法：{self.cmd_unmute_name} @某人 或 {self.cmd_unmute_name} QQ号")
                GLOBAL_STATS["send"] += 1
                return
            can, role = await self.moderation_module.bot_can_moderate(event)
            if not can:
                yield event.plain_result(self.moderation_module.no_permission_tip(role))
                GLOBAL_STATS["send"] += 1
                return
            done = await self.moderation_module.do_unmute(event, target)
            yield event.plain_result(
                f"✅ 已解除成员 {target} 的禁言" if done else "❌ 解除禁言失败，请查看后台日志"
            )
            GLOBAL_STATS["send"] += 1
            return

        # ---------- 拉黑成员 ----------
        bl_raw = self._is_blacklist_cmd(msg_str)
        if bl_raw is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管/插件专属管理员可执行")
                GLOBAL_STATS["send"] += 1
                return
            if not self.moderation_enable:
                yield event.plain_result("⚠️ 群员管理功能已关闭（后台「群员管理」中开启）")
                GLOBAL_STATS["send"] += 1
                return
            parts = str(bl_raw).split()
            target = _resolve_target_uid(parts[0] if parts else "")
            act = parts[1].lower() if len(parts) >= 2 else ""
            if act not in (ACTION_KICK, ACTION_MUTE, ACTION_IGNORE):
                act = ""
            if not target:
                yield event.plain_result(
                    f"⚠️ 请指定要拉黑的成员\n"
                    f"用法：{self.cmd_blacklist_name} @某人 [kick|mute|ignore]\n"
                    f"　 kick=再发言就踢出　mute=再发言就禁言　ignore=无视其指令\n"
                    f"💡 不填动作则用后台默认（当前 {ACTION_LABEL.get(self.blacklist_default_action, self.blacklist_default_action)}）"
                )
                GLOBAL_STATS["send"] += 1
                return
            if target == to_str(bot_id):
                yield event.plain_result("⚠️ 不能拉黑机器人自己")
                GLOBAL_STATS["send"] += 1
                return

            self._blacklist_raw = upsert_blacklist(self._blacklist_raw, target, act or self.blacklist_default_action)
            self.member_blacklist = parse_blacklist(self._blacklist_raw)
            self.save_rules_to_config()

            eff = self.member_blacklist.get(target, self.blacklist_default_action)
            eff_label = ACTION_LABEL.get(eff, eff)
            yield event.plain_result(
                f"✅ 已拉黑成员 {target}\n"
                f"· 后续发言处理：{eff_label}\n"
                f"💡 可用「{self.cmd_unblacklist_name} {target}」解除"
            )
            GLOBAL_STATS["send"] += 1
            return

        # ---------- 解除拉黑 ----------
        ubl_raw = self._is_unblacklist_cmd(msg_str)
        if ubl_raw is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管/插件专属管理员可执行")
                GLOBAL_STATS["send"] += 1
                return
            target = _resolve_target_uid(ubl_raw)
            if not target:
                yield event.plain_result(f"⚠️ 用法：{self.cmd_unblacklist_name} @某人 或 {self.cmd_unblacklist_name} QQ号")
                GLOBAL_STATS["send"] += 1
                return
            new_raw, removed = remove_blacklist(self._blacklist_raw, target)
            if removed:
                self._blacklist_raw = new_raw
                self.member_blacklist = parse_blacklist(self._blacklist_raw)
                self.save_rules_to_config()
            yield event.plain_result(
                f"✅ 已解除成员 {target} 的拉黑" if removed
                else f"⚠️ 成员 {target} 不在黑名单里"
            )
            GLOBAL_STATS["send"] += 1
            return

        # ---------- 黑名单列表 ----------
        if self._is_blacklist_list_cmd(msg_str):
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管/插件专属管理员可执行")
                GLOBAL_STATS["send"] += 1
                return
            head = (
                "======成员黑名单======\n"
                f"功能开关：{'✅ 已开启' if self.moderation_enable else '❌ 已关闭'}\n"
                f"默认动作：{ACTION_LABEL.get(self.blacklist_default_action, self.blacklist_default_action)}\n"
                f"禁言时长：{self.mute_duration} 秒"
            )
            if not self.member_blacklist:
                yield event.plain_result(head + "\n（黑名单为空）")
                GLOBAL_STATS["send"] += 1
                return
            lines = [head, f"已拉黑：{len(self.member_blacklist)} 人"]
            for uid, act in sorted(self.member_blacklist.items()):
                a = act or self.blacklist_default_action
                lines.append(f"· {uid} — {ACTION_LABEL.get(a, a)}")
            lines.append("")
            lines.append(f"💡 解除：{self.cmd_unblacklist_name} QQ号")
            yield event.plain_result("\n".join(lines))
            GLOBAL_STATS["send"] += 1
            return

        # ============ MC 自动检测开关 ============
        if self._is_mc_auto_cmd(msg_str):
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if not group_id:
                yield event.plain_result("⚠️请在群聊中使用该指令")
                GLOBAL_STATS["send"] += 1
                return
            if self.minecraft_module is None:
                yield event.plain_result("❌ Minecraft 版本模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            if not self._is_group_feature_enable(group_id, "minecraft"):
                yield event.plain_result("⚠️ Minecraft 版本检测功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            current = self.minecraft_module.is_group_auto(group_id)
            new_state = not current
            self.minecraft_module.set_group_auto(group_id, new_state)
            try:
                self.minecraft_auto_groups = list(self.minecraft_module.auto_groups)
                self.save_rules_to_config()
            except Exception:
                logger.exception("[apix-meme] 保存 MC 自动检测群列表失败")
            if new_state:
                yield event.plain_result(
                    "✅ 本群已开启 Minecraft 版本自动检测\n"
                    f"📢 检测到新版本时会推送到本群\n"
                    f"⚙️ 检测间隔：{self.minecraft_module.interval} 秒\n"
                    f"💡 再次发送「{self.cmd_mc_auto_name}」可关闭"
                )
            else:
                yield event.plain_result("✅ 本群已关闭 Minecraft 版本自动检测")
            GLOBAL_STATS["send"] += 1
            return

        # ============ MC 测试推送 ============
        if self._is_mc_test_cmd(msg_str):
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if self.minecraft_module is None:
                yield event.plain_result("❌ Minecraft 版本模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            if not self._is_group_feature_enable(group_id, "minecraft"):
                yield event.plain_result("⚠️ Minecraft 版本检测功能已关闭")
                GLOBAL_STATS["send"] += 1
                return

            # 推送目标：优先用「MC测试推送指定群」后台配置，未配置则回退到所有开启自动检测的群
            test_groups = list(getattr(self, "minecraft_test_groups", []) or [])
            if test_groups:
                groups = test_groups
                scope_note = "（来自后台「MC测试推送指定群」配置）"
            else:
                groups = list(self.minecraft_module.auto_groups)
                scope_note = "（未配置指定群，默认推送给所有开启自动检测的群）"

            if not groups:
                yield event.plain_result(
                    "⚠️ 没有可推送的群\n"
                    f"💡 在后台「MC测试推送指定群」里填群号（一行一个），"
                    f"或先在本群发「{self.cmd_mc_auto_name}」开启自动检测"
                )
                GLOBAL_STATS["send"] += 1
                return

            yield event.plain_result(
                f"⏳ 正在拉取最新版本并推送到 {len(groups)} 个群，请稍候...\n{scope_note}"
            )
            GLOBAL_STATS["send"] += 1

            try:
                result = await self.minecraft_module.check_all(force=True, include_bedrock=True)
                text = self.minecraft_module.format_text(result, include_bedrock=True)
            except Exception:
                logger.exception("[apix-meme] MC 测试推送：拉取版本失败")
                yield event.plain_result("❌ 拉取版本失败，请查看后台日志")
                GLOBAL_STATS["send"] += 1
                return

            push_text = "📢 【MC版本测试推送】\n\n" + text
            ok_count = 0
            fail_count = 0
            fail_groups = []
            for gid in groups:
                try:
                    umo = self.minecraft_module.get_umo(gid)
                    ok = await self._push_mc_notification(str(gid), push_text, umo=umo)
                    if ok:
                        ok_count += 1
                    else:
                        fail_count += 1
                        fail_groups.append(str(gid))
                except Exception:
                    logger.exception(f"[apix-meme] MC 测试推送：群 {gid} 推送异常")
                    fail_count += 1
                    fail_groups.append(str(gid))

            lines = [
                "======MC 测试推送结果======",
                f"✅ 成功：{ok_count} 个群",
                f"❌ 失败：{fail_count} 个群",
            ]
            if fail_groups:
                lines.append("")
                lines.append("失败群号：")
                for g in fail_groups:
                    lines.append(f"  · {g}")
            lines.append("")
            lines.append(f"💡 推送范围：{scope_note}")
            if test_groups:
                lines.append(f"💡 共 {len(groups)} 个群（后台指定）")
            else:
                lines.append(f"💡 共 {len(groups)} 个群开启了自动检测")
            yield event.plain_result("\n".join(lines))
            GLOBAL_STATS["send"] += 1
            return

        # ============ MC 版本手动查询 ============
        mc_args = self._is_minecraft_cmd(msg_str)
        if mc_args is not None:
            if not self._is_group_feature_enable(group_id, "minecraft"):
                yield event.plain_result("⚠️ Minecraft 版本检测功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            if self.minecraft_module is None:
                yield event.plain_result("❌ Minecraft 版本模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            force = mc_args[0]
            try:
                result = await self.minecraft_module.check_all(force=force, include_bedrock=True)
                yield event.plain_result(self.minecraft_module.format_text(result, include_bedrock=True))
            except Exception:
                logger.exception("[apix-meme] MC 版本查询失败")
                yield event.plain_result("❌ 查询失败，请稍后重试")
            GLOBAL_STATS["send"] += 1
            return

        # ============ 群白名单（不填 = 不限制群聊）============
        if self.allowed_groups:
            if not group_allowed(group_id, self.allowed_groups):
                return
        elif not is_group_allowed(group_id, self.group_mode, self.group_whitelist, self.group_blacklist):
            # 未填新白名单时，回退到旧的黑/白名单逻辑
            return

        # ============ 运势 ============
        if (
            self._is_group_feature_enable(group_id, "fortune")
            and self.fortune_module is not None
            and self.fortune_module.match_trigger(msg_str)
            and self.fortune_module._is_group_allowed(group_id)
        ):
            try:
                text = self.fortune_module.get_today_text(event)
                if text:
                    yield event.plain_result(text)
                    GLOBAL_STATS["send"] += 1
            except Exception:
                logger.exception("[apix-meme] 运势处理失败")
            return

        # ============ 老公 ============
        if (
            self._is_group_feature_enable(group_id, "husband")
            and self.husband_module is not None
            and self.husband_module.match_trigger(msg_str)
            and self.husband_module._is_group_allowed(group_id)
        ):
            try:
                text, avatar_path = await self.husband_module.get_today_result(event)
                lines = text.splitlines() if text else []
                qq_line_idx = -1
                for i, line in enumerate(lines):
                    if "QQ：" in line or "QQ:" in line:
                        qq_line_idx = i
                        break
                chain = []
                if qq_line_idx == -1:
                    if text:
                        chain.append(Plain(text))
                    if avatar_path:
                        chain.append(Image.fromFileSystem(avatar_path))
                else:
                    upper = "\n".join(lines[:qq_line_idx + 1])
                    lower = "\n".join(lines[qq_line_idx + 1:])
                    if upper:
                        chain.append(Plain(upper))
                    if avatar_path:
                        chain.append(Image.fromFileSystem(avatar_path))
                    if lower.strip():
                        chain.append(Plain(lower))
                if chain:
                    yield event.chain_result(chain)
                    GLOBAL_STATS["send"] += 1
            except Exception:
                logger.exception("[apix-meme] 老公处理失败")
            return

        # ============ 人品 ============
        if (
            self._is_group_feature_enable(group_id, "luck")
            and self.luck_module is not None
            and self.luck_module.match_trigger(msg_str)
            and self.luck_module._is_group_allowed(group_id)
        ):
            try:
                text = self.luck_module.get_today_text(event)
                if text:
                    yield event.plain_result(text)
                    GLOBAL_STATS["send"] += 1
            except Exception:
                logger.exception("[apix-meme] 人品处理失败")
            return

        # ============ 词库回复 ============
        if self._is_group_feature_enable(group_id, "word_reply") and self.word_reply_module is not None:
            rule, _kw = self.word_reply_module.match(msg_str, group_id)
            if rule:
                reply = self.word_reply_module.get_reply(rule)
                if reply:
                    yield event.plain_result(reply)
                    GLOBAL_STATS["send"] += 1
                return

        # ============ 词库管理指令 ============
        args_add = self._is_word_add(msg_str)
        if args_add is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if ac is None:
                yield event.plain_result("❌管理指令模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            yield event.plain_result(ac.word_add(args_add))
            GLOBAL_STATS["send"] += 1
            return

        args_del = self._is_word_del(msg_str)
        if args_del is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if ac is None:
                yield event.plain_result("❌管理指令模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            yield event.plain_result(ac.word_del(args_del))
            GLOBAL_STATS["send"] += 1
            return

        if self._is_word_list(msg_str):
            if ac is None:
                yield event.plain_result("❌管理指令模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            yield event.plain_result(ac.word_list_text())
            GLOBAL_STATS["send"] += 1
            return

        # ============ 表情包管理指令 ============
        arg_add = self._extract_arg(msg_str, self.cmd_add_name)
        if arg_add is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if ac is None:
                yield event.plain_result("❌管理指令模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            yield event.plain_result(ac.meme_add(arg_add))
            GLOBAL_STATS["send"] += 1
            return

        arg_del = self._extract_arg(msg_str, self.cmd_del_name)
        if arg_del is not None:
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if ac is None:
                yield event.plain_result("❌管理指令模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            yield event.plain_result(ac.meme_del(arg_del))
            GLOBAL_STATS["send"] += 1
            return

        if msg_str in (self.cmd_save_name, f"/{self.cmd_save_name}"):
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            if ac is None:
                yield event.plain_result("❌管理指令模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            yield event.plain_result(ac.meme_save())
            GLOBAL_STATS["send"] += 1
            return

        # ============ 电脑状态 ============
        if self._match_status_cmd(msg_str):
            if not await self._check_admin(event):
                yield event.plain_result("⚠️仅管理员/群主/群管可执行")
                GLOBAL_STATS["send"] += 1
                return
            # ★ 电脑状态功能总开关（同时控制定时推送）
            if not self.status_enable:
                yield event.plain_result("⚠️ 电脑状态功能已关闭（后台「电脑状态」中开启）")
                GLOBAL_STATS["send"] += 1
                return
            # ★ 本群功能开关（默认开启，可用「关闭功能 电脑状态」关闭本群）
            if not self._is_group_feature_enable(group_id, "status"):
                yield event.plain_result("⚠️ 本群电脑状态功能已关闭")
                GLOBAL_STATS["send"] += 1
                return
            # ★ 电脑状态单独群开关：填了群号则只有这些群可查
            if not group_allowed(group_id, self.status_groups):
                yield event.plain_result("⚠️ 本群未开启电脑状态查询")
                GLOBAL_STATS["send"] += 1
                return
            try:
                yield event.plain_result(
                    collect_runtime_status(event, cfg=self._read_disk_config() or {})
                )
            except Exception:
                logger.exception("[apix-meme] 电脑状态查询失败")
                yield event.plain_result("❌ 查询失败")
            GLOBAL_STATS["send"] += 1
            return

        # ================================================================
        # ★★★ 菜单区 ★★★
        # 顺序：三级子菜单 → 二级子菜单 → 主菜单
        # ================================================================

        # ---- 打卡系统 · 三级子菜单 ----
        if self._is_greeting_morning_menu(msg_str):
            yield event.plain_result(self._build_greeting_morning_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_greeting_night_menu(msg_str):
            yield event.plain_result(self._build_greeting_night_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_greeting_rank_menu(msg_str):
            yield event.plain_result(self._build_greeting_rank_menu())
            GLOBAL_STATS["send"] += 1
            return

        # ---- 签到系统 · 三级子菜单 ----
        if self._is_checkin_signin_menu(msg_str):
            yield event.plain_result(self._build_checkin_signin_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_checkin_query_menu(msg_str):
            yield event.plain_result(self._build_checkin_query_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_checkin_bank_menu(msg_str):
            yield event.plain_result(self._build_checkin_bank_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_checkin_steal_menu(msg_str):
            yield event.plain_result(self._build_checkin_steal_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_checkin_mount_menu(msg_str):
            yield event.plain_result(self._build_checkin_mount_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_checkin_job_menu(msg_str):
            yield event.plain_result(self._build_checkin_job_menu())
            GLOBAL_STATS["send"] += 1
            return

        # ---- 接口系统 · 三级子菜单（图片 / 视频 各自独立） ----
        meme_feature_args = self._is_meme_feature_menu(msg_str)
        if meme_feature_args is not None:
            if not self.meme_enable:
                yield event.plain_result("⚠️ 接口系统已关闭（后台「接口系统」中开启）")
                GLOBAL_STATS["send"] += 1
                return
            if not group_allowed(group_id, self.meme_groups):
                yield event.plain_result("⚠️ 本群未开启接口系统")
                GLOBAL_STATS["send"] += 1
                return
            if ac is None:
                yield event.plain_result("❌管理指令模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            media, page = meme_feature_args
            body = self._render_interface_list(page, media)
            if not body:
                kind = "视频" if media == "video" else "图片" if media == "image" else ""
                yield event.plain_result(f"暂无{kind}接口规则")
                GLOBAL_STATS["send"] += 1
                return
            lines = [body]
            lines.append("")
            lines.extend(self._interface_usage_lines(media))
            lines.append("")
            lines.append(f"💡 发送「{self._interface_menu_hint(media)} 页码」翻页")
            yield event.plain_result("\n".join(lines))
            GLOBAL_STATS["send"] += 1
            return

        # ---- MC系统 · 三级子菜单 ----
        if self._is_mc_version_menu(msg_str):
            yield event.plain_result(self._build_mc_version_menu())
            GLOBAL_STATS["send"] += 1
            return

        # ---- 管理系统 · 二级子菜单 ----
        if self._is_meme_admin_menu(msg_str):
            yield event.plain_result(self._build_meme_admin_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_word_admin_menu(msg_str):
            yield event.plain_result(self._build_word_admin_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_checkin_admin_menu(msg_str):
            yield event.plain_result(self._build_checkin_admin_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_status_admin_menu(msg_str):
            yield event.plain_result(self._build_status_admin_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_switch_admin_menu(msg_str):
            yield event.plain_result(self._build_switch_admin_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_chime_admin_menu(msg_str):
            yield event.plain_result(self._build_chime_admin_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_news_admin_menu(msg_str):
            yield event.plain_result(self._build_news_admin_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_member_admin_menu(msg_str):
            yield event.plain_result(self._build_member_admin_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_must_at_admin_menu(msg_str):
            yield event.plain_result(self._build_must_at_admin_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_super_admin_menu(msg_str):
            yield event.plain_result(self._build_super_admin_menu())
            GLOBAL_STATS["send"] += 1
            return

        # ---- 一级 / 二级菜单 ----
        if self._is_main_menu(msg_str):
            yield event.plain_result(self._build_main_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_meme_menu(msg_str):
            if not self.meme_enable:
                yield event.plain_result("⚠️ 接口系统已关闭（后台「接口系统」中开启）")
                GLOBAL_STATS["send"] += 1
                return
            if not group_allowed(group_id, self.meme_groups):
                yield event.plain_result("⚠️ 本群未开启接口系统")
                GLOBAL_STATS["send"] += 1
                return
            yield event.plain_result(self._build_meme_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_mc_menu(msg_str):
            yield event.plain_result(self._build_mc_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_greeting_menu(msg_str):
            yield event.plain_result(self._build_greeting_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_checkin_menu(msg_str):
            yield event.plain_result(self._build_checkin_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_daily_menu(msg_str):
            yield event.plain_result(self._build_daily_menu())
            GLOBAL_STATS["send"] += 1
            return
        if self._is_admin_menu(msg_str):
            yield event.plain_result(self._build_admin_menu())
            GLOBAL_STATS["send"] += 1
            return

        # ============ 接口列表 ============
        page = self._is_list_menu(msg_str)
        if page is not None:
            if not self.meme_enable:
                yield event.plain_result("⚠️ 接口系统已关闭（后台「接口系统」中开启）")
                GLOBAL_STATS["send"] += 1
                return
            if not group_allowed(group_id, self.meme_groups):
                yield event.plain_result("⚠️ 本群未开启接口系统")
                GLOBAL_STATS["send"] += 1
                return
            if ac is None:
                yield event.plain_result("❌管理指令模块未加载")
                GLOBAL_STATS["send"] += 1
                return
            body = self._render_interface_list(page)
            if not body:
                yield event.plain_result("暂无接口规则")
                GLOBAL_STATS["send"] += 1
                return
            lines = [body, ""]
            lines.append(f"💡 发送「{self.cmd_list_name} 页码」翻页")
            yield event.plain_result("\n".join(lines))
            GLOBAL_STATS["send"] += 1
            return

        # ============ 早安晚安（真实打卡逻辑，放在菜单之后） ============
        if self._is_group_feature_enable(group_id, "greeting") and self.greeting_module is not None:
            # ★ 打卡系统群白名单（早安与晚安共用一个开关）
            greeting_group_ok = self.greeting_module.is_group_allowed(group_id)
            if (self.greeting_module.match_morning(msg_str) and greeting_group_ok):
                try:
                    text = self.greeting_module.handle_morning(event)
                    if text:
                        yield event.plain_result(text)
                        GLOBAL_STATS["send"] += 1
                except Exception:
                    logger.exception("[apix-meme] 早安处理失败")
                return
            if (self.greeting_module.match_night(msg_str) and greeting_group_ok):
                try:
                    text = self.greeting_module.handle_night(event)
                    if text:
                        yield event.plain_result(text)
                        GLOBAL_STATS["send"] += 1
                except Exception:
                    logger.exception("[apix-meme] 晚安处理失败")
                return

        # ============ 接口调用 ============
        if (self.meme_enable
                and group_allowed(group_id, self.meme_groups)
                and self._is_group_feature_enable(group_id, "meme")):
            async for result in self._handle_meme(event, msg_str):
                yield result
            return

    # ============================================================
    # 接口调用处理
    # ============================================================
    async def _handle_meme(self, event: AstrMessageEvent, msg_str: str):
        group_id = _get_group_id_from_event(event)

        raw_clean, at_map = split_text_and_ats(event)
        raw_clean = " ".join(raw_clean.split())
        token_map = {}
        text_for_match = raw_clean
        for i, ph in enumerate(list(at_map.keys())):
            token = f"__AT{i}__"
            text_for_match = text_for_match.replace(ph, token)
            token_map[token] = at_map[ph]
        at_map = token_map

        if not text_for_match:
            return

        matched_rule = None
        matched_kw = ""
        param_str = ""
        for rule in self.rules:
            for kw in rule["keywords"]:
                if not kw:
                    continue
                if text_for_match == kw:
                    matched_rule = rule
                    matched_kw = kw
                    param_str = ""
                    break
                if text_for_match.startswith(kw):
                    rest = text_for_match[len(kw):].strip()
                    if rest:
                        matched_rule = rule
                        matched_kw = kw
                        param_str = rest
                        break
                if text_for_match.endswith(kw):
                    head = text_for_match[: -len(kw)].strip()
                    if head:
                        matched_rule = rule
                        matched_kw = kw
                        param_str = head
                        break
                midx = text_for_match.find(kw)
                if midx > 0:
                    head = text_for_match[:midx].strip()
                    tail = text_for_match[midx + len(kw):].strip()
                    if head or tail:
                        matched_rule = rule
                        matched_kw = kw
                        param_str = (head + " " + tail).strip()
                        break
            if matched_rule:
                break

        if not matched_rule:
            return

        if is_keyword_blocked(group_id, matched_kw, self.group_block_map):
            return

        try:
            need = int(matched_rule.get("param_count", "1"))
        except Exception:
            need = 1
        if need < 0:
            need = 0

        if need == 0:
            params = []
        else:
            if not param_str:
                return
            param_str = restore_ats(param_str, at_map)
            params = parse_params(param_str)
            if len(params) < need:
                return
            param_types = detect_param_types(matched_rule.get("url_template", ""), need)
            for i in range(need):
                if param_types[i] == "qq":
                    if not params[i].isdigit():
                        return

        url = build_url(matched_rule["url_template"], params)

        # media_type: 规则里标注 video 则按视频发送，其余按图片
        raw_media = str(matched_rule.get("media_type", "") or "").strip().lower()
        expect_kind = raw_media if raw_media in ("image", "video") else ""
        # json_field: 接口返回 JSON 时，媒体地址所在的字段（如 data.video）
        json_field = str(matched_rule.get("json_field", "") or "").strip()

        try:
            media_path, media_kind = await download_media(
                url, expect=expect_kind, json_field=json_field
            )
        except Exception as e:
            logger.warning(f"[apix-meme] 下载媒体失败: {e}")
            return

        # 规则标注为视频但接口实际返回图片（或反之）时，按实际类型发送，避免发不出去
        if expect_kind and media_kind != expect_kind:
            logger.warning(
                f"[apix-meme] 规则标注为 {expect_kind}，但接口返回 {media_kind}，按实际类型发送"
            )

        try:
            if media_kind == "video":
                chain = [Video.fromFileSystem(media_path)]
            else:
                chain = [Image.fromFileSystem(media_path)]
            yield event.chain_result(chain)
            GLOBAL_STATS["send"] += 1
        except Exception:
            logger.exception("[apix-meme] 发送媒体失败")