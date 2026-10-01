import os
import json
from astrbot.api import logger

FEATURE_ALIAS = {
    "运势": "fortune",
    "今日运势": "fortune",
    "fortune": "fortune",
    "老公": "husband",
    "今日老公": "husband",
    "husband": "husband",
    "人品": "luck",
    "今日人品": "luck",
    "luck": "luck",
    "词库": "word_reply",
    "word_reply": "word_reply",
    "表情": "meme",
    "表情包": "meme",
    "meme": "meme",
    "电脑状态": "status",
    "状态": "status",
    "status": "status",
    "早安": "greeting",
    "晚安": "greeting",
    "早安晚安": "greeting",
    "greeting": "greeting",
    "mc": "minecraft",
    "MC": "minecraft",
    "minecraft": "minecraft",
    "MC版本": "minecraft",
    "mc版本": "minecraft",
    "签到": "checkin",
    "checkin": "checkin",
    "神偷": "steal",
    "偷积分": "steal",
    "steal": "steal",
    "银行": "bank",
    "bank": "bank",
    "坐骑": "mount",
    "mount": "mount",
    "打工": "job",
    "job": "job",
}

FEATURE_LABEL = {
    "fortune": "今日运势",
    "husband": "今日老公",
    "luck": "今日人品",
    "word_reply": "自定义词库",
    "meme": "接口系统",
    "status": "电脑状态",
    "greeting": "早安晚安",
    "minecraft": "MC版本检测",
    "checkin": "每日签到",
    "steal": "偷积分",
    "bank": "银行系统",
    "mount": "坐骑系统",
    "job": "打工系统",
}

# 这些是「每日签到」下的子功能：主签到开关关掉后，它们也会一并失效
CHECKIN_SUB_FEATURES = ("steal", "bank", "mount", "job")


class AdminCommands:
    def __init__(self, plugin):
        self.plugin = plugin

    @staticmethod
    def _sender_id(event) -> str:
        try:
            return str(event.get_sender_id() or "")
        except Exception:
            return ""

    async def check_admin(self, event) -> bool:
        p = self.plugin
        user_id = self._sender_id(event)
        if not user_id:
            return False
        try:
            if event.is_admin():
                return True
        except Exception:
            pass
        if user_id in p.plugin_admins:
            return True
        if p.group_admin_module is not None:
            try:
                return await p.group_admin_module.is_group_admin(event, user_id)
            except Exception:
                logger.exception("[apix-meme] 群管判定失败")
                return False
        return False

    def add_plugin_admin(self, qq: str) -> bool:
        p = self.plugin
        qq = str(qq).strip()
        if not qq:
            return False
        if qq not in p.plugin_admins:
            p.plugin_admins.append(qq)
            p.save_rules_to_config()
        return True

    def del_plugin_admin(self, qq: str) -> bool:
        p = self.plugin
        qq = str(qq).strip()
        if qq in p.plugin_admins:
            p.plugin_admins.remove(qq)
            p.save_rules_to_config()
            return True
        return False

    def list_plugin_admins(self) -> list:
        return list(self.plugin.plugin_admins)

    def is_feature_on(self, key: str) -> bool:
        return True

    def disable_feature(self, name: str, group_id: str = None, target_group: str = None) -> str:
        key = FEATURE_ALIAS.get(str(name).strip())
        if not key:
            return f"⚠️未知功能：{name}\n可用：{' / '.join(FEATURE_LABEL.values())}"
        p = self.plugin

        gid = None
        if target_group:
            gid = str(target_group).strip()
        elif group_id:
            gid = str(group_id).strip()

        if not gid:
            return "⚠️ 请在群聊中使用该指令，或指定群号：关闭功能 运势 群号"

        if gid not in p.group_feature_switches:
            p.group_feature_switches[gid] = {}
        p.group_feature_switches[gid][key] = False
        p.save_rules_to_config()

        if target_group:
            return f"✅已远程关闭群【{gid}】：{FEATURE_LABEL[key]}"
        return f"✅本群已关闭：{FEATURE_LABEL[key]}"

    def enable_feature(self, name: str, group_id: str = None, target_group: str = None) -> str:
        key = FEATURE_ALIAS.get(str(name).strip())
        if not key:
            return f"⚠️未知功能：{name}\n可用：{' / '.join(FEATURE_LABEL.values())}"
        p = self.plugin

        gid = None
        if target_group:
            gid = str(target_group).strip()
        elif group_id:
            gid = str(group_id).strip()

        if not gid:
            return "⚠️ 请在群聊中使用该指令，或指定群号：开启功能 运势 群号"

        if gid not in p.group_feature_switches:
            p.group_feature_switches[gid] = {}
        p.group_feature_switches[gid][key] = True
        p.save_rules_to_config()

        if target_group:
            return f"✅已远程开启群【{gid}】：{FEATURE_LABEL[key]}"
        return f"✅本群已开启：{FEATURE_LABEL[key]}"

    def feature_status_text(self, group_id: str = None, target_group: str = None) -> str:
        """
        显示本群的功能状态。
        与后台配置保持一致：既显示「全局总开关 / 允许群号」，
        也显示「本群功能开关」，这样一眼能看出功能到底为什么开/关。
        """
        p = self.plugin

        show_gid = None
        if target_group:
            show_gid = str(target_group).strip()
        elif group_id:
            show_gid = str(group_id).strip()

        if not show_gid:
            return "⚠️ 请在群聊中使用该指令，或指定群号：功能状态 群号"

        gid = show_gid
        lines = [f"======群 {gid} 功能开关状态======"]

        # ---------- ① 全局总开关 ----------
        global_switches = []
        try:
            global_switches.append(("电脑状态", bool(getattr(p, "status_enable", True))))
        except Exception:
            pass
        try:
            global_switches.append(("接口系统", bool(getattr(p, "meme_enable", True))))
        except Exception:
            pass
        if global_switches:
            lines.append("【全局总开关】")
            for label, on in global_switches:
                lines.append(f"· {label}：{'✅ 开启' if on else '❌ 全局关闭'}")

        # ---------- ② 全局群白名单 ----------
        def _glist(name):
            return [str(x) for x in (getattr(p, name, None) or [])]

        def _wl_state(name):
            gids = _glist(name)
            if not gids:
                return "不限制群聊", True
            return (f"仅限 {len(gids)} 个群", gid in gids)

        wl_rows = []
        for label, name in (("全局", "allowed_groups"),
                            ("电脑状态", "status_groups"),
                            ("接口系统", "meme_groups")):
            desc, ok = _wl_state(name)
            wl_rows.append((label, desc, ok))
        if any(desc != "不限制群聊" for _l, desc, _o in wl_rows):
            lines.append("")
            lines.append("【群号白名单】")
            for label, desc, ok in wl_rows:
                mark = "✅" if ok else "❌"
                lines.append(f"· {label}：{desc} {mark if desc != '不限制群聊' else ''}".rstrip())

        # ---------- ③ 各功能的「允许群号」配置 ----------
        #   与后台各功能页的群号白名单一一对应，避免状态显示与实际配置脱节
        def _wl_of(getter):
            """getter() 返回群号列表；空列表视为不限制"""
            try:
                gids = [str(x) for x in (getter() or [])]
            except Exception:
                return None
            return gids

        wl_specs = [
            ("今日运势", lambda: getattr(getattr(p, "fortune_module", None), "allowed_groups", None)),
            ("今日老公", lambda: getattr(getattr(p, "husband_module", None), "allowed_groups", None)),
            ("今日人品", lambda: getattr(getattr(p, "luck_module", None), "allowed_groups", None)),
            ("自定义词库", lambda: getattr(getattr(p, "word_reply_module", None), "allowed_groups", None)),
            ("早安晚安", lambda: getattr(getattr(p, "greeting_module", None), "allowed_groups", None)),
            ("签到系统", lambda: getattr(getattr(p, "checkin_module", None), "allowed_groups", None)),
        ]
        wl_lines = []
        for label, getter in wl_specs:
            gids = _wl_of(getter)
            if gids is None:
                continue          # 模块未加载，跳过
            if not gids:
                continue          # 不限制群聊，无需显示
            mark = "✅" if gid in gids else "❌"
            wl_lines.append(f"· {label}：{'、'.join(gids)} {mark}")
        if wl_lines:
            lines.append("")
            lines.append("【功能群号白名单】（标注的是本群是否可用）")
            lines.extend(wl_lines)

        # ---------- ④ 本群功能开关 ----------
        lines.append("")
        lines.append("【本群功能开关】")
        group_cfg = p.group_feature_switches.get(gid, {})
        sub_feats = set(CHECKIN_SUB_FEATURES)
        for key, label in FEATURE_LABEL.items():
            g_on = bool(group_cfg.get(key, True))
            # 子功能额外标注父开关，避免误解为完全独立
            suffix = ""
            if key in sub_feats:
                if not bool(group_cfg.get("checkin", True)):
                    suffix = "（签到主开关已关，随之失效）"
                else:
                    suffix = "（签到子功能）"
            lines.append(f"· {label}：{'✅ 开启' if g_on else '❌ 关闭'}{suffix}")

        # ---------- ⑤ 用「群号订阅」控制的功能 ----------
        #   整点报时 / 每日读报 / 定时状态推送 的每群开关存在各自的状态文件里，
        #   不在 group_feature_switches 中，这里单独列出，避免状态显示与后台脱节
        sub_specs = [
            ("整点报时", "hourly_chime_module"),
            ("每日读报", "daily_news_module"),
            ("定时状态推送", "status_push_module"),
        ]
        sub_lines = []
        for label, attr in sub_specs:
            m = getattr(p, attr, None)
            if m is None:
                continue
            try:
                on = bool(m.is_group_on(gid))
            except Exception:
                continue
            sub_lines.append(f"· {label}：{'✅ 本群已开启' if on else '❌ 本群未开启'}")
        if sub_lines:
            lines.append("")
            lines.append("【群号订阅类功能】")
            lines.extend(sub_lines)

        lines.append("")
        lines.append("💡 默认全部开启；用「开启功能 xxx」「关闭功能 xxx」调整本群状态")
        lines.append("💡 全局总开关与群号白名单在后台配置中设置")
        lines.append("💡 群号订阅类功能在各自菜单里用指令开关（或在后台填群号）")
        return "\n".join(lines)

    def set_group_must_at_bot(self, group_id: str, enabled: bool) -> str:
        p = self.plugin
        gid = str(group_id).strip()
        if not gid:
            return "⚠️ 请指定群号"
        if not hasattr(p, "group_must_at_bot") or p.group_must_at_bot is None:
            p.group_must_at_bot = {}
        p.group_must_at_bot[gid] = bool(enabled)
        p.save_rules_to_config()
        state = "开启" if enabled else "关闭"
        return f"✅ 已{state}群【{gid}】的「必须艾特机器人」限制"

    def get_group_must_at_bot(self, group_id: str) -> bool:
        p = self.plugin
        gid = str(group_id).strip()
        if not gid:
            return bool(p.must_at_bot)
        if hasattr(p, "group_must_at_bot") and gid in p.group_must_at_bot:
            return bool(p.group_must_at_bot[gid])
        return bool(p.must_at_bot)

    def must_at_bot_status_text(self, group_id: str = None, target_group: str = None) -> str:
        p = self.plugin
        gid = None
        if target_group:
            gid = str(target_group).strip()
        elif group_id:
            gid = str(group_id).strip()
        if not gid:
            return "⚠️ 请在群聊中使用该指令，或指定群号：必须艾特状态 群号"
        enabled = self.get_group_must_at_bot(gid)
        global_default = bool(p.must_at_bot)
        is_override = hasattr(p, "group_must_at_bot") and gid in p.group_must_at_bot
        lines = [
            f"======群 {gid} 必须艾特机器人状态======",
            f"当前状态：{'✅ 开启（必须 @机器人 才响应）' if enabled else '❌ 关闭（无需 @机器人）'}",
            f"来源：{'本群独立设置' if is_override else '跟随全局默认'}",
            f"全局默认：{'开启' if global_default else '关闭'}",
            "",
            "💡 用「必须艾特开 [群号]」「必须艾特关 [群号]」调整",
        ]
        return "\n".join(lines)

    def word_add(self, args: str) -> str:
        p = self.plugin
        if p.word_reply_module is None:
            return "❌词库模块未加载"
        if "|" not in args:
            return f"用法：{p.cmd_word_add_name} 关键词1,关键词2 | 回复内容"
        kw_part, reply_part = args.split("|", 1)
        kw_part = kw_part.strip()
        reply_part = reply_part.strip()
        if not kw_part or not reply_part:
            return "关键词和回复内容都不能为空"
        keywords = [k.strip() for k in kw_part.split(",") if k.strip()]
        if not keywords:
            return "关键词不能为空"
        p.word_reply_module.rules.append({
            "keywords": keywords,
            "reply": reply_part,
        })
        p.save_rules_to_config()
        return f"✅词库已添加\n关键词：{','.join(keywords)}\n回复：{reply_part}"

    def word_del(self, args: str) -> str:
        p = self.plugin
        if p.word_reply_module is None:
            return "❌词库模块未加载"
        if not args.isdigit():
            return f"用法：{p.cmd_word_del_name} 序号"
        idx = int(args) - 1
        if idx < 0 or idx >= len(p.word_reply_module.rules):
            return "⚠️序号不存在"
        removed = p.word_reply_module.rules.pop(idx)
        p.save_rules_to_config()
        return f"✅已删除词库：{'/'.join(removed['keywords'])}"

    def word_list_text(self) -> str:
        p = self.plugin
        if p.word_reply_module is None:
            return "❌词库模块未加载"
        rules = p.word_reply_module.rules
        if not rules:
            return "词库为空"
        lines = [f"======词库列表（共 {len(rules)} 条）======"]
        for i, rule in enumerate(rules, start=1):
            kw = " ☆ ".join(rule["keywords"])
            reply = rule["reply"].replace("\n", " ")
            if len(reply) > 20:
                reply = reply[:20] + "..."
            lines.append(f"{i}：{kw} → {reply}")
        return "\n".join(lines)

    def group_disable(self, group_id: str) -> str:
        p = self.plugin
        if not group_id:
            return "私聊无法关闭"
        if group_id in p.disabled_groups:
            return "本群已经处于关闭状态"
        p.disabled_groups.append(group_id)
        p.save_rules_to_config()
        return "✅本群娱乐系统已关闭"

    def group_enable(self, group_id: str) -> str:
        p = self.plugin
        if not group_id:
            return "私聊无法开启"
        if group_id in p.disabled_groups:
            p.disabled_groups.remove(group_id)
            p.save_rules_to_config()
        return "✅本群娱乐系统已开启"

    @staticmethod
    def _sync_rules(p):
        """
        改规则前先把 self.rules 与磁盘对齐。
        因为 reload_cfg() 每次都会按磁盘顺序重建 self.rules（未保存的修改会被
        挂到列表末尾），若直接用内存里的序号增删，用户看到列表和实际序号可能不一致。
        """
        try:
            if not getattr(p, "_dirty", False):
                p.reload_cfg()
        except Exception:
            logger.exception("[apix-meme] 同步规则列表失败")

    def meme_add(self, args: str) -> str:
        p = self.plugin
        if not args:
            return (
                f"用法1（单参数）：{p.cmd_add_name} 关键词1,关键词2,URL模板\n"
                f"用法2（多参数）：{p.cmd_add_name} 关键词1,关键词2 | URL模板 | 参数个数\n"
                f"用法3（指定返回类型）：{p.cmd_add_name} 关键词 | URL模板 | 参数个数 | video\n"
                f"用法4（接口返回 JSON）：{p.cmd_add_name} 关键词 | URL模板 | 参数个数 | video | data.video\n"
                f"　 （参数个数填 0 表示无参数接口；返回类型 image=图片 / video=视频，默认 image）\n"
                f"　 （最后一段填 JSON 里媒体地址的字段路径，留空则自动搜索）"
            )

        self._sync_rules(p)

        if "|" in args:
            parts = [x.strip() for x in args.split("|")]
            if len(parts) < 2 or len(parts) > 5:
                return "格式错误！多参数格式：关键词 | URL | 参数个数 | 返回类型 | JSON字段"
            kw_str = parts[0]
            url_template = parts[1]
            param_count = parts[2] if len(parts) >= 3 else "1"
            media_type = parts[3].lower() if len(parts) >= 4 else ""
            json_field = parts[4] if len(parts) >= 5 else ""
            keywords = [k.strip() for k in kw_str.split(",") if k.strip()]
            if not keywords or not url_template:
                return "关键词和 URL 不能为空"
            if not param_count.isdigit():
                param_count = "1"
            if media_type not in ("image", "video"):
                media_type = "image"
            p.rules.append({
                "keywords": keywords,
                "url_template": url_template,
                "param_count": param_count,
                "media_type": media_type,
                "json_field": json_field,
                "meme": "",
            })
            p._dirty = True
            kind_label = "视频" if media_type == "video" else "图片"
            extra = f"，JSON字段 {json_field}" if json_field else ""
            return (
                f"✅添加成功（{param_count} 参数，{kind_label}{extra}）\n"
                f"执行 {p.cmd_save_name} 保存！"
            )

        parts = [x.strip() for x in args.rsplit(",", 1)]
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return "格式错误！"
        kw_str, url_template = parts
        keywords = [k.strip() for k in kw_str.split(",") if k.strip()]
        if not keywords:
            return "关键词不能为空"
        p.rules.append({
            "keywords": keywords,
            "url_template": url_template,
            "param_count": "1",
            "media_type": "image",
            "json_field": "",
            "meme": "",
        })
        p._dirty = True
        return f"✅添加成功（1 参数，图片）\n执行 {p.cmd_save_name} 保存！"

    def meme_del(self, args: str) -> str:
        p = self.plugin
        if not args or not args.isdigit():
            return f"用法：{p.cmd_del_name} 序号"
        self._sync_rules(p)
        idx = int(args) - 1
        if idx < 0 or idx >= len(p.rules):
            return "⚠️序号不存在"
        p.rules.pop(idx)
        p._dirty = True
        return f"✅已删除，执行 {p.cmd_save_name} 保存！"

    def meme_save(self) -> str:
        p = self.plugin
        ok = p.save_rules_to_config()
        if ok:
            return "✅所有规则已保存到插件配置！"
        return "❌保存失败，请查看后台日志"