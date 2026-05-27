"""Utility functions for URL handling, size estimation, and language support."""
import tkinter as tk
from config import YOUTUBE_URL_PATTERN

LANGUAGE_MAP = {
    'en': '英文',
    'zh': '简体中文',
    'zh-Hans': '简体中文',
    'zh-Hant': '繁体中文',
    'zh-TW': '繁体中文',
    'zh-CN': '简体中文',
    'zh-Hans-CN': '简体中文',
    'zh-Hant-TW': '繁体中文',
    'ja': '日语',
    'ko': '韩语',
    'es': '西班牙语',
    'fr': '法语',
    'de': '德语',
    'it': '意大利语',
    'ru': '俄语',
    'pt': '葡萄牙语',
    'pt-BR': '巴西葡萄牙语',
    'vi': '越南语',
    'id': '印尼语',
    'th': '泰语',
    'ar': '阿拉伯语',
    'hi': '印地语',
    'nl': '荷兰语',
    'pl': '波兰语',
    'tr': '土耳其语',
    'uk': '乌克兰语',
    'sv': '瑞典语',
    'no': '挪威语',
    'fi': '芬兰语',
    'da': '丹麦语',
    'cs': '捷克语',
    'el': '希腊语',
    'he': '希伯来语',
    'ro': '罗马尼亚语',
    'hu': '匈牙利语',
    'ms': '马来语',
    'gu': '古吉拉特语',
    'fa': '波斯语',
    'bn': '孟加拉语',
    'ur': '乌尔都语',
    'bg': '保加利亚语',
    'sk': '斯洛伐克语',
    'sw': '斯瓦希里语',
    'ka': '格鲁吉亚语',
    'ta': '泰米尔语',
    'fil': '菲律宾语',
    'ml': '马拉雅拉姆语',
    'te': '泰卢固语',
    'mr': '马拉蒂语',
    'kn': '卡纳达语',
    'pa': '旁遮普语',
    'my': '缅甸语',
    'km': '高棉语',
    'lo': '老挝语',
    'am': '阿姆哈拉语',
    'ne': '尼泊尔语',
    'si': '僧伽罗语',
    'jw': '爪哇语',
    'su': '巽他语',
    'ca': '加泰罗尼亚语',
    'hr': '克罗地亚语',
    'sr': '塞尔维亚语',
    'sl': '斯洛文尼亚语',
    'et': '爱沙尼亚语',
    'lv': '拉脱维亚语',
    'lt': '立陶宛语',
    'az': '阿塞拜疆语',
    'kk': '哈萨克语',
    'uz': '乌兹别克语',
    'be': '白俄罗斯语',
    'mk': '马其顿语',
    'sq': '阿尔巴尼亚语',
    'hy': '亚美尼亚语',
    'eu': '巴斯克语',
    'gl': '加利西亚语',
    'af': '南非荷兰语',
    'iw': '希伯来语',
}

def get_language_display(code):
    return LANGUAGE_MAP.get(code, code)

def subtitle_sort_key(display_name):
    priority = {'简体中文': 0, '繁体中文': 1, 'English': 2}
    return (priority.get(display_name, 3), display_name)

def get_language_code(display):
    for code, name in LANGUAGE_MAP.items():
        if name == display:
            return code
    return display

def estimate_size(height, duration=None):
    est_size = height * height * 10 / 8
    if duration and duration > 0:
        est_size = est_size * duration / 60
    if est_size > 1024 * 1024 * 1024:
        return f"{est_size / 1024 / 1024 / 1024:.2f} GB"
    elif est_size > 1024 * 1024:
        return f"{est_size / 1024 / 1024:.1f} MB"
    else:
        return f"{est_size / 1024:.0f} KB"

def get_url_from_clipboard(root):
    try:
        clipboard_text = root.clipboard_get()
        url = clipboard_text.strip()
        if url and YOUTUBE_URL_PATTERN.match(url):
            return url
    except:
        pass
    return None