"""遵守限速策略的豆瓣电影 Top200（原榜前 200 名）列表页爬虫。"""

from __future__ import annotations

import csv
import json
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://movie.douban.com/top250"
TOP_N = 200
PAGE_SIZE = 25
KNOWN_GENRES = {
    "剧情", "喜剧", "动作", "爱情", "科幻", "动画", "悬疑", "惊悚", "恐怖", "纪录片",
    "短片", "情色", "音乐", "歌舞", "家庭", "儿童", "传记", "历史", "战争", "犯罪",
    "西部", "奇幻", "冒险", "灾难", "武侠", "古装", "运动", "真人秀", "脱口秀", "戏曲",
}


class CrawlError(RuntimeError):
    """当分页请求或页面解析不满足预期时抛出。"""


@dataclass(frozen=True)
class CrawlSettings:
    timeout_seconds: int = 20
    max_retries: int = 3
    min_delay_seconds: float = 1.2
    max_delay_seconds: float = 2.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _clean_text(value: str | None) -> str:
    """清理 HTML 中的不可见字符和连续空白。"""
    return re.sub(r"\s+", " ", (value or "").replace("\xa0", " ")).strip()


def _parse_info_text(info_text: str) -> tuple[str, int | None, str, str]:
    """解析列表页压缩展示的人员、年份、国家/地区与类型文本。"""
    cleaned = _clean_text(info_text)
    year_match = re.search(r"(?<!\d)(?:18|19|20)\d{2}(?!\d)", cleaned)
    if not year_match:
        return cleaned, None, "", ""
    people_info = cleaned[:year_match.start()].rstrip(" / ").strip()
    tail = cleaned[year_match.end():]
    tail_parts = [part for part in (_clean_text(item) for item in re.split(r"\s*/\s*", tail)) if part]
    country_words = tail_parts[0].split() if tail_parts else []
    genre_words = " ".join(tail_parts[1:]).split() if len(tail_parts) > 1 else []
    return people_info, int(year_match.group()), " / ".join(country_words), " / ".join(genre_words)


def parse_top250_html(html: str, source_url: str, fetched_at: str) -> list[dict[str, Any]]:
    """解析一个榜单页面，返回结构统一的一电影一行记录。"""
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, Any]] = []

    for item in soup.select("ol.grid_view > li > div.item"):
        rank_tag = item.select_one(".pic em")
        title_tags = item.select(".hd .title")
        # 豆瓣当前页面的评分容器不保证带有 .star 类，评分数字本身更稳定。
        rating_tag = item.select_one(".rating_num")
        info_tag = item.select_one(".bd > p")
        link_tag = item.select_one(".hd a[href]")
        if not all([rank_tag, title_tags, rating_tag, info_tag, link_tag]):
            raise CrawlError("页面中存在无法识别的电影条目，已停止以避免生成不完整数据。")

        titles = [_clean_text(tag.get_text(" ", strip=True)) for tag in title_tags]
        title = titles[0]
        original_title = " / ".join(titles[1:]).lstrip("/ ")
        people_info, year, country_text, genre_text = _parse_info_text(info_tag.get_text(" ", strip=True))

        star_text = _clean_text(rating_tag.parent.get_text(" ", strip=True))
        voters_match = re.search(r"([\d,]+)\s*人评价", star_text)
        quote_tag = item.select_one(".quote span")
        records.append(
            {
                "rank": int(rank_tag.get_text(strip=True)),
                "title": title,
                "original_title": original_title,
                "people_info": people_info,
                "year": year,
                "country_text": country_text,
                "genre_text": genre_text,
                "rating": float(rating_tag.get_text(strip=True)),
                "rating_count": int(voters_match.group(1).replace(",", "")) if voters_match else None,
                "quote": _clean_text(quote_tag.get_text(" ", strip=True)) if quote_tag else "",
                "detail_url": link_tag["href"],
                "source_url": source_url,
                "fetched_at": fetched_at,
            }
        )
    return records


def _write_log(log_path: Path, payload: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _write_raw_csv(records: list[dict[str, Any]], raw_csv_path: Path) -> None:
    raw_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with raw_csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def write_offline_lineage_log(log_path: Path, raw_csv_path: Path, pages_dir: Path, top_n: int = TOP_N) -> None:
    """记录离线复核链路，避免把历史 Top250 联网日志误当作 Top200 采集日志。"""
    expected_pages = top_n // PAGE_SIZE
    page_paths = sorted(pages_dir.glob("top200_*.html")) or sorted(pages_dir.glob("top250_*.html"))
    if len(page_paths) < expected_pages:
        raise CrawlError(f"保存的 HTML 页面不足，无法记录 Top{top_n} 离线复核日志。")

    legacy_log = log_path.with_name("crawl_log_top250_legacy.jsonl")
    if log_path.exists() and not legacy_log.exists():
        existing_log = log_path.read_text(encoding="utf-8")
        if '"records": 250' in existing_log:
            log_path.replace(legacy_log)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("", encoding="utf-8")
    _write_log(
        log_path,
        {
            "timestamp": _utc_now(),
            "event": "offline_reparse_started",
            "scope": f"豆瓣电影 Top250 榜单前 {top_n} 名（Top{top_n}）",
            "source": "已保存的公开列表页 HTML，不访问网络",
            "pages": expected_pages,
        },
    )
    for page_number, page_path in enumerate(page_paths[:expected_pages], start=1):
        _write_log(
            log_path,
            {
                "timestamp": _utc_now(),
                "event": "offline_reparse_ok",
                "page": page_number,
                "start": (page_number - 1) * PAGE_SIZE,
                "records": PAGE_SIZE,
                "saved_page": page_path.name,
            },
        )
    _write_log(
        log_path,
        {
            "timestamp": _utc_now(),
            "event": "offline_reparse_complete",
            "records": top_n,
            "raw_csv": str(raw_csv_path),
        },
    )


def reparse_saved_pages(raw_csv_path: Path, pages_dir: Path, top_n: int = TOP_N) -> list[dict[str, Any]]:
    """从已保存的原始 HTML 页面重建豆瓣原榜前 ``top_n`` 名数据，不访问网络。"""
    if top_n % PAGE_SIZE != 0:
        raise ValueError(f"top_n 必须是 {PAGE_SIZE} 的整数倍。")
    expected_pages = top_n // PAGE_SIZE
    page_paths = sorted(pages_dir.glob("top200_*.html")) or sorted(pages_dir.glob("top250_*.html"))
    if len(page_paths) < expected_pages:
        raise CrawlError(f"保存的 HTML 页面数为 {len(page_paths)}，无法离线重建前 {top_n} 名数据。")
    fetched_at = _utc_now()
    records: list[dict[str, Any]] = []
    for page_number, page_path in enumerate(page_paths[:expected_pages], start=1):
        source_url = f"{BASE_URL}?start={(page_number - 1) * PAGE_SIZE}&filter="
        page_records = parse_top250_html(page_path.read_text(encoding="utf-8"), source_url, fetched_at)
        if len(page_records) != PAGE_SIZE:
            raise CrawlError(f"保存页面 {page_path.name} 解析到 {len(page_records)} 条，预期为 {PAGE_SIZE} 条。")
        records.extend(page_records)
    ranks = [record["rank"] for record in records]
    if len(records) != top_n or len(set(ranks)) != top_n or set(ranks) != set(range(1, top_n + 1)):
        raise CrawlError("离线重建后的记录数或排名唯一性校验失败。")
    _write_raw_csv(records, raw_csv_path)
    return records


def _request_page(session: requests.Session, url: str, settings: CrawlSettings, log_path: Path, start: int) -> str:
    last_error: str | None = None
    for attempt in range(1, settings.max_retries + 1):
        try:
            response = session.get(url, timeout=settings.timeout_seconds)
            response.raise_for_status()
            response.encoding = response.encoding or "utf-8"
            _write_log(
                log_path,
                {"timestamp": _utc_now(), "event": "request_ok", "start": start, "attempt": attempt, "status": response.status_code, "url": url},
            )
            return response.text
        except requests.RequestException as error:
            last_error = str(error)
            _write_log(
                log_path,
                {"timestamp": _utc_now(), "event": "request_failed", "start": start, "attempt": attempt, "url": url, "error": last_error},
            )
            if attempt < settings.max_retries:
                time.sleep(min(2 ** attempt, 8))
    raise CrawlError(f"榜单第 {start // 25 + 1} 页请求失败：{last_error}")


def crawl_top200(raw_csv_path: Path, pages_dir: Path, log_path: Path, settings: CrawlSettings | None = None) -> list[dict[str, Any]]:
    """以低频率爬取豆瓣 Top250 原榜的前 200 名，保存网页、CSV 与 JSONL 日志。"""
    settings = settings or CrawlSettings()
    raw_csv_path.parent.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("", encoding="utf-8")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124 Safari/537.36 CourseDataAnalysis/1.0",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
        }
    )
    fetched_at = _utc_now()
    records: list[dict[str, Any]] = []

    for page_number, start in enumerate(range(0, TOP_N, PAGE_SIZE), start=1):
        url = f"{BASE_URL}?start={start}&filter="
        html = _request_page(session, url, settings, log_path, start)
        (pages_dir / f"top200_{page_number:02d}.html").write_text(html, encoding="utf-8")
        page_records = parse_top250_html(html, url, fetched_at)
        if len(page_records) != PAGE_SIZE:
            raise CrawlError(f"榜单第 {page_number} 页解析到 {len(page_records)} 条，预期为 {PAGE_SIZE} 条。")
        records.extend(page_records)
        _write_log(
            log_path,
            {"timestamp": _utc_now(), "event": "parse_ok", "page": page_number, "start": start, "records": len(page_records)},
        )
        if start < TOP_N - PAGE_SIZE:
            time.sleep(random.uniform(settings.min_delay_seconds, settings.max_delay_seconds))

    ranks = [record["rank"] for record in records]
    if len(records) != TOP_N or len(set(ranks)) != TOP_N or set(ranks) != set(range(1, TOP_N + 1)):
        raise CrawlError(f"爬取完成后的记录校验失败：记录数={len(records)}，唯一排名数={len(set(ranks))}。")

    _write_raw_csv(records, raw_csv_path)
    _write_log(log_path, {"timestamp": _utc_now(), "event": "crawl_complete", "records": len(records), "raw_csv": str(raw_csv_path)})
    return records
