from pathlib import Path

import pandas as pd

from src.crawler import parse_top250_html
from src.processing import build_summary, clean_movies, normalize_country_name


def test_parse_sample_page() -> None:
    html = (Path(__file__).parent / "fixtures" / "douban_sample.html").read_text(encoding="utf-8")
    records = parse_top250_html(html, "https://example.com", "2026-06-26T00:00:00+08:00")
    assert len(records) == 2
    assert records[0]["title"] == "样例电影甲"
    assert records[0]["original_title"] == "Sample A"
    assert records[0]["country_text"] == "美国"
    assert records[0]["genre_text"] == "剧情 / 犯罪"
    assert records[1]["year"] == 2001


def test_clean_and_summarize_data() -> None:
    raw = pd.DataFrame(
        [
            {"rank": 1, "title": "甲", "original_title": "", "people_info": "导演: A", "year": 1994, "country_text": "美国", "genre_text": "剧情 / 犯罪", "rating": 9.5, "rating_count": 1000, "quote": "", "detail_url": "x", "source_url": "x", "fetched_at": "x"},
            {"rank": 2, "title": "乙", "original_title": "", "people_info": "导演: B", "year": 2001, "country_text": "中国大陆 / 中国香港", "genre_text": "喜剧", "rating": 8.8, "rating_count": 500, "quote": "", "detail_url": "y", "source_url": "x", "fetched_at": "x"},
            {"rank": 2, "title": "乙（重复）", "original_title": "", "people_info": "导演: B", "year": 2001, "country_text": "中国大陆", "genre_text": "喜剧", "rating": 8.8, "rating_count": 500, "quote": "", "detail_url": "z", "source_url": "x", "fetched_at": "x"},
        ]
    )
    clean, countries, genres, quality = clean_movies(raw)
    summary, decade_table = build_summary(clean, countries, genres, quality)
    assert len(clean) == 2
    assert quality["duplicate_rank_removed"] == 1
    assert set(countries["country"]) == {"美国", "中国大陆", "中国香港"}
    assert summary["overall"]["movie_count"] == 2
    assert len(decade_table) == 2


def test_normalize_country_name_removes_parenthetical_variant() -> None:
    assert normalize_country_name("(中国大陆)") == "中国大陆"
    assert normalize_country_name("（中国大陆）") == "中国大陆"


def test_clean_movies_keeps_missing_original_title_blank() -> None:
    raw = pd.DataFrame(
        [
            {"rank": 1, "title": "只有中文名", "original_title": float("nan"), "people_info": "导演: A", "year": 2000, "country_text": "中国大陆", "genre_text": "剧情", "rating": 9.0, "rating_count": 100, "quote": "", "detail_url": "x", "source_url": "x", "fetched_at": "x"},
        ]
    )
    clean, _, _, _ = clean_movies(raw)
    assert clean.loc[0, "original_title"] == ""
    assert "nan" not in clean["original_title"].tolist()
