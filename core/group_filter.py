def parse_line_list(raw) -> list:
    result = []
    if not raw:
        return result
    if isinstance(raw, list):
        lines = []
        for item in raw:
            if isinstance(item, str):
                lines.extend(item.splitlines())
    else:
        lines = str(raw).splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line not in result:
            result.append(line)
    return result


def parse_group_block_keywords(raw) -> dict:
    result = {}
    if not raw:
        return result
    if isinstance(raw, list):
        lines = []
        for item in raw:
            if isinstance(item, str):
                lines.extend(item.splitlines())
    else:
        lines = str(raw).splitlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line and "：" not in line:
            continue
        parts = line.replace("：", ":").split(":", 1)
        group_id = parts[0].strip()
        kw_str = parts[1].strip()
        if not group_id:
            continue
        kws = [k.strip() for k in kw_str.split(",") if k.strip()]
        result.setdefault(group_id, [])
        for k in kws:
            if k not in result[group_id]:
                result[group_id].append(k)
    return result


def is_group_allowed(group_id: str, mode: str, whitelist: list, blacklist: list) -> bool:
    if not group_id:
        return True
    mode = (mode or "off").strip().lower()
    if mode == "whitelist":
        return group_id in whitelist
    if mode == "blacklist":
        return group_id not in blacklist
    return True


def is_keyword_blocked(group_id: str, keyword: str, group_block_map: dict) -> bool:
    if not group_id or not group_block_map:
        return False
    blocked = group_block_map.get(group_id, [])
    if not blocked:
        return False
    for b in blocked:
        if b and b in keyword:
            return True
    return False