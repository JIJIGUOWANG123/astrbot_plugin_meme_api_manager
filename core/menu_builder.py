# ============================================================
# 菜单渲染辅助
# 标题栏统一为 ━━━ 标题 ━━━（每侧 3 个 ━），页脚为等宽色条。
#
# 关于对齐：emoji 在 QQ 等客户端里通常按双宽渲染，因此下面用「emoji + 全角空格」
# 来对齐命令名。不同客户端字体对 emoji 宽度处理可能不同，若某处不齐属正常现象。
# ============================================================
def _bar(title: str) -> str:
    """标题栏，两侧各 3 个 ━。"""
    return f"━━━ {title} ━━━"


def _bar_plain(total: int = 12) -> str:
    """页脚色条，长度取标题栏的常见宽度（4 个全角字标题时正好等长）。"""
    return "━" * total


# ============================================================
# 一级菜单
# ============================================================
def build_main_menu(plugin) -> str:
    return "\n".join([
        _bar("主菜单"),
        "🎭 接口系统    ⛏ MC系统",
        "📅 打卡系统    💰 签到系统",
        "🎲 每日系列    🔧 管理系统",
        _bar_plain(),
    ])


def build_meme_menu(plugin) -> str:
    def _names(raw, fallback):
        return [x.strip() for x in str(raw or "").split(",") if x.strip()] or [fallback]

    imgs = _names(getattr(plugin, "cmd_meme_image_name", ""), "图片接口")
    vids = _names(getattr(plugin, "cmd_meme_video_name", ""), "视频接口")

    lines = [_bar("接口系统")]
    lines.append(f"🖼 {imgs[0]}［页数］")
    if len(imgs) > 1:
        lines.append(f"　 别名：{' / '.join(imgs[1:])}")
    lines.append("　 只看图片类接口，没有页数默认第一页")
    lines.append(f"🎬 {vids[0]}［页数］")
    if len(vids) > 1:
        lines.append(f"　 别名：{' / '.join(vids[1:])}")
    lines.append("　 只看视频类接口，没有页数默认第一页")
    lines.append(_bar_plain())
    return "\n".join(lines)


def build_mc_menu(plugin) -> str:
    return "\n".join([
        _bar("MC系统"),
        "⛏ MC版本",
        _bar_plain(),
    ])


def build_greeting_menu(plugin) -> str:
    rank = getattr(plugin, "cmd_greeting_rank_name", "") or "打卡排行"
    stats = getattr(plugin, "cmd_greeting_stats_name", "") or "打卡统计"
    return "\n".join([
        _bar("打卡系统"),
        "🌅 早安打卡    🌙 晚安打卡",
        f"🏆 {rank}    📊 {stats}",
        _bar_plain(),
    ])


def build_checkin_menu(plugin) -> str:
    return "\n".join([
        _bar("签到系统"),
        "✅ 签到指令    📊 查询指令",
        "🏦 银行功能    🦸 神偷功能",
        "🐴 坐骑功能    🔨 打工功能",
        _bar_plain(),
    ])


def build_daily_menu(plugin) -> str:
    lines = [_bar("每日系列")]
    fortune_names = ""
    if plugin.fortune_module is not None:
        try:
            fortune_names = " / ".join(plugin.fortune_module.trigger_names)
        except Exception:
            pass
    husband_names = ""
    if plugin.husband_module is not None:
        try:
            husband_names = " / ".join(plugin.husband_module.trigger_names)
        except Exception:
            pass
    luck_names = ""
    if plugin.luck_module is not None:
        try:
            luck_names = " / ".join(plugin.luck_module.trigger_names)
        except Exception:
            pass

    if fortune_names:
        lines.append(f"🔮 运势　{fortune_names}")
    if husband_names:
        lines.append(f"💑 老公　{husband_names}")
    if luck_names:
        lines.append(f"🍀 人品　{luck_names}")
    # 读报指令是「多个用逗号分隔」的配置，这里统一成和上面一致的 / 分隔显示
    news_raw = getattr(plugin, "cmd_daily_news_name", "") or "每日读报"
    news_names = [x.strip() for x in str(news_raw).split(",") if x.strip()] or ["每日读报"]
    lines.append(f"📰 读报　{' / '.join(news_names)}")
    lines.append(_bar_plain())
    return "\n".join(lines)


def build_admin_menu(plugin) -> str:
    return "\n".join([
        _bar("管理系统"),
        "🖼 接口管理    📚 词库管理",
        "✅ 签到管理    🖥 状态管理",
        "🔀 开关管理    🕐 整点管理",
        "📣 艾特设置    👑 超管设置",
        "📰 读报管理    🚫 成员管理",
        _bar_plain(),
    ])


def build_member_admin_menu(plugin) -> str:
    return "\n".join([
        _bar("成员管理"),
        f"👢 {plugin.cmd_kick_name} @某人",
        f"🔇 {plugin.cmd_mute_name} @某人 ［秒数］",
        f"🔊 {plugin.cmd_unmute_name} @某人",
        "",
        f"🚫 {plugin.cmd_blacklist_name} @某人 ［kick|mute|ignore］",
        f"✅ {plugin.cmd_unblacklist_name} @某人",
        f"📋 {plugin.cmd_blacklist_list_name}",
        "",
        "💡 需要机器人是群主或管理员才能踢人/禁言",
        _bar_plain(),
    ])


def build_news_admin_menu(plugin) -> str:
    return "\n".join([
        _bar("读报管理"),
        f"🔔 {plugin.cmd_daily_news_on_name} ［群号］",
        f"🔕 {plugin.cmd_daily_news_off_name} ［群号］",
        f"🕐 {plugin.cmd_daily_news_time_name} ［群号］ 08:00",
        f"📋 {plugin.cmd_daily_news_list_name}",
        "",
        f"💡 手动读报：{plugin.cmd_daily_news_name}",
        _bar_plain(),
    ])


# ============================================================
# 接口系统 · 三级子菜单
# ============================================================
def build_meme_feature_menu(plugin) -> str:
    return "\n".join([
        _bar("接口功能"),
        f"📋 {plugin.cmd_list_name} ［页码］",
        "　 查看接口规则列表（支持分页）",
        "",
        "💡 发送「关键词 + 参数」即可调用接口",
        "　 无参数接口直接发关键词即可",
        "　 例：上香@某人",
        "　 例：鞭打 QQ号 QQ号",
        "　 例：报悲 任意文本",
        "　 返回图片或视频由接口配置决定",
        _bar_plain(),
    ])


# ============================================================
# MC系统 · 三级子菜单
# ============================================================
def build_mc_version_menu(plugin) -> str:
    return "\n".join([
        _bar("MC版本"),
        f"⛏ {plugin.cmd_minecraft_name}",
        "　 查询最新 Java 正式版 / 测试版",
        "",
        f"🔔 {plugin.cmd_mc_auto_name}",
        "　 开启/关闭本群自动检测推送",
        "",
        f"🚀 {plugin.cmd_mc_test_name}",
        "　 手动拉取最新版本并推送",
        "　 推送范围可在后台「MC测试推送指定群」里指定",
        _bar_plain(),
    ])


# ============================================================
# 打卡系统 · 三级子菜单
# ============================================================
def build_greeting_morning_menu(plugin) -> str:
    mn = " / ".join(plugin.greeting_module.morning_names) if plugin.greeting_module else "早安 / 早上好 / 起床"
    return "\n".join([
        _bar("早安打卡"),
        f"🌅 指令：{mn}",
        "　 记录起床时间，并显示睡眠时长",
        "",
        "💡 需在有效时间窗口内打早安",
        "💡 逻辑日 6 点重置",
        _bar_plain(),
    ])


def build_greeting_night_menu(plugin) -> str:
    nn = " / ".join(plugin.greeting_module.night_names) if plugin.greeting_module else "晚安 / 睡觉 / 睡了"
    return "\n".join([
        _bar("晚安打卡"),
        f"🌙 指令：{nn}",
        "　 记录睡觉时间，并显示清醒时长",
        "",
        "💡 需先打早安，才能打晚安",
        "💡 有截止时间限制",
        _bar_plain(),
    ])


def build_greeting_rank_menu(plugin) -> str:
    return "\n".join([
        _bar("打卡排行"),
        f"🏆 指令：{plugin.cmd_greeting_rank_name}",
        "　 查看打卡次数榜 + 早起时间榜各前十",
        _bar_plain(),
    ])


# ============================================================
# 签到系统 · 三级子菜单
# ============================================================
def build_checkin_signin_menu(plugin) -> str:
    ck = " / ".join(plugin.checkin_module.trigger_names) if plugin.checkin_module else "签到"
    rk = " / ".join(plugin.checkin_module.rank_trigger_names) if plugin.checkin_module else "签到排行"
    return "\n".join([
        _bar("签到指令"),
        f"✅ {ck}",
        "　 每日签到，随机 1-1000 积分",
        "",
        f"🏆 {rk}",
        "　 查看积分榜 / 连续榜 / 银行富豪榜",
        _bar_plain(),
    ])


def build_checkin_query_menu(plugin) -> str:
    inf = " / ".join(plugin.checkin_module.info_trigger_names) if plugin.checkin_module else "签到统计"
    rk = " / ".join(plugin.checkin_module.rank_trigger_names) if plugin.checkin_module else "签到排行"
    return "\n".join([
        _bar("查询指令"),
        f"📊 {inf}",
        "　 不跟参数 = 查自己",
        "",
        f"📊 {inf} @某人",
        f"📊 {inf} QQ号",
        "　 查询指定用户",
        "",
        f"🏆 {rk}",
        "　 查看积分榜 / 连续榜 / 银行富豪榜",
        _bar_plain(),
    ])


def build_checkin_bank_menu(plugin) -> str:
    bk = " / ".join(plugin.checkin_module.bank_trigger_names) if plugin.checkin_module else "银行"
    dp = " / ".join(plugin.checkin_module.bank_deposit_names) if plugin.checkin_module else "存钱"
    wd = " / ".join(plugin.checkin_module.bank_withdraw_names) if plugin.checkin_module else "取钱"
    return "\n".join([
        _bar("银行功能"),
        f"🏦 {bk}",
        "　 查看持有积分 / 银行余额 / 总资产",
        "",
        f"📥 {dp} 数量 / {dp} all",
        "　 把积分存入银行",
        "",
        f"📤 {wd} 数量 / {wd} all",
        "　 从银行取出积分",
        _bar_plain(),
    ])


def build_checkin_steal_menu(plugin) -> str:
    st = " / ".join(plugin.checkin_module.steal_trigger_names) if plugin.checkin_module else "偷积分"
    return "\n".join([
        _bar("神偷功能"),
        f"🦸 {st} @某人",
        f"🦸 {st} QQ号",
        "",
        "💡 有概率失败，失败可能被对方反拿积分",
        "💡 银行里的积分不会被偷",
        _bar_plain(),
    ])


def build_checkin_mount_menu(plugin) -> str:
    mt = " / ".join(plugin.checkin_module.mount_trigger_names) if plugin.checkin_module else "坐骑"
    ml = " / ".join(plugin.checkin_module.mount_list_trigger_names) if plugin.checkin_module else "坐骑列表"
    mb = " / ".join(plugin.checkin_module.mount_buy_trigger_names) if plugin.checkin_module else "购买坐骑"
    return "\n".join([
        _bar("坐骑功能"),
        f"🐴 {mt}",
        "　 查看已拥有坐骑",
        "",
        f"🛒 {ml}",
        "　 浏览可购买坐骑",
        "",
        f"💰 {mb} 坐骑名",
        "　 消耗积分购买坐骑",
        _bar_plain(),
    ])


def build_checkin_job_menu(plugin) -> str:
    jl = " / ".join(plugin.checkin_module.job_info_trigger_names) if plugin.checkin_module else "打工列表"
    jw = " / ".join(plugin.checkin_module.job_trigger_names) if plugin.checkin_module else "打工"
    return "\n".join([
        _bar("打工功能"),
        f"📋 {jl}",
        "　 查看工种和收益",
        "",
        f"🔨 {jw} 工种名",
        "　 打工赚取积分（各工种有独立冷却）",
        _bar_plain(),
    ])


# ============================================================
# 管理系统 · 二级子菜单
# ============================================================
def build_meme_admin_menu(plugin) -> str:
    return "\n".join([
        _bar("接口管理"),
        f"➕ {plugin.cmd_add_name} 关键词1,关键词2 | URL模板 | 参数个数 | 返回类型",
        f"🗑 {plugin.cmd_del_name} 序号",
        f"💾 {plugin.cmd_save_name}",
        "",
        "💡 返回类型填 image=图片 / video=视频；无参数接口参数个数填 0",
        _bar_plain(),
    ])


def build_word_admin_menu(plugin) -> str:
    return "\n".join([
        _bar("词库管理"),
        f"➕ {plugin.cmd_word_add_name} 关键词 | 回复内容",
        f"🗑 {plugin.cmd_word_del_name} 序号",
        f"📋 {plugin.cmd_word_list_name}",
        _bar_plain(),
    ])


def build_checkin_admin_menu(plugin) -> str:
    return "\n".join([
        _bar("签到管理"),
        f"🔨 {plugin.cmd_job_add_name} 工种名 | 冷却小时 | 最少收益 | 最多收益",
        f"🗑 {plugin.cmd_job_del_name} 工种名或序号",
        f"🐴 {plugin.cmd_mount_add_name} 坐骑名 | 价格 | 描述",
        f"🗑 {plugin.cmd_mount_del_name} 坐骑名或序号",
        _bar_plain(),
    ])


def build_status_admin_menu(plugin) -> str:
    names = " / ".join(plugin.cmd_status_names)
    return "\n".join([
        _bar("状态管理"),
        f"🖥 电脑状态：{names}",
        f"🔔 {plugin.cmd_daily_push_on_name} ［群号］",
        f"🔕 {plugin.cmd_daily_push_off_name} ［群号］",
        f"🕐 {plugin.cmd_daily_push_time_name} ［群号］ 09:00",
        f"📋 {plugin.cmd_daily_push_list_name}",
        _bar_plain(),
    ])


def build_switch_admin_menu(plugin) -> str:
    return "\n".join([
        _bar("开关管理"),
        f"🟢 {plugin.cmd_enable_name}",
        f"🔴 {plugin.cmd_disable_name}",
        f"🟢 {plugin.cmd_enable_feature_name} 运势 ［群号］",
        f"🔴 {plugin.cmd_disable_feature_name} 运势 ［群号］",
        f"📊 {plugin.cmd_feature_status_name} ［群号］",
        _bar_plain(),
    ])


def build_chime_admin_menu(plugin) -> str:
    return "\n".join([
        _bar("整点管理"),
        f"🟢 {plugin.cmd_chime_on_name} ［群号］",
        f"🔴 {plugin.cmd_chime_off_name} ［群号］",
        f"📊 {plugin.cmd_chime_status_name} ［群号］",
        f"🕐 {plugin.cmd_chime_hours_name} 8,12,20",
        f"✏️ {plugin.cmd_chime_text_name} 自定义文案",
        f"📋 {plugin.cmd_chime_list_name}",
        f"🚀 {plugin.cmd_chime_test_name} ［群号］",
        _bar_plain(),
    ])


def build_must_at_admin_menu(plugin) -> str:
    return "\n".join([
        _bar("艾特设置"),
        f"🟢 {plugin.cmd_must_at_bot_on_name} ［群号］",
        f"🔴 {plugin.cmd_must_at_bot_off_name} ［群号］",
        f"📊 {plugin.cmd_must_at_bot_status_name} ［群号］",
        _bar_plain(),
    ])


def build_super_admin_menu(plugin) -> str:
    return "\n".join([
        _bar("超管设置"),
        f"➕ {plugin.cmd_add_admin_name} QQ号",
        f"🗑 {plugin.cmd_del_admin_name} QQ号",
        f"📋 {plugin.cmd_admin_list_name}",
        f"👀 {plugin.cmd_view_admin_name}",
        f"🔄 {plugin.cmd_refresh_admin_name}",
        _bar_plain(),
    ])
