"""
AstrBot LLM 工具包装器
将 pixiv 小说工具函数包装为 AstrBot FunctionTool
"""

import json
from typing import Any, List

from pydantic import Field
from pydantic.dataclasses import dataclass

from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext
from astrbot.api import logger

from .tools import (
    SearchNovelParams,
    NovelRecommendedParams,
    SortAndSendNovelResultsParams,
    SearchNovelAndSendParams,
    NovelRecommendedAndSendParams,
    GetCurrentTimeParams,
    search_novel,
    novel_recommended,
    sort_and_send_novel_results,
    search_novel_and_send,
    novel_recommended_and_send,
    get_current_time,
)


@dataclass
class PixivSearchNovelTool(FunctionTool[AstrAgentContext]):
    """搜索Pixiv小说"""

    api_manager: Any = None
    name: str = "pixiv_search_novel"
    description: str = "搜索Pixiv小说。支持按关键词、标签、正文搜索"
    parameters: dict = Field(
        default_factory=lambda: SearchNovelParams.model_json_schema()
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        try:
            api = self.api_manager.get_api()
            params = SearchNovelParams(**kwargs)
            result = await search_novel(api, params)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"搜索小说失败: {e}")
            return f"搜索小说失败: {str(e)}"


@dataclass
class PixivNovelRecommendedTool(FunctionTool[AstrAgentContext]):
    """获取推荐小说"""

    api_manager: Any = None
    name: str = "pixiv_novel_recommended"
    description: str = "获取系统推荐的小说列表"
    parameters: dict = Field(
        default_factory=lambda: NovelRecommendedParams.model_json_schema()
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        try:
            api = self.api_manager.get_api()
            params = NovelRecommendedParams(**kwargs)
            result = await novel_recommended(api, params)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"获取推荐小说失败: {e}")
            return f"获取推荐小说失败: {str(e)}"


@dataclass
class SortAndSendNovelResultsTool(FunctionTool[AstrAgentContext]):
    """整理小说搜索结果并格式化为HTML卡片"""

    name: str = "sort_and_send_novel_results"
    description: str = (
        "将小说搜索/推荐等工具返回的结果整理为HTML卡片格式。"
        "自动按收藏数从高到低排序，自动处理标签URL转义。"
        "使用方法：将其他小说工具返回的结果JSON序列化后作为novels_json参数传入，"
        "工具会自动将HTML卡片发送给用户，无需再手动发送。"
    )
    parameters: dict = Field(
        default_factory=lambda: SortAndSendNovelResultsParams.model_json_schema()
    )

    def _get_event(self, context):
        try:
            agent_context = context.context if hasattr(context, "context") else context
            if hasattr(context, "event") and context.event:
                return context.event
            elif hasattr(agent_context, "event") and agent_context.event:
                return agent_context.event
        except Exception:
            pass
        return None

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        try:
            params = SortAndSendNovelResultsParams(**kwargs)
            html_result = await sort_and_send_novel_results(params)
            event = self._get_event(context)
            if event and hasattr(event, "send"):
                await event.send(event.plain_result(html_result))
                return "已将格式化的小说 HTML 卡片结果直接发送给用户。"
            return html_result
        except Exception as e:
            logger.error(f"格式化小说结果失败: {e}")
            return f"格式化小说结果失败: {str(e)}"


@dataclass
class PixivSearchNovelAndSendTool(FunctionTool[AstrAgentContext]):
    """搜索小说并直接格式化为HTML卡片"""

    api_manager: Any = None
    name: str = "pixiv_search_novel_and_send"
    description: str = (
        "搜索Pixiv小说并直接输出格式化的HTML卡片。"
        "合并了搜索与格式化步骤，自动按收藏数排序并截取前N个结果。"
        "工具会自动将HTML卡片发送给用户，无需再手动发送。"
    )
    parameters: dict = Field(
        default_factory=lambda: SearchNovelAndSendParams.model_json_schema()
    )

    def _get_event(self, context):
        try:
            agent_context = context.context if hasattr(context, "context") else context
            if hasattr(context, "event") and context.event:
                return context.event
            elif hasattr(agent_context, "event") and agent_context.event:
                return agent_context.event
        except Exception:
            pass
        return None

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        try:
            api = self.api_manager.get_api()
            params = SearchNovelAndSendParams(**kwargs)
            html_result = await search_novel_and_send(api, params)
            event = self._get_event(context)
            if event and hasattr(event, "send"):
                await event.send(event.plain_result(html_result))
                return f"已搜索关键词「{params.word}」并将 HTML 卡片结果直接发送给用户。"
            return html_result
        except Exception as e:
            logger.error(f"搜索小说并格式化失败: {e}")
            return f"搜索小说并格式化失败: {str(e)}"


@dataclass
class PixivNovelRecommendedAndSendTool(FunctionTool[AstrAgentContext]):
    """获取推荐小说并直接格式化为HTML卡片"""

    api_manager: Any = None
    name: str = "pixiv_novel_recommended_and_send"
    description: str = (
        "获取系统推荐小说并直接输出格式化的HTML卡片。"
        "合并了推荐获取与格式化步骤，自动按收藏数排序并截取前N个结果。"
        "工具会自动将HTML卡片发送给用户，无需再手动发送。"
    )
    parameters: dict = Field(
        default_factory=lambda: NovelRecommendedAndSendParams.model_json_schema()
    )

    def _get_event(self, context):
        try:
            agent_context = context.context if hasattr(context, "context") else context
            if hasattr(context, "event") and context.event:
                return context.event
            elif hasattr(agent_context, "event") and agent_context.event:
                return agent_context.event
        except Exception:
            pass
        return None

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        try:
            api = self.api_manager.get_api()
            params = NovelRecommendedAndSendParams(**kwargs)
            html_result = await novel_recommended_and_send(api, params)
            event = self._get_event(context)
            if event and hasattr(event, "send"):
                await event.send(event.plain_result(html_result))
                return "已将推荐小说的 HTML 卡片结果直接发送给用户。"
            return html_result
        except Exception as e:
            logger.error(f"获取推荐小说并格式化失败: {e}")
            return f"获取推荐小说并格式化失败: {str(e)}"


@dataclass
class GetCurrentTimeTool(FunctionTool[AstrAgentContext]):
    """获取当前时间信息"""

    name: str = "get_current_time"
    description: str = (
        "获取当前时间信息，包括当前日期、时区信息以及常用的时间范围建议"
        "（如过去两年、过去一年等）"
    )
    parameters: dict = Field(
        default_factory=lambda: GetCurrentTimeParams.model_json_schema()
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        try:
            params = GetCurrentTimeParams(**kwargs)
            result = await get_current_time(params)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"获取当前时间失败: {e}")
            return f"获取当前时间失败: {str(e)}"


def create_pixiv_novel_tools(api_manager) -> List[FunctionTool]:
    """创建所有 Pixiv LLM 工具"""
    tools = [
        PixivSearchNovelTool(api_manager=api_manager),
        PixivNovelRecommendedTool(api_manager=api_manager),
        SortAndSendNovelResultsTool(),
        PixivSearchNovelAndSendTool(api_manager=api_manager),
        PixivNovelRecommendedAndSendTool(api_manager=api_manager),
        GetCurrentTimeTool(),
    ]
    logger.info(f"已创建 {len(tools)} 个 Pixiv LLM 工具")
    return tools
