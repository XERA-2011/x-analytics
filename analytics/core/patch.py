"""
API 请求伪装补丁
用于绕过反爬虫限制
"""

import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 常见浏览器 UA
# 常见浏览器 UA (扩充列表)
USER_AGENTS = [
    # macOS - Chrome / Safari / Edge
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    
    # Windows - Chrome / Edge / Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

# 原始请求方法
_original_request = requests.Session.request

def _patched_request(self, method, url, *args, **kwargs):
    """
    打补丁后的请求方法
    自动添加随机 UA 和常用 Headers
    """
    headers = kwargs.get("headers", {})
    
    # 如果没有 UA，随机添加一个
    if "User-Agent" not in headers:
        headers["User-Agent"] = random.choice(USER_AGENTS)
    
    # 添加其他常用 Headers 伪装成真实浏览器
    if "Accept" not in headers:
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    
    if "Accept-Language" not in headers:
        headers["Accept-Language"] = "zh-CN,zh;q=0.9,en;q=0.8"
    
    if "Accept-Encoding" not in headers:
        headers["Accept-Encoding"] = "gzip, deflate, br, zstd"
        
    if "Connection" not in headers:
        headers["Connection"] = "keep-alive"
        
    if "Cache-Control" not in headers:
        headers["Cache-Control"] = "max-age=0"

    # 针对东方财富的特定伪装
    if "eastmoney.com" in url or "em" in url:
        headers["Referer"] = "https://quote.eastmoney.com/center/gridlist.html"
        headers["Origin"] = "https://quote.eastmoney.com"
        # 移除可能暴露身份的 Host (requests 会自动管理)
        # headers["Host"] = "push2.eastmoney.com"

    if "Upgrade-Insecure-Requests" not in headers:
        headers["Upgrade-Insecure-Requests"] = "1"

    kwargs["headers"] = headers
    
    # 增加超时设置 (如果未设置)
    if "timeout" not in kwargs:
        kwargs["timeout"] = 15
        
    return _original_request(self, method, url, *args, **kwargs)

def apply_patches():
    """应用所有补丁"""
    print("🛡️ 正在应用 API 伪装补丁...")
    
    # 1. Monkey Patch requests.Session.request
    requests.Session.request = _patched_request
    print("✅ 已注入随机 User-Agent 和浏览器 Headers")
    
    # 2. 配置全局重试策略 (针对 requests.get/post 等直接调用)
    # 注意：AkShare 内部虽然可能有自己的 session，但这个全局补丁能覆盖大部分情况
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    http.mount("https://", adapter)
    http.mount("http://", adapter)
    
    print("🛡️ API 伪装补丁已生效")
