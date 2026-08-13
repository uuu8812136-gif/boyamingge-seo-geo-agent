"""平台编码常量。

保留 Synapse 原项目编码方案：
    1 = xiaohongshu
    2 = channels (视频号)
    3 = douyin
    4 = kuaishou
    5 = bilibili
图文平台（本项目新增，编码 10 段）：
    10 = baijiahao (百家号图文)
    11 = zhihu (知乎文章)
"""

PLATFORM_CODES = {
    "xiaohongshu": 1,
    "channels": 2,
    "douyin": 3,
    "kuaishou": 4,
    "bilibili": 5,
    "baijiahao": 10,
    "zhihu": 11,
}
CODE_TO_PLATFORM = {v: k for k, v in PLATFORM_CODES.items()}

PLATFORM_NAMES = {
    "xiaohongshu": "小红书",
    "channels": "视频号",
    "douyin": "抖音",
    "kuaishou": "快手",
    "bilibili": "B站",
    "baijiahao": "百家号",
    "zhihu": "知乎",
}

# 以图文（标题+正文+插图）为主的平台，区别于短视频平台
IMAGE_TEXT_PLATFORMS = {"baijiahao", "zhihu", "xiaohongshu"}

# 以短视频上传发布为主的平台（先上传视频文件，转码/处理后再填标题、封面、发布）
VIDEO_PLATFORMS = {"channels", "douyin", "kuaishou", "bilibili"}

# 各平台发布页 URL（用于 Playwright 自动化登录与发布）
# baijiahao / zhihu 的发布页与选择器基于平台公开的创作者后台结构，标记为待真实账号联调验证
PLATFORM_PUBLISH_URLS = {
    "xiaohongshu": "https://creator.xiaohongshu.com/publish/publish",
    "channels": "https://channels.weixin.qq.com/platform/post/create",
    "douyin": "https://creator.douyin.com/creator-micro/content/upload",
    "kuaishou": "https://cp.kuaishou.com/article/publish/video",
    "bilibili": "https://member.bilibili.com/platform/upload/video/frame",
    "baijiahao": "https://baijiahao.baidu.com/builder/rc/edit?type=news",
    "zhihu": "https://zhuanlan.zhihu.com/write",
}

# 各平台登录页 URL
PLATFORM_LOGIN_URLS = {
    "xiaohongshu": "https://creator.xiaohongshu.com/login",
    "channels": "https://channels.weixin.qq.com/login",
    "douyin": "https://creator.douyin.com/creator-micro/login?enter_from=qr",
    "kuaishou": "https://cp.kuaishou.com/article/publish/video",
    "bilibili": "https://passport.bilibili.com/login",
    "baijiahao": "https://baijiahao.baidu.com/",
    "zhihu": "https://www.zhihu.com/signin",
}

# 各平台强认证 Cookie 名集合（用于判断登录是否成功）
PLATFORM_AUTH_COOKIE_NAMES = {
    "xiaohongshu": {"web_session", "customer-sso-sid", "x-user-id-encoder"},
    "channels": {"wxuin", "uin", "finder_username"},
    "douyin": {"sessionid", "sessionid_ss", "sid_guard", "sid_tt", "uid_tt", "sso_uid_tt"},
    "kuaishou": {"userId", "bUserId", "kuaishou.server.web_st", "kuaishou.server.web_ph"},
    "bilibili": {"DedeUserID", "DedeUserID__ckMd5", "SESSDATA", "bili_jct"},
    "baijiahao": {"BDUSS", "BDUSS_BFESS", "STOKEN"},
    "zhihu": {"z_c0", "_zap", "d_c0"},
}


def normalize_platform(name: str) -> str:
    return (name or "").strip().lower()


def resolve_platform_code(name: str) -> int:
    norm = normalize_platform(name)
    if norm not in PLATFORM_CODES:
        raise ValueError(f"Unsupported platform: {name}")
    return PLATFORM_CODES[norm]
