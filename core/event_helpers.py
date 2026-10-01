from astrbot.api.message_components import At


def to_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="ignore")
        except Exception:
            return value.decode("latin-1", errors="ignore")
    return str(value)


def get_group_id_from_event(event) -> str:
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


def get_ats_from_msg(event) -> list:
    """从消息链里提取所有 @ 的 QQ 号"""
    at_list = []
    try:
        for comp in event.message_obj.message:
            if not isinstance(comp, At):
                continue
            qq = (
                getattr(comp, "qq", None)
                or getattr(comp, "user_id", None)
                or getattr(comp, "target", None)
            )
            if qq is not None:
                at_list.append(to_str(qq))
    except Exception:
        pass
    return at_list


def split_text_and_ats(event):
    """
    把消息链拆成 (纯文本, at占位符映射)。
    at 会被替换成 \x00AT0\x00 之类的占位符，方便关键词匹配。
    """
    parts = []
    at_map = {}
    idx = 0
    try:
        for comp in event.message_obj.message:
            if isinstance(comp, At):
                qq = (
                    getattr(comp, "qq", None)
                    or getattr(comp, "user_id", None)
                    or getattr(comp, "target", None)
                )
                ph = f"\x00AT{idx}\x00"
                at_map[ph] = to_str(qq) if qq is not None else ""
                parts.append(f" {ph} ")
                idx += 1
            else:
                text = getattr(comp, "text", None)
                if text:
                    parts.append(str(text))
                else:
                    t2 = getattr(comp, "content", None)
                    if t2:
                        parts.append(str(t2))
    except Exception:
        pass
    return "".join(parts), at_map


def restore_ats(text: str, at_map: dict) -> str:
    """把占位符还原回真实 QQ 号"""
    if not text:
        return ""
    out = text
    for ph, qq in at_map.items():
        out = out.replace(ph, qq)
    return out


def has_at_bot(event, bot_id: str) -> bool:
    """判断消息里有没有 @ 到指定 bot"""
    if not bot_id:
        return False
    try:
        return bot_id in get_ats_from_msg(event)
    except Exception:
        return False


def get_sender_name(event) -> str:
    """尽最大努力获取发送者昵称"""
    for attr in ("sender_name", "sender_nickname", "nickname", "nick"):
        try:
            v = getattr(event, attr, None)
            if v:
                return to_str(v)
        except Exception:
            pass
    try:
        mo = getattr(event, "message_obj", None)
        if mo is not None:
            for attr in ("sender_name", "sender_nickname", "nickname"):
                v = getattr(mo, attr, None)
                if v:
                    return to_str(v)
            sender = getattr(mo, "sender", None)
            if sender is not None:
                for attr in ("nickname", "card", "name"):
                    v = getattr(sender, attr, None)
                    if v:
                        return to_str(v)
    except Exception:
        pass
    return ""