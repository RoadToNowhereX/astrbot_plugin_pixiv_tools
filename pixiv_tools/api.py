"""
Pixiv API 管理模块
管理 AppPixivAPI 实例的创建和认证
"""

import asyncio
from typing import Optional

from pixivpy3 import AppPixivAPI
from astrbot.api import logger


class PixivApiManager:
    """Pixiv API 管理器，从插件配置读取 refresh_token"""

    def __init__(self, refresh_token: str):
        self._refresh_token = refresh_token
        self._api: Optional[AppPixivAPI] = None

    def get_api(self) -> AppPixivAPI:
        """获取或创建已认证的 API 实例"""
        if self._api is None:
            if not self._refresh_token:
                raise ValueError(
                    "未配置 Pixiv Refresh Token，请在插件设置中填写。"
                )
            self._api = AppPixivAPI()
            self._api.auth(refresh_token=self._refresh_token)
            logger.info("Pixiv API 认证成功。")
        return self._api
