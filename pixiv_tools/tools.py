"""
Pixiv 工具函数
从 pixiv-mcp 项目移植，改为接收 api 实例作为参数
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from pixivpy3 import AppPixivAPI
from pydantic import BaseModel, Field


# ==================== Pydantic Models ====================

class SearchNovelParams(BaseModel):
    word: str = Field(description="搜索关键词")
    search_target: str = Field(
        default="partial_match_for_tags",
        description="搜索类型: partial_match_for_tags(标签部分匹配), exact_match_for_tags(标签完全匹配), text(正文), keyword(关键词)"
    )
    sort: str = Field(default="date_desc", description="排序方式: date_desc(最新), date_asc(最旧)")
    start_date: Optional[str] = Field(default=None, description="搜索的时间范围起点，格式: YYYY-MM-DD (如 2026-03-06)。如果需要按范围过滤，强烈要求填入正确的日期字符串，绝对不能传null")
    end_date: Optional[str] = Field(default=None, description="搜索的时间范围终点，格式: YYYY-MM-DD (如 2026-03-13)。如果需要按范围过滤，强烈要求填入正确的日期字符串，绝对不能传null")
    count: int = Field(default=20, description="返回结果数，默认为20", ge=1, le=100)


class NovelRecommendedParams(BaseModel):
    count: int = Field(default=20, description="返回结果数，默认为20", ge=1, le=100)


class SortAndSendNovelResultsParams(BaseModel):
    """整理并格式化小说搜索结果为HTML卡片"""
    novels_json: str = Field(description="小说搜索结果的JSON字符串（从其他小说相关工具获取的原始结果，直接JSON序列化后传入）")
    sort_by_bookmarks: bool = Field(default=True, description="是否按收藏数(total_bookmarks)从高到低排序，默认为True")
    top_n: int = Field(default=20, description="排序后最多显示的结果数量，默认为20", ge=1)


class SearchNovelAndSendParams(BaseModel):
    """搜索小说并直接格式化为HTML卡片"""
    word: str = Field(description="搜索关键词")
    search_target: str = Field(
        default="partial_match_for_tags",
        description="搜索类型: partial_match_for_tags(标签部分匹配), exact_match_for_tags(标签完全匹配), text(正文), keyword(关键词)"
    )
    sort: str = Field(default="date_desc", description="排序方式: date_desc(最新), date_asc(最旧)")
    start_date: Optional[str] = Field(default=None, description="搜索的时间范围起点，格式: YYYY-MM-DD (如 2026-03-06)。如果需要按范围过滤，强烈要求填入正确的日期字符串，绝对不能传null")
    end_date: Optional[str] = Field(default=None, description="搜索的时间范围终点，格式: YYYY-MM-DD (如 2026-03-13)。如果需要按范围过滤，强烈要求填入正确的日期字符串，绝对不能传null")
    count: int = Field(default=20, description="从API获取的结果数，默认为20", ge=1, le=100)
    sort_by_bookmarks: bool = Field(default=True, description="是否按收藏数从高到低排序，默认为True")
    top_n: int = Field(default=20, description="排序后最多显示的结果数量，默认为20", ge=1)


class NovelRecommendedAndSendParams(BaseModel):
    """获取推荐小说并直接格式化为HTML卡片"""
    count: int = Field(default=20, description="从API获取的结果数，默认为20", ge=1, le=100)
    sort_by_bookmarks: bool = Field(default=True, description="是否按收藏数从高到低排序，默认为True")
    top_n: int = Field(default=20, description="排序后最多显示的结果数量，默认为20", ge=1)


class GetCurrentTimeParams(BaseModel):
    """获取当前时间参数（无需参数）"""
    pass


# ==================== Helper Functions ====================

def _render_novel_cards(novels: List[Dict[str, Any]], sort_by_bookmarks: bool = True, top_n: int = 20) -> str:
    """内部辅助函数：将小说列表排序并渲染为HTML卡片"""
    if not novels:
        return "没有找到小说结果。"

    # 按收藏数排序
    if sort_by_bookmarks:
        novels.sort(key=lambda x: x.get("total_bookmarks", 0), reverse=True)

    # 截取前N个
    novels = novels[:top_n]

    cards = []
    for novel in novels:
        novel_id = novel.get("id", "")
        title = novel.get("title", "无标题")
        caption = novel.get("caption", "") or ""
        total_bookmarks = novel.get("total_bookmarks", 0)

        # 用户信息
        user_info = novel.get("user", {})
        author_name = user_info.get("name", "未知作者")
        author_id = user_info.get("id", "")

        # 系列信息
        series_info = novel.get("series", None)

        # 标签处理：将 / 替换为 %2F
        tags = novel.get("tags", [])
        tag_links = []
        for tag in tags:
            tag_escaped = str(tag).replace("/", "%2F")
            tag_links.append(
                f'<a href="https://www.pixiv.net/tags/{tag_escaped}/novels" '
                f'target="_blank" style="display: inline-block; text-decoration: none; '
                f'background-color: rgba(128,128,128,0.12); padding: 2px 8px; '
                f'border-radius: 6px; margin: 2px 3px;">{tag}</a>'
            )

        # 构建链接
        work_link = f"https://www.pixiv.net/novel/show.php?id={novel_id}"
        author_link = f"https://www.pixiv.net/users/{author_id}"

        # 获取图片 URL 并转换为反代 URL
        image_urls = novel.get("image_urls", {})
        cover_url = image_urls.get("large") or image_urls.get("medium") or ""
        proxied_cover_url = _get_proxied_image_url(cover_url)

        # 构建HTML卡片 (Flexbox左右布局)
        card_html = '<div style="border: 1px solid rgba(128,128,128,0.3); border-radius: 10px; padding: 8px; margin-bottom: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.05); display: flex; gap: 8px; align-items: flex-start;">\n'

        # ================= 左侧：封面和收藏数 =================
        card_html += '  <div style="flex: 0 0 60px; display: flex; flex-direction: column; gap: 6px; align-items: center;">\n'
        # 封面图片
        if proxied_cover_url:
            card_html += f'    <img src="{proxied_cover_url}" alt="封面" style="width: 100%; border-radius: 6px; object-fit: contain; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">\n'
        # 收藏数
        card_html += f'    <div style="font-size: 0.7em; text-align: center;">❤️ {total_bookmarks}</div>\n'
        card_html += '  </div>\n'

        # ================= 右侧：标题、系列名、作者、标签、简介 =================
        card_html += '  <div style="flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 6px;">\n'
        
        # 系列行（放置在最上方，仅在有系列时显示）
        if series_info and series_info.get("id"):
            series_id = series_info.get("id", "")
            series_title = series_info.get("title", "")
            series_link = f"https://www.pixiv.net/novel/series/{series_id}"
            card_html += f'    <div style="font-size: 0.9em; word-break: break-all;"><b>📚 系列：</b><a href="{series_link}" target="_blank" style="text-decoration: none; color: gray;">{series_title}</a></div>\n'
        
        # 标题
        card_html += f'    <h3 style="margin: 0; font-size: 1.1em;"><a href="{work_link}" target="_blank" style="text-decoration: none; color: black; word-break: break-all;">{title}</a></h3>\n'

        # 作者
        card_html += f'    <div style="font-size: 0.9em; word-break: break-all;"><b>👤 作者：</b><a href="{author_link}" target="_blank" style="text-decoration: none; color: #337ab7;">{author_name}</a></div>\n'

        # 标签
        tags_html = " ".join(tag_links)
        card_html += f'    <div style="font-size: 0.7em; line-height: 1.4; word-break: break-all;"><b>🏷️ 标签：</b>{tags_html}</div>\n'

        # 简介（可折叠）
        if caption:
            card_html += f'    <details style="font-size: 0.7em;"><summary style="cursor: pointer; color: #555;"><b>📝 点击展开简介</b></summary><div style="margin-top: 8px; padding: 10px; background-color: rgba(128,128,128,0.08); border-radius: 8px; white-space: pre-wrap; line-height: 1.5; word-break: break-word;">{caption}</div></details>\n'

        card_html += '  </div>\n'
        card_html += '</div>'
        cards.append(card_html)

    return "\n\n---\n\n".join(cards)


def _get_proxied_image_url(url: str) -> str:
    """将原始 Pixiv 图片 URL 转换为反代 URL 以绕过防盗链"""
    if not url:
        return ""
    if "i.pximg.net" in url:
        return url.replace("i.pximg.net", "i.pixiv.re")
    return url


def _parse_novel(novel) -> Dict[str, Any]:
    """将 pixivpy3 的 novel 对象转为字典"""
    return {
        "id": novel.id,
        "title": novel.title,
        "caption": novel.caption,
        "image_urls": {
            "large": getattr(novel.image_urls, "large", ""),
            "medium": getattr(novel.image_urls, "medium", ""),
        } if hasattr(novel, "image_urls") else {},
        "user": {
            "id": novel.user.id,
            "name": novel.user.name,
        },
        "tags": [tag.name for tag in novel.tags],
        "total_view": novel.total_view,
        "total_bookmarks": novel.total_bookmarks,
        "is_original": novel.is_original if hasattr(novel, 'is_original') else False,
        "series": {
            "id": novel.series.id,
            "title": novel.series.title,
        } if hasattr(novel, 'series') and novel.series else None,
    }


# ==================== Tool Functions ====================

async def search_novel(api: AppPixivAPI, params: SearchNovelParams) -> List[Dict[str, Any]]:
    """搜索小说"""
    try:
        result = await asyncio.to_thread(
            api.search_novel,
            params.word,
            search_target=params.search_target,
            sort=params.sort,
            start_date=params.start_date,
            end_date=params.end_date,
        )

        if not hasattr(result, 'novels') or not result.novels:
            return []

        return [_parse_novel(novel) for novel in result.novels[:params.count]]

    except Exception as e:
        raise Exception(f"搜索小说失败: {str(e)}")


async def novel_recommended(api: AppPixivAPI, params: NovelRecommendedParams) -> List[Dict[str, Any]]:
    """获取推荐小说"""
    try:
        result = await asyncio.to_thread(api.novel_recommended)

        if not hasattr(result, 'novels') or not result.novels:
            return []

        return [_parse_novel(novel) for novel in result.novels[:params.count]]

    except Exception as e:
        raise Exception(f"获取推荐小说失败: {str(e)}")


async def sort_and_send_novel_results(params: SortAndSendNovelResultsParams) -> str:
    """整理小说搜索结果并格式化为HTML卡片"""
    try:
        novels = json.loads(params.novels_json)
        if not isinstance(novels, list):
            raise ValueError("输入必须是小说结果的JSON数组")
        return _render_novel_cards(novels, params.sort_by_bookmarks, params.top_n)
    except json.JSONDecodeError as e:
        raise Exception(f"JSON解析失败: {str(e)}")
    except Exception as e:
        raise Exception(f"格式化小说结果失败: {str(e)}")


async def search_novel_and_send(api: AppPixivAPI, params: SearchNovelAndSendParams) -> str:
    """搜索小说并直接格式化为HTML卡片"""
    try:
        result = await asyncio.to_thread(
            api.search_novel,
            params.word,
            search_target=params.search_target,
            sort=params.sort,
            start_date=params.start_date,
            end_date=params.end_date,
        )

        if not hasattr(result, 'novels') or not result.novels:
            return "没有找到小说结果。"

        novels = [_parse_novel(novel) for novel in result.novels[:params.count]]
        return _render_novel_cards(novels, params.sort_by_bookmarks, params.top_n)

    except Exception as e:
        raise Exception(f"搜索小说并格式化失败: {str(e)}")


async def novel_recommended_and_send(api: AppPixivAPI, params: NovelRecommendedAndSendParams) -> str:
    """获取推荐小说并直接格式化为HTML卡片"""
    try:
        result = await asyncio.to_thread(api.novel_recommended)

        if not hasattr(result, 'novels') or not result.novels:
            return "没有找到推荐小说。"

        novels = [_parse_novel(novel) for novel in result.novels[:params.count]]
        return _render_novel_cards(novels, params.sort_by_bookmarks, params.top_n)

    except Exception as e:
        raise Exception(f"获取推荐小说并格式化失败: {str(e)}")


async def get_current_time(params: GetCurrentTimeParams) -> Dict[str, Any]:
    """获取当前时间信息"""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    local_now = datetime.now()

    return {
        "current_utc": now.isoformat(),
        "current_local": local_now.isoformat(),
        "current_date": now.strftime("%Y-%m-%d"),
        "current_year": now.year,
        "current_month": now.month,
        "current_day": now.day,
        "timezone_info": str(local_now.astimezone().tzinfo),
        "IMPORTANT_MESSAGE": f"今天是 {now.strftime('%Y-%m-%d')}"
    }
