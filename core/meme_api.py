import aiohttp
import json
import os
import time
import uuid
import tempfile
import urllib.parse
from astrbot.api import logger


def parse_params(raw: str) -> list:
    """把用户输入拆成参数列表（逗号、空格、顿号都作为分隔）"""
    if not raw:
        return []
    text = str(raw)
    for sep in ("，", "、", " ", "\t", "\n"):
        text = text.replace(sep, ",")
    return [x.strip() for x in text.split(",") if x.strip()]


def build_url(template: str, params: list) -> str:
    """
    替换 URL 模板里的占位符。
    支持：
      {qq} {qq1} {qq2} ...   → 数字参数（调用方负责校验是纯数字）
      {text} {text1} {text2} → 文本参数
      {pic} {pic1} {pic2}    → 兼容旧配置（不校验类型）
    """
    if not template:
        return template

    url = template

    def _quote(v):
        return urllib.parse.quote(str(v), safe="")

    if "{qq}" in url:
        val = params[0] if params else ""
        url = url.replace("{qq}", _quote(val))

    for i in range(1, 6):
        ph = f"{{qq{i}}}"
        if ph in url:
            idx = i - 1
            val = params[idx] if idx < len(params) else ""
            url = url.replace(ph, _quote(val))

    if "{text}" in url:
        val = params[0] if params else ""
        url = url.replace("{text}", _quote(val))

    for i in range(1, 6):
        ph = f"{{text{i}}}"
        if ph in url:
            idx = i - 1
            val = params[idx] if idx < len(params) else ""
            url = url.replace(ph, _quote(val))

    if "{pic}" in url:
        val = params[0] if params else ""
        url = url.replace("{pic}", _quote(val))

    for i in range(1, 6):
        ph = f"{{pic{i}}}"
        if ph in url:
            idx = i - 1
            val = params[idx] if idx < len(params) else ""
            url = url.replace(ph, _quote(val))

    return url


def detect_param_types(template: str, param_count: int) -> list:
    """
    根据 URL 模板里出现的占位符，推断每个参数的类型。
    返回列表，长度 = param_count，元素为 "qq" / "text" / "any"。

    优先级：qq > text > any
    """
    types = ["any"] * max(0, param_count)
    if not template:
        return types

    def _set(idx, t):
        if idx < 0 or idx >= len(types):
            return
        rank = {"qq": 3, "text": 2, "any": 1}
        if rank.get(t, 0) > rank.get(types[idx], 0):
            types[idx] = t

    if "{qq}" in template:
        _set(0, "qq")
    for i in range(1, 6):
        if f"{{qq{i}}}" in template:
            _set(i - 1, "qq")

    if "{text}" in template:
        _set(0, "text")
    for i in range(1, 6):
        if f"{{text{i}}}" in template:
            _set(i - 1, "text")

    if "{pic}" in template:
        _set(0, "any")
    for i in range(1, 6):
        if f"{{pic{i}}}" in template:
            _set(i - 1, "any")

    return types


# 各类媒体格式的后缀映射
_EXT_MAP = {
    "jpeg": "jpg", "jpg": "jpg", "png": "png", "gif": "gif", "webp": "webp",
    "bmp": "bmp", "svg": "svg", "avif": "avif", "heic": "heic",
    "mp4": "mp4", "webm": "webm", "quicktime": "mov", "x-matroska": "mkv",
    "x-msvideo": "avi", "mpeg": "mpeg", "3gpp": "3gp", "x-flv": "flv",
}


def _guess_media(content_type: str, url: str = "") -> tuple:
    """
    根据 content-type（必要时看 URL 后缀）判断媒体类型。
    返回 (kind, ext)，kind 为 "image" / "video" / "unknown"。
    """
    ct = (content_type or "").lower().split(";")[0].strip()
    ext = ""
    for key, val in _EXT_MAP.items():
        if key in ct:
            ext = val
            break

    if ct.startswith("video/") or ext in ("mp4", "webm", "mov", "mkv", "avi", "mpeg", "3gp", "flv"):
        return "video", ext or "mp4"
    if ct.startswith("image/") or ext in ("jpg", "png", "gif", "webp", "bmp", "svg", "avif", "heic"):
        return "image", ext or "png"

    # content-type 不认识时，退回看 URL 后缀
    lower_url = (url or "").lower().split("?")[0]
    for suffix, kind in (
        (".mp4", "video"), (".webm", "video"), (".mov", "video"), (".mkv", "video"),
        (".avi", "video"), (".flv", "video"), (".gif", "image"), (".jpg", "image"),
        (".jpeg", "image"), (".png", "image"), (".webp", "image"),
    ):
        if lower_url.endswith(suffix):
            return kind, suffix.lstrip(".")
    return "unknown", ext or "bin"


def get_content_ext(content_type: str) -> str:
    """兼容旧接口：仅按 content-type 推断后缀。
    历史上无法识别时统一回落 png，这里保持一致，避免影响既有调用方。"""
    _kind, ext = _guess_media(content_type)
    if not ext or ext == "bin":
        return "png"
    return ext


# JSON 里常见的媒体地址字段名，按优先级排序
_URL_FIELD_CANDIDATES = (
    "video", "video_url", "videourl", "mp4", "play", "play_url", "playurl",
    "url", "src", "image", "image_url", "imageurl", "img", "imgurl",
    "pic", "picture", "cover", "media", "file", "download",
)

# 值明显不是媒体直链的字段，避免误取
_URL_SKIP_VALUES = ("success", "ok", "true", "false", "null", "none", "")


def _looks_like_media_url(value: str) -> bool:
    """判断一个字符串是否像媒体地址（http/https 开头，或指向常见媒体后缀）。"""
    if not isinstance(value, str):
        return False
    v = value.strip()
    if not v or v.lower() in _URL_SKIP_VALUES:
        return False
    lower = v.lower().split("?")[0]
    if lower.startswith(("http://", "https://")):
        return True
    # 相对路径：必须带媒体后缀才认
    return any(lower.endswith(s) for s in (
        ".mp4", ".webm", ".mov", ".mkv", ".avi", ".flv", ".m3u8",
        ".gif", ".jpg", ".jpeg", ".png", ".webp", ".bmp",
    ))


def _get_by_path(data, path: str):
    """按 "data.video" 这样的点号路径取值，取不到返回 None。"""
    cur = data
    for part in str(path or "").split("."):
        part = part.strip()
        if not part:
            continue
        if isinstance(cur, dict):
            if part not in cur:
                return None
            cur = cur[part]
        elif isinstance(cur, list):
            if not part.isdigit() or int(part) >= len(cur):
                return None
            cur = cur[int(part)]
        else:
            return None
    return cur


def extract_media_url(payload, json_field: str = "") -> str:
    """
    从接口返回的 JSON 里提取媒体地址。

    提取顺序：
      1. 规则里显式配置的字段（json_field，支持 "data.video" 这种点号路径）
      2. 深度优先搜索常见字段名（video / url / mp4 ...）
      3. 递归扫描所有字符串值，找出像媒体直链的那个
    找不到返回空串。
    """
    if payload is None:
        return ""

    # 1) 显式配置优先
    if json_field:
        val = _get_by_path(payload, json_field)
        if isinstance(val, str) and _looks_like_media_url(val):
            return val.strip()
        # 显式字段存在但不像直链时继续兜底，不直接失败

    # 2) 按常见字段名搜索（同一层优先，再看嵌套）
    def _search_fields(node, depth=0):
        if depth > 6:
            return ""
        if isinstance(node, dict):
            for key in _URL_FIELD_CANDIDATES:
                if key in node:
                    val = node[key]
                    if isinstance(val, str) and _looks_like_media_url(val):
                        return val.strip()
                    # 字段值是嵌套对象时继续往里找
                    if isinstance(val, (dict, list)):
                        got = _search_fields(val, depth + 1)
                        if got:
                            return got
            for val in node.values():
                if isinstance(val, (dict, list)):
                    got = _search_fields(val, depth + 1)
                    if got:
                        return got
        elif isinstance(node, list):
            for item in node:
                got = _search_fields(item, depth + 1)
                if got:
                    return got
        return ""

    got = _search_fields(payload)
    if got:
        return got

    # 3) 全量扫描字符串
    def _scan(node, depth=0):
        if depth > 6:
            return ""
        if isinstance(node, str):
            return node.strip() if _looks_like_media_url(node) else ""
        if isinstance(node, dict):
            for val in node.values():
                got = _scan(val, depth + 1)
                if got:
                    return got
        elif isinstance(node, list):
            for item in node:
                got = _scan(item, depth + 1)
                if got:
                    return got
        return ""

    return _scan(payload)


def _json_error_message(payload) -> str:
    """从 JSON 里取出可读的错误信息，用于失败提示。"""
    if isinstance(payload, dict):
        for k in ("msg", "message", "error", "errmsg", "info"):
            v = payload.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        code = payload.get("code")
        if code not in (None, 0, "0", 200, "200"):
            return f"code={code}"
    return ""


async def download_media(
    url: str,
    timeout: int = 15,
    expect: str = "",
    json_field: str = "",
    _depth: int = 0,
    _seen=None,
) -> tuple:
    """
    下载接口返回的媒体（图片或视频）。
    返回 (file_path, kind)，kind 为 "image" / "video" / "unknown"。

    expect    : 规则里标注的期望类型（"image" / "video"）。
                当 content-type 和 URL 后缀都无法判断时用它兜底。
    json_field: 接口返回 JSON 时，媒体地址所在的字段（如 "data.video"）。
                留空则自动搜索常见字段名。
    """
    seen = _seen if _seen is not None else set()
    if _depth > 3:
        raise RuntimeError("接口返回的 JSON 嵌套层级过深，无法提取媒体地址")
    if url in seen:
        raise RuntimeError("接口返回的 JSON 指向了同一个地址，疑似循环")
    seen.add(url)

    logger.info(f"[meme-api] 请求 URL: {url}")
    t = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=t) as session:
        async with session.get(url) as resp:
            content_type = resp.headers.get("content-type", "").lower()
            if resp.status != 200:
                try:
                    body = await resp.text()
                except Exception:
                    body = ""
                logger.warning(f"[meme-api] HTTP {resp.status}, body={body[:300]}")
                raise RuntimeError(f"接口异常 HTTP {resp.status}")

            # ---- 接口返回 JSON：说明是「API 包装」，真正的媒体地址在 JSON 里 ----
            if "application/json" in content_type or "text/plain" in content_type:
                payload = None
                try:
                    payload = await resp.json(content_type=None)
                except Exception:
                    try:
                        payload = json.loads(await resp.text())
                    except Exception:
                        payload = None

                if payload is not None:
                    media_url = extract_media_url(payload, json_field)
                    if not media_url:
                        msg = _json_error_message(payload) or "未找到媒体地址"
                        logger.warning(f"[meme-api] JSON 中未找到媒体地址: {payload}")
                        raise RuntimeError(
                            f"接口返回的是 JSON，但没找到媒体地址：{msg}"
                            + ("（可在规则里配置「JSON字段」指定路径）" if not json_field else
                               f"（已按字段 {json_field} 查找）")
                        )

                    # 相对路径补全为绝对地址
                    if media_url.startswith("//"):
                        media_url = "https:" + media_url
                    elif media_url.startswith("/"):
                        parsed = urllib.parse.urlsplit(str(resp.url) if resp.url else url)
                        media_url = f"{parsed.scheme}://{parsed.netloc}{media_url}"

                    logger.info(
                        f"[meme-api] 从 JSON 提取到媒体地址"
                        f"{'（字段 ' + json_field + '）' if json_field else ''}: {media_url}"
                    )
                    # 递归下载真正的媒体文件
                    return await download_media(
                        media_url,
                        timeout=timeout,
                        expect=expect,
                        json_field=json_field,
                        _depth=_depth + 1,
                        _seen=seen,
                    )

            final_url = str(resp.url) if resp.url else url
            kind, ext = _guess_media(content_type, final_url)

            # content-type / 后缀都判断不出来时，按规则期望类型兜底
            want = str(expect or "").strip().lower()
            if kind == "unknown" and want in ("image", "video"):
                kind = want
                ext = "mp4" if want == "video" else "png"
                logger.info(
                    f"[meme-api] 无法从响应判断类型（content-type={content_type!r}），"
                    f"按规则标注当作 {want} 处理"
                )

            if kind == "unknown":
                logger.warning(
                    f"[meme-api] 无法识别的媒体类型: content-type={content_type!r}, url={final_url}"
                )
                raise RuntimeError(
                    f"接口返回了未知格式的内容（{content_type or '无 content-type'}），"
                    f"请在规则里把「返回类型」设为 image 或 video"
                )

            data = await resp.read()

    tmp_dir = os.path.join(tempfile.gettempdir(), "astrbot_meme")
    os.makedirs(tmp_dir, exist_ok=True)
    try:
        now = time.time()
        for fn in os.listdir(tmp_dir):
            fp = os.path.join(tmp_dir, fn)
            if os.path.isfile(fp) and now - os.path.getmtime(fp) > 3600:
                os.remove(fp)
    except Exception:
        pass

    fname = f"meme_{int(time.time())}_{uuid.uuid4().hex[:8]}.{ext}"
    fpath = os.path.join(tmp_dir, fname)
    with open(fpath, "wb") as f:
        f.write(data)
    logger.info(f"[meme-api] 已下载 {kind}（{len(data)} 字节）-> {fpath}")
    return fpath, kind


async def download_image(url: str, timeout: int = 15) -> str:
    """兼容旧接口：只下载图片，返回本地路径。"""
    path, kind = await download_media(url, timeout=timeout)
    if kind != "image":
        raise RuntimeError("接口返回的不是图片")
    return path