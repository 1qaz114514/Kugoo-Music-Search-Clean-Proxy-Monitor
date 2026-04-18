from mitmproxy import http, ctx
import json
import os

# ==============================================
# 从配置文件导入所有配置
# ==============================================
from kugou_config import (
    SINGER_WHITELIST_FILE,
    SONG_WHITELIST_FILE,
    KUGOU_DOMAINS,
    KUGOU_IP_PATTERNS,
    COMPILED_SEARCH_PATTERNS,
    STATIC_EXTENSIONS,
    COMPILED_BLOCK_PATTERNS,
    EMPTY_RESPONSE,
    ALLOW_AUDIO_EXTENSIONS
)

# ==============================================
# 加载白名单
# ==============================================
def load_song_whitelist():
    singer_set = set()
    song_set = set()
    
    # 加载歌手白名单
    if os.path.exists(SINGER_WHITELIST_FILE):
        with open(SINGER_WHITELIST_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # 移除序号（如 "1. 周杰伦" -> "周杰伦"）
                    if ". " in line:
                        line = line.split(". ", 1)[1]
                    singer_set.add(line.strip())
    
    # 加载歌曲白名单
    if os.path.exists(SONG_WHITELIST_FILE):
        with open(SONG_WHITELIST_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    song_set.add(line.strip())
    
    return singer_set, song_set

SINGER_WHITELIST, SONG_WHITELIST = load_song_whitelist()

PLAY_KEYWORDS = (
    "getsonginfo", "get_song_info", "playinfo", "play_info",
    "trackercdn", "tracker", "get_res_privilege", "get_res",
    "get_url", "geturl", "playurl", "play_url",
    "getsongplayinfo", "getplayinfo",
    "mv", "getmv", "mvplay", "getmvinfo", "video", "getvideo", "playvideo",
    "mvstartflv", "union_all_mv_play", "/v1/video"
)

SEARCH_QUERY_KEYS = (
    "keyword", "songName", "singerName", "query", "key",
    "keyword_original", "songname", "singername"
)

FORM_QUERY_KEYS = (
    "keyword", "songName", "singerName", "query", "key", "songname", "singername"
)

# 专门的黑名单关键词（必须拦截）+ 额外拦截规则
BLACKLIST_KEYWORDS = {"9178", "7891"}


def contains_blocked_numbers(text):
    """检查文本是否包含需要拦截的数字（91、78、9178、7891等）"""
    if not text:
        return False
    text = str(text).lower()
    # 检查是否包含91或78
    if "91" in text or "78" in text:
        return True
    return False


def is_in_blacklist(text):
    """检查是否在黑名单中"""
    if not text:
        return False
    text = text.strip()
    return text in BLACKLIST_KEYWORDS


def load(loader):
    """在 addon 注册后打日志；勿在模块 import 时调用 ctx.log，否则 mitmdump 可能加载失败立刻退出"""
    ctx.log.info(
        f"[√] 白名单已加载，共 {len(SINGER_WHITELIST)} 位歌手，{len(SONG_WHITELIST)} 首歌曲"
    )


# ==============================================
# 白名单匹配
# ==============================================
def is_in_whitelist(text):
    if not text:
        return False
    text = text.strip()
    
    # 过滤掉明显不是搜索词的内容（避免Parameter Error等提示）
    if len(text) < 2:
        return False
    if text.lower() in ["parameter error", "error", "null", "none", "undefined"]:
        return False
    # 过滤纯数字（搜索建议接口返回的数字ID）
    if text.isdigit():
        return False
    
    # 必须完全匹配白名单才放行
    if text in SINGER_WHITELIST or text in SONG_WHITELIST:
        ctx.log.info(f"[√] 白名单完全匹配 | {text}")
        return True
    
    ctx.log.info(f"[X] 未完全匹配白名单 | {text}")
    return False


def host_matches_domain(host, domain):
    return host == domain or host.endswith(f".{domain}")


def url_has_extension(url, extensions):
    return any(
        url.endswith(ext) or f"{ext}?" in url or f"{ext}&" in url
        for ext in extensions
    )


def extract_keyword_from_json(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in ["keyword", "songname", "singername", "query", "key"]:
                return str(v)
            result = extract_keyword_from_json(v)
            if result:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = extract_keyword_from_json(item)
            if result:
                return result
    return ""

# ==============================================
# 第一步：判断是否是酷狗的请求
# ==============================================
def is_kugou_url(host):
    host = host.lower()
    if any(host_matches_domain(host, domain) for domain in KUGOU_DOMAINS):
        return True
    for pattern in KUGOU_IP_PATTERNS:
        if pattern.match(host):
            return True
    return False

# ==============================================
# 第二步：判断是否是音频文件（优先放行）
# ==============================================
def is_audio_file(url):
    url = url.lower()
    if url_has_extension(url, ALLOW_AUDIO_EXTENSIONS):
        return True
    media_keywords = ["playurl", "play_url", "get_res_privilege", "get_url", "media", "audio", "song", "video", "mv", "playvideo"]
    for keyword in media_keywords:
        if keyword in url:
            for ext in ALLOW_AUDIO_EXTENSIONS:
                if ext.replace(".", "") in url:
                    return True
    return False

# ==============================================
# 第三步：判断是否是静态资源
# ==============================================
def is_static_resource(url):
    url = url.lower()
    return url_has_extension(url, STATIC_EXTENSIONS)

# ==============================================
# 第三步：拦截规则（匹配完整 URL 和路径）
# ==============================================
def should_block(url, path=None):
    url = url.lower()
    for pattern in COMPILED_BLOCK_PATTERNS:
        if pattern.search(url):
            return True
    if path:
        path = path.lower()
        for pattern in COMPILED_BLOCK_PATTERNS:
            if pattern.search(path):
                return True
    return False

def is_search_path(url, path=None):
    url = url.lower()
    for pattern in COMPILED_SEARCH_PATTERNS:
        if pattern.search(url):
            return True
    if path:
        path = path.lower()
        for pattern in COMPILED_SEARCH_PATTERNS:
            if pattern.search(path):
                return True
    return False


def is_play_request(url, method=None, path=None):
    if any(keyword in url for keyword in PLAY_KEYWORDS):
        return True
    return method == "POST" and path == "/"

# ==============================================
# 空响应
# ==============================================
EMPTY_JSON = json.dumps(EMPTY_RESPONSE).encode("utf-8")

# ==============================================
# 核心拦截逻辑
# ==============================================
def request(flow: http.HTTPFlow):
    try:
        host = flow.request.host.lower()
        url = flow.request.pretty_url.lower()
        path = flow.request.path.lower()
        method = flow.request.method
        
        # 第一步：只处理酷狗的请求
        if not is_kugou_url(host):
            return

        # 第二步：播放相关接口优先放行（核心播放接口）
        if is_play_request(url, method, path):
            ctx.log.info(f"[√] 放行播放接口 | {flow.request.pretty_url}")
            return

        # 第三步：搜索建议接口直接拦截（优先处理，避免Parameter Error重复提示）
        if "getsearchtip" in url or "search_no_focus_word" in url:
            ctx.log.warn(f"[KUGOU BLOCK] 搜索建议接口拦截 | {flow.request.pretty_url}")
            flow.response = http.Response.make(200, EMPTY_JSON, {"Content-Type": "application/json;charset=utf-8"})
            return

        # 第四步：音频文件优先放行（确保可以播放）
        if is_audio_file(url):
            ctx.log.info(f"[√] 放行音频文件 | {flow.request.pretty_url}")
            return

        # 第五步：检查是否拦截 - 同时检查完整URL和路径（优先拦截）
        # 对于IP地址请求，先检查是否是播放接口，否则直接拦截
        is_ip_request = any(pattern.match(host) for pattern in KUGOU_IP_PATTERNS)
        if is_ip_request:
            if not is_play_request(url, method, path) and not is_audio_file(url):
                ctx.log.warn(f"[KUGOU BLOCK] IP地址请求拦截 | {flow.request.pretty_url}")
                flow.response = http.Response.make(200, EMPTY_JSON, {"Content-Type": "application/json;charset=utf-8"})
                return
        
        if should_block(url, path):
            ctx.log.warn(f"[KUGOU BLOCK] {flow.request.pretty_url}")
            flow.response = http.Response.make(200, EMPTY_JSON, {"Content-Type": "application/json;charset=utf-8"})
            return

        # 第六步：检查是否是搜索路径
        if is_search_path(url, path):
            
            ctx.log.info(f"[DEBUG] 检测到搜索路径 | {flow.request.pretty_url}")
            keyword = ""

            if flow.request.query:
                for key in SEARCH_QUERY_KEYS:
                    keyword = flow.request.query.get(key, "")
                    if keyword:
                        break

            if not keyword and method == "POST":
                try:
                    if flow.request.urlencoded_form:
                        for key in FORM_QUERY_KEYS:
                            keyword = flow.request.urlencoded_form.get(key, "")
                            if keyword:
                                break
                    elif flow.request.text:
                        body = json.loads(flow.request.text)
                        keyword = extract_keyword_from_json(body)
                except:
                    pass

            if keyword:
                ctx.log.info(f"[+] 捕获搜索 | {keyword}")
                # 优先检查额外拦截规则：任何包含91或78的都拦截
                if contains_blocked_numbers(keyword):
                    ctx.log.info(f"[X] 额外拦截（包含91/78） | {keyword}")
                    flow.metadata["whitelist_allowed"] = False
                    flow.response = http.Response.make(200, EMPTY_JSON, {"Content-Type": "application/json;charset=utf-8"})
                    return
                # 然后检查黑名单，黑名单中的关键词必须拦截
                elif is_in_blacklist(keyword):
                    ctx.log.info(f"[X] 黑名单拦截 | {keyword}")
                    flow.metadata["whitelist_allowed"] = False
                    flow.response = http.Response.make(200, EMPTY_JSON, {"Content-Type": "application/json;charset=utf-8"})
                    return
                elif is_in_whitelist(keyword):
                    ctx.log.info(f"[√] 白名单放行 | {keyword}")
                    flow.metadata["whitelist_allowed"] = True
                    return
                else:
                    ctx.log.info(f"[X] 拦截非白名单 | {keyword}")
                    flow.metadata["whitelist_allowed"] = False
                    flow.response = http.Response.make(200, EMPTY_JSON, {"Content-Type": "application/json;charset=utf-8"})
                    return
            else:
                ctx.log.info(f"[!] 拦截无关键词搜索")
                flow.response = http.Response.make(200, EMPTY_JSON, {"Content-Type": "application/json;charset=utf-8"})
                return

        # 第六步：静态资源放行（仅在没有拦截规则匹配时）
        if is_static_resource(url):
            ctx.log.info(f"[√] 放行静态资源 | {flow.request.pretty_url}")
            return

        # 第七步：其他所有酷狗请求都拦截！（激进策略）
        ctx.log.warn(f"[KUGOU BLOCK] 激进拦截 | {flow.request.pretty_url}")
        flow.response = http.Response.make(200, EMPTY_JSON, {"Content-Type": "application/json;charset=utf-8"})
        return
        
    except Exception as e:
        ctx.log.error(f"request() 异常: {e}")

# ==============================================
# 响应拦截
# ==============================================
def response(flow: http.HTTPFlow):
    try:
        host = flow.request.host.lower()
        url = flow.request.pretty_url.lower()
        path = flow.request.path.lower()
        
        if not is_kugou_url(host):
            return

        if not is_search_path(url, path):
            return

        # 检查是否是白名单放行的请求
        if flow.metadata.get("whitelist_allowed"):
            ctx.log.info(f"[√] 白名单响应保留 | {flow.request.pretty_url}")
            return

        # 禁用缓存
        flow.response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        flow.response.headers["Pragma"] = "no-cache"
        flow.response.headers["Expires"] = "0"

        content_type = flow.response.headers.get("Content-Type", "")
        if "application/json" not in content_type and "text/json" not in content_type:
            flow.response.text = ""
            flow.response.status_code = 404
            return

        try:
            data = json.loads(flow.response.text)
            has_allow = False
            def check_content(obj):
                nonlocal has_allow
                if has_allow:
                    return
                if isinstance(obj, str):
                    if is_in_whitelist(obj):
                        has_allow = True
                elif isinstance(obj, dict):
                    for v in obj.values():
                        check_content(v)
                elif isinstance(obj, list):
                    for item in obj:
                        check_content(item)

            check_content(data)
            if not has_allow:
                ctx.log.info(f"[!] 响应清空 | {flow.request.pretty_url}")
                flow.response.text = json.dumps(EMPTY_RESPONSE)
                flow.response.status_code = 200
        except:
            flow.response.text = json.dumps(EMPTY_RESPONSE)
            flow.response.status_code = 200
            
    except Exception as e:
        ctx.log.error(f"response() 异常: {e}")

# ==============================================
# 错误处理
# ==============================================
def error(flow: http.HTTPFlow):
    if flow.error:
        error_msg = str(flow.error)
        if any(key in error_msg for key in ["Connection killed", "ConnectionResetError", "WinError 10054", "client disconnect", "server disconnect", "stream reset"]):
            return
        ctx.log.error(f"非致命错误: {flow.error}")
