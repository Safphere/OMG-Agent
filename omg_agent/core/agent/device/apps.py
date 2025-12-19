"""App package name mappings."""

# Common app name to package name mapping
APP_PACKAGE_MAP: dict[str, str] = {
    # Social
    "wechat": "com.tencent.mm",
    "weixin": "com.tencent.mm",
    "qq": "com.tencent.mobileqq",
    "weibo": "com.sina.weibo",
    "dingtalk": "com.alibaba.android.rimet",
    "feishu": "com.ss.android.lark",
    "telegram": "org.telegram.messenger",
    "whatsapp": "com.whatsapp",

    # Shopping
    "taobao": "com.taobao.taobao",
    "jd": "com.jingdong.app.mall",
    "jingdong": "com.jingdong.app.mall",
    "pinduoduo": "com.xunmeng.pinduoduo",
    "xianyu": "com.taobao.idlefish",

    # Food & Delivery
    "meituan": "com.sankuai.meituan",
    "eleme": "me.ele",
    "dianping": "com.dianping.v1",

    # Travel
    "gaode": "com.autonavi.minimap",
    "amap": "com.autonavi.minimap",
    "baidu_map": "com.baidu.BaiduMap",
    "didi": "com.sdu.didi.psnger",
    "ctrip": "ctrip.android.view",
    "12306": "com.MobileTicket",

    # Video
    "douyin": "com.ss.android.ugc.aweme",
    "tiktok": "com.zhiliaoapp.musically",
    "kuaishou": "com.smile.gifmaker",
    "bilibili": "tv.danmaku.bili",
    "tencent_video": "com.tencent.qqlive",
    "youku": "com.youku.phone",
    "iqiyi": "com.qiyi.video",

    # Music
    "netease_music": "com.netease.cloudmusic",
    "qq_music": "com.tencent.qqmusic",
    "kugou": "com.kugou.android",
    "ximalaya": "com.ximalaya.ting.android",

    # Social/Community
    "xiaohongshu": "com.xingin.xhs",
    "zhihu": "com.zhihu.android",
    "douban": "com.douban.frodo",

    # Tools
    "chrome": "com.android.chrome",
    "settings": "com.android.settings",
    "camera": "com.android.camera",
    "gallery": "com.android.gallery3d",
    "calculator": "com.android.calculator2",
    "clock": "com.android.deskclock",
    "calendar": "com.android.calendar",
    "contacts": "com.android.contacts",
    "messages": "com.android.mms",
    "phone": "com.android.dialer",
    "files": "com.android.documentsui",

    # Others
    "alipay": "com.eg.android.AlipayGphone",
    "unionpay": "com.unionpay",
    "cainiao": "com.cainiao.wireless",
    "keep": "com.gotokeep.keep",
}

# Alternative names mapping
APP_ALIASES: dict[str, str] = {
    "wechat": "weixin",
    "jingdong": "jd",
    "amap": "gaode",
    "tiktok": "douyin",
    "netease": "netease_music",
    "wymusic": "netease_music",
    "qqmusic": "qq_music",
    "red": "xiaohongshu",
    "xhs": "xiaohongshu",
}


def find_package_name(app_name: str) -> str | None:
    """
    Find package name for an app.

    Args:
        app_name: App name (Chinese or English)

    Returns:
        Package name or None if not found
    """
    # Normalize name
    name_lower = app_name.lower().strip()

    # Remove common suffixes/prefixes
    name_lower = name_lower.replace(" ", "_")
    for suffix in ["app", "应用", "软件"]:
        name_lower = name_lower.replace(suffix, "")

    # Direct lookup
    if name_lower in APP_PACKAGE_MAP:
        return APP_PACKAGE_MAP[name_lower]

    # Check if it's already a package name
    if "." in name_lower and name_lower.count(".") >= 2:
        return app_name

    # Alias lookup
    if name_lower in APP_ALIASES:
        canonical = APP_ALIASES[name_lower]
        return APP_PACKAGE_MAP.get(canonical)

    # Fuzzy matching - check if name is substring
    for key, package in APP_PACKAGE_MAP.items():
        if name_lower in key or key in name_lower:
            return package

    # Chinese name mapping
    chinese_map = {
        "微信": "com.tencent.mm",
        "微博": "com.sina.weibo",
        "钉钉": "com.alibaba.android.rimet",
        "飞书": "com.ss.android.lark",
        "淘宝": "com.taobao.taobao",
        "京东": "com.jingdong.app.mall",
        "拼多多": "com.xunmeng.pinduoduo",
        "闲鱼": "com.taobao.idlefish",
        "美团": "com.sankuai.meituan",
        "饿了么": "me.ele",
        "大众点评": "com.dianping.v1",
        "高德地图": "com.autonavi.minimap",
        "百度地图": "com.baidu.BaiduMap",
        "滴滴": "com.sdu.didi.psnger",
        "携程": "ctrip.android.view",
        "抖音": "com.ss.android.ugc.aweme",
        "快手": "com.smile.gifmaker",
        "哔哩哔哩": "tv.danmaku.bili",
        "B站": "tv.danmaku.bili",
        "腾讯视频": "com.tencent.qqlive",
        "优酷": "com.youku.phone",
        "爱奇艺": "com.qiyi.video",
        "网易云音乐": "com.netease.cloudmusic",
        "QQ音乐": "com.tencent.qqmusic",
        "酷狗": "com.kugou.android",
        "喜马拉雅": "com.ximalaya.ting.android",
        "小红书": "com.xingin.xhs",
        "知乎": "com.zhihu.android",
        "豆瓣": "com.douban.frodo",
        "支付宝": "com.eg.android.AlipayGphone",
        "云闪付": "com.unionpay",
        "菜鸟": "com.cainiao.wireless",
        "设置": "com.android.settings",
        "相机": "com.android.camera",
        "相册": "com.android.gallery3d",
        "计算器": "com.android.calculator2",
        "时钟": "com.android.deskclock",
        "日历": "com.android.calendar",
        "通讯录": "com.android.contacts",
        "短信": "com.android.mms",
        "电话": "com.android.dialer",
        "文件": "com.android.documentsui",
    }

    return chinese_map.get(app_name)


def get_all_supported_apps() -> list[str]:
    """Get list of all supported app names."""
    apps = list(APP_PACKAGE_MAP.keys())
    apps.sort()
    return apps
