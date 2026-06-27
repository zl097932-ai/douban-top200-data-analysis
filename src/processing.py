"""数据清洗、统计摘要与静态中文图表生成。"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd
from scipy import stats


TEXT_COLUMNS = ["title", "original_title", "people_info", "country_text", "genre_text", "quote", "detail_url", "source_url", "fetched_at"]


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()


def split_multi_value(value: object) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    return [part for part in (clean_text(item) for item in re.split(r"\s*/\s*", text)) if part]


def normalize_country_name(value: object) -> str:
    """统一国家/地区展示名称，避免括号写法造成重复类别。"""
    return clean_text(value).strip("()（）").strip()


def clean_movies(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """清洗原始主表，并构造国家/地区、类型的展开分析表。"""
    required_columns = {"rank", "title", "year", "rating", "rating_count", "country_text", "genre_text"}
    missing_columns = required_columns.difference(raw_df.columns)
    if missing_columns:
        raise ValueError(f"原始数据缺少字段：{', '.join(sorted(missing_columns))}")

    working = raw_df.copy()
    for column in TEXT_COLUMNS:
        if column in working.columns:
            working[column] = working[column].map(clean_text)
    for column in ["rank", "year", "rating", "rating_count"]:
        working[column] = pd.to_numeric(working[column], errors="coerce")

    input_records = len(working)
    missing_required = working[["rank", "title", "rating"]].isna().any(axis=1) | (working["title"] == "")
    current_year = datetime.now().year
    invalid_range = (
        working["rating"].lt(0)
        | working["rating"].gt(10)
        | working["rating_count"].lt(0)
        | working["rank"].lt(1)
        | working["year"].notna() & (working["year"].lt(1888) | working["year"].gt(current_year))
    )
    invalid_rows = missing_required | invalid_range
    dropped_invalid = int(invalid_rows.sum())
    working = working.loc[~invalid_rows].copy()

    duplicate_rank = int(working.duplicated(subset=["rank"], keep="first").sum())
    working = working.drop_duplicates(subset=["rank"], keep="first")
    duplicate_title_year = int(working.duplicated(subset=["title", "year"], keep="first").sum())
    working = working.drop_duplicates(subset=["title", "year"], keep="first")
    working = working.sort_values("rank").reset_index(drop=True)
    working["rank"] = working["rank"].astype(int)
    working["rating"] = working["rating"].astype(float)
    working["rating_count"] = working["rating_count"].fillna(0).astype(int)
    working["year"] = working["year"].astype("Int64")
    working["decade"] = (working["year"] // 10 * 10).astype("Int64")

    country_df = (
        working.assign(country=working["country_text"].map(lambda value: [normalize_country_name(item) for item in split_multi_value(value)]))
        .explode("country")
        .dropna(subset=["country"])
        .query("country != ''")
        [["rank", "title", "year", "rating", "rating_count", "country"]]
        .reset_index(drop=True)
    )
    genre_df = (
        working.assign(genre=working["genre_text"].map(split_multi_value))
        .explode("genre")
        .dropna(subset=["genre"])
        .query("genre != ''")
        [["rank", "title", "year", "rating", "rating_count", "genre"]]
        .reset_index(drop=True)
    )
    quality = {
        "input_records": input_records,
        "dropped_invalid_records": dropped_invalid,
        "duplicate_rank_removed": duplicate_rank,
        "duplicate_title_year_removed": duplicate_title_year,
        "output_records": int(len(working)),
        "missing_year_after_cleaning": int(working["year"].isna().sum()),
        "missing_country_after_cleaning": int((working["country_text"] == "").sum()),
        "missing_genre_after_cleaning": int((working["genre_text"] == "").sum()),
        "rating_range": [float(working["rating"].min()), float(working["rating"].max())],
        "rank_is_unique": bool(working["rank"].is_unique),
    }
    return working, country_df, genre_df, quality


def _records_from_series(series: pd.Series, value_name: str, limit: int | None = None) -> list[dict[str, Any]]:
    if limit is not None:
        series = series.head(limit)
    return [{value_name: str(index), "count": int(value)} for index, value in series.items()]


def build_summary(clean_df: pd.DataFrame, country_df: pd.DataFrame, genre_df: pd.DataFrame, quality: dict[str, Any]) -> tuple[dict[str, Any], pd.DataFrame]:
    """计算报告和图表共享的统计结果。"""
    genre_counts = genre_df["genre"].value_counts()
    country_counts = country_df["country"].value_counts()
    decade_counts = clean_df.dropna(subset=["decade"]).groupby("decade", observed=True).size().sort_index()
    decade_ratings = clean_df.dropna(subset=["decade"]).groupby("decade", observed=True)["rating"].mean().sort_index()
    decade_table = pd.DataFrame(
        {
            "decade": decade_counts.index.astype(int),
            "movie_count": decade_counts.values.astype(int),
            "average_rating": decade_ratings.reindex(decade_counts.index).round(3).values,
        }
    )
    top_movies = clean_df.sort_values(["rating", "rating_count"], ascending=[False, False]).head(10)
    log_count = (clean_df["rating_count"] + 1).map(math.log10)
    rating_values = clean_df["rating"]
    pearson = stats.pearsonr(rating_values, log_count)
    rating_votes_spearman = stats.spearmanr(rating_values, log_count)
    rank_rating_spearman = stats.spearmanr(clean_df["rank"], rating_values)
    summary = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "quality": quality,
        "overall": {
            "movie_count": int(len(clean_df)),
            "average_rating": round(float(clean_df["rating"].mean()), 3),
            "median_rating": round(float(clean_df["rating"].median()), 3),
            "min_rating": round(float(clean_df["rating"].min()), 3),
            "max_rating": round(float(clean_df["rating"].max()), 3),
            "total_rating_count": int(clean_df["rating_count"].sum()),
            "year_min": int(clean_df["year"].dropna().min()),
            "year_max": int(clean_df["year"].dropna().max()),
            "rating_log_count_correlation": round(float(pearson.statistic), 3),
            "rating_log_count_pearson_p_value": float(pearson.pvalue),
            "rating_log_count_spearman_rho": round(float(rating_votes_spearman.statistic), 3),
            "rating_log_count_spearman_p_value": float(rating_votes_spearman.pvalue),
            "rank_rating_spearman_rho": round(float(rank_rating_spearman.statistic), 3),
            "rank_rating_spearman_p_value": float(rank_rating_spearman.pvalue),
        },
        "top_genres": _records_from_series(genre_counts, "genre", 12),
        "top_countries": _records_from_series(country_counts, "country", 12),
        "decades": decade_table.to_dict(orient="records"),
        "top_movies": [
            {"rank": int(row.rank), "title": row.title, "rating": float(row.rating), "rating_count": int(row.rating_count)}
            for row in top_movies.itertuples(index=False)
        ],
    }
    return summary, decade_table


def write_processed_data(
    clean_df: pd.DataFrame,
    country_df: pd.DataFrame,
    genre_df: pd.DataFrame,
    quality: dict[str, Any],
    summary: dict[str, Any],
    decade_table: pd.DataFrame,
    processed_dir: Path,
) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(processed_dir / "movies_clean.csv", index=False, encoding="utf-8-sig")
    country_df.to_csv(processed_dir / "movies_by_country.csv", index=False, encoding="utf-8-sig")
    genre_df.to_csv(processed_dir / "movies_by_genre.csv", index=False, encoding="utf-8-sig")
    decade_table.to_csv(processed_dir / "decade_summary.csv", index=False, encoding="utf-8-sig")
    (processed_dir / "data_quality_report.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    (processed_dir / "analysis_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def select_chinese_font() -> str:
    available = {font.name for font in font_manager.fontManager.ttflist}
    for name in ["SimSun", "NSimSun", "STSong"]:
        if name in available:
            return name
    raise RuntimeError("未检测到可用宋体；请安装 SimSun（宋体）后重试。")


def _finish_plot(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()


def create_figures(clean_df: pd.DataFrame, country_df: pd.DataFrame, genre_df: pd.DataFrame, figures_dir: Path) -> dict[str, Path]:
    """生成 7 张中文静态图表，返回其语义化路径映射。"""
    font_name = select_chinese_font()
    plt.rcParams.update({"font.family": font_name, "font.sans-serif": [font_name], "axes.unicode_minus": False, "figure.dpi": 120})
    figures_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "rating_distribution": figures_dir / "01_评分分布.png",
        "genre_counts": figures_dir / "02_热门电影类型.png",
        "country_counts": figures_dir / "03_主要制片国家地区.png",
        "decade_counts": figures_dir / "04_不同年代电影数量.png",
        "decade_ratings": figures_dir / "05_不同年代平均评分.png",
        "rating_votes": figures_dir / "06_评分与评价人数关系.png",
        "rank_rating": figures_dir / "07_排名与评分关系.png",
    }
    accent, dark, warm = "#2E74B5", "#1F4D78", "#D97706"

    plt.figure(figsize=(9, 5.2))
    plt.hist(clean_df["rating"], bins=12, color=accent, edgecolor="white")
    plt.axvline(clean_df["rating"].mean(), color=warm, linestyle="--", label=f"平均分：{clean_df['rating'].mean():.2f}")
    plt.title("豆瓣电影 Top200 评分分布")
    plt.xlabel("豆瓣评分")
    plt.ylabel("电影数量")
    plt.legend()
    _finish_plot(paths["rating_distribution"])

    top_genres = genre_df["genre"].value_counts().head(12).sort_values()
    plt.figure(figsize=(9, 6))
    plt.barh(top_genres.index, top_genres.values, color=plt.cm.Blues(np.linspace(0.45, 0.9, len(top_genres))))
    plt.title("Top200 中出现频次最高的电影类型")
    plt.xlabel("电影数量（同一电影可含多种类型）")
    plt.ylabel("电影类型")
    _finish_plot(paths["genre_counts"])

    top_countries = country_df["country"].value_counts().head(12).sort_values()
    plt.figure(figsize=(9, 6))
    plt.barh(top_countries.index, top_countries.values, color=plt.cm.Greens(np.linspace(0.45, 0.9, len(top_countries))))
    plt.title("Top200 的主要制片国家/地区")
    plt.xlabel("电影数量（合拍片可重复计入）")
    plt.ylabel("国家/地区")
    _finish_plot(paths["country_counts"])

    decade_counts = clean_df.dropna(subset=["decade"]).groupby("decade", observed=True).size().sort_index()
    plt.figure(figsize=(12, 5.2))
    plt.bar([f"{int(value)}年代" for value in decade_counts.index], decade_counts.values, color=accent)
    plt.title("不同年代入选 Top200 的电影数量")
    plt.xlabel("上映年代")
    plt.ylabel("电影数量")
    plt.xticks(rotation=0, ha="center")
    _finish_plot(paths["decade_counts"])

    decade_ratings = clean_df.dropna(subset=["decade"]).groupby("decade", observed=True)["rating"].mean().sort_index()
    plt.figure(figsize=(12, 5.2))
    plt.plot([f"{int(value)}年代" for value in decade_ratings.index], decade_ratings.values, marker="o", color=dark, linewidth=2.5)
    plt.title("不同年代入选电影的平均评分")
    plt.xlabel("上映年代")
    plt.ylabel("平均豆瓣评分")
    plt.ylim(max(0, decade_ratings.min() - 0.25), min(10, decade_ratings.max() + 0.25))
    plt.xticks(rotation=0, ha="center")
    _finish_plot(paths["decade_ratings"])

    plt.figure(figsize=(9, 5.5))
    log_rating_count = np.log10(clean_df["rating_count"].to_numpy() + 1)
    plt.scatter(clean_df["rating_count"], clean_df["rating"], s=58, alpha=0.7, color=accent, edgecolors="white", linewidths=0.4)
    slope, intercept = np.polyfit(log_rating_count, clean_df["rating"], 1)
    x_line = np.linspace(log_rating_count.min(), log_rating_count.max(), 100)
    plt.plot(10**x_line - 1, slope * x_line + intercept, color=warm, linewidth=2.2, label="线性趋势（评价人数取对数）")
    plt.xscale("log")
    plt.title("评分与评价人数的关系（横轴为对数刻度）")
    plt.xlabel("评价人数（对数刻度）")
    plt.ylabel("豆瓣评分")
    plt.legend()
    _finish_plot(paths["rating_votes"])

    plt.figure(figsize=(9, 5.5))
    plt.scatter(clean_df["rank"], clean_df["rating"], color=dark, alpha=0.75, s=52, edgecolors="white", linewidths=0.4)
    rank_slope, rank_intercept = np.polyfit(clean_df["rank"], clean_df["rating"], 1)
    rank_line = np.linspace(clean_df["rank"].min(), clean_df["rank"].max(), 100)
    plt.plot(rank_line, rank_slope * rank_line + rank_intercept, color=warm, linewidth=2.2, label="线性趋势")
    plt.gca().invert_xaxis()
    plt.title("榜单排名与豆瓣评分的关系")
    plt.xlabel("榜单排名（左侧为第 1 名）")
    plt.ylabel("豆瓣评分")
    plt.legend()
    _finish_plot(paths["rank_rating"])
    return paths
