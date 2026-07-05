"""Machine learning extension for the Douban Top200 analysis project."""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.processing import select_chinese_font, split_multi_value


RANDOM_STATE = 42
TOP_GENRE_LIMIT = 12
TOP_COUNTRY_LIMIT = 10


def load_processed_tables(processed_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    movies = pd.read_csv(processed_dir / "movies_clean.csv", encoding="utf-8-sig")
    genres = pd.read_csv(processed_dir / "movies_by_genre.csv", encoding="utf-8-sig")
    countries = pd.read_csv(processed_dir / "movies_by_country.csv", encoding="utf-8-sig")
    return movies, genres, countries


def _multi_hot_from_text(values: pd.Series, selected: list[str], prefix: str) -> pd.DataFrame:
    rows: list[dict[str, int]] = []
    for value in values:
        tokens = set(split_multi_value(value))
        rows.append({f"{prefix}_{name}": int(name in tokens) for name in selected})
    return pd.DataFrame(rows)


def build_feature_matrix(movies: pd.DataFrame, genres: pd.DataFrame, countries: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, list[str], list[str]]:
    top_genres = genres["genre"].value_counts().head(TOP_GENRE_LIMIT).index.tolist()
    top_countries = countries["country"].value_counts().head(TOP_COUNTRY_LIMIT).index.tolist()

    numeric = pd.DataFrame(
        {
            "year": movies["year"].astype(float),
            "movie_age": datetime.now().year - movies["year"].astype(float),
            "log_rating_count": np.log10(movies["rating_count"].astype(float) + 1),
            "genre_count": movies["genre_text"].map(lambda value: len(split_multi_value(value))),
            "country_count": movies["country_text"].map(lambda value: len(split_multi_value(value))),
        }
    )
    genre_features = _multi_hot_from_text(movies["genre_text"], top_genres, "genre")
    country_features = _multi_hot_from_text(movies["country_text"], top_countries, "country")
    features = pd.concat([numeric, genre_features, country_features], axis=1).fillna(0)
    target = movies["rating"].astype(float)
    return features, target, top_genres, top_countries


def _cv_metrics(model, features: pd.DataFrame, target: pd.Series) -> dict[str, float]:
    cv = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    scores = cross_validate(
        model,
        features,
        target,
        cv=cv,
        scoring={
            "mae": "neg_mean_absolute_error",
            "rmse": "neg_root_mean_squared_error",
            "r2": "r2",
        },
    )
    return {
        "mae_mean": round(float(-scores["test_mae"].mean()), 4),
        "mae_std": round(float(scores["test_mae"].std()), 4),
        "rmse_mean": round(float(-scores["test_rmse"].mean()), 4),
        "r2_mean": round(float(scores["test_r2"].mean()), 4),
    }


def evaluate_rating_models(features: pd.DataFrame, target: pd.Series) -> dict[str, Any]:
    models = {
        "Baseline mean rating": DummyRegressor(strategy="mean"),
        "Ridge regression": Pipeline([("scaler", StandardScaler()), ("model", Ridge(alpha=5.0))]),
        "Random forest": RandomForestRegressor(
            n_estimators=350,
            min_samples_leaf=4,
            random_state=RANDOM_STATE,
        ),
    }
    results = {name: _cv_metrics(model, features, target) for name, model in models.items()}
    best_name = min((name for name in results if not name.startswith("Baseline")), key=lambda name: results[name]["mae_mean"])
    baseline_mae = results["Baseline mean rating"]["mae_mean"]
    best_mae = results[best_name]["mae_mean"]
    return {
        "task": "rating prediction",
        "target": "Douban rating",
        "validation": "5-fold cross validation, shuffled with random_state=42",
        "sample_size": int(len(target)),
        "models": results,
        "best_model": best_name,
        "best_mae": best_mae,
        "baseline_mae": baseline_mae,
        "mae_improvement_vs_baseline": round(float(baseline_mae - best_mae), 4),
        "note": "Top200 样本量小且评分范围窄，模型用于探索特征关系，不作为真实评分预测服务。",
    }


def compute_feature_importance(features: pd.DataFrame, target: pd.Series) -> pd.DataFrame:
    model = RandomForestRegressor(
        n_estimators=500,
        min_samples_leaf=4,
        random_state=RANDOM_STATE,
    )
    model.fit(features, target)
    importance = permutation_importance(
        model,
        features,
        target,
        n_repeats=30,
        random_state=RANDOM_STATE,
        scoring="neg_mean_absolute_error",
    )
    table = pd.DataFrame(
        {
            "feature": features.columns,
            "importance": importance.importances_mean,
            "importance_std": importance.importances_std,
        }
    ).sort_values("importance", ascending=False)
    return table.head(12).reset_index(drop=True)


def cluster_movies(movies: pd.DataFrame, features: pd.DataFrame, genres: pd.DataFrame, countries: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cluster_features = features.copy()
    cluster_features["rating"] = movies["rating"].astype(float)
    scaler = StandardScaler()
    scaled = scaler.fit_transform(cluster_features)

    kmeans = KMeans(n_clusters=4, n_init=30, random_state=RANDOM_STATE)
    cluster_labels = kmeans.fit_predict(scaled)

    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    coords = pca.fit_transform(scaled)
    clustered = movies[["rank", "title", "year", "rating", "rating_count", "genre_text", "country_text"]].copy()
    clustered["cluster"] = cluster_labels
    clustered["pca_x"] = coords[:, 0]
    clustered["pca_y"] = coords[:, 1]

    profile_rows = []
    for cluster_id, group in clustered.groupby("cluster"):
        genre_tokens = genres[genres["rank"].isin(group["rank"])]["genre"].value_counts().head(3)
        country_tokens = countries[countries["rank"].isin(group["rank"])]["country"].value_counts().head(3)
        average_year = float(group["year"].mean())
        average_votes = float(group["rating_count"].mean())
        average_rating = float(group["rating"].mean())
        profile = infer_cluster_profile(genre_tokens, country_tokens)
        profile_rows.append(
            {
                "cluster": int(cluster_id),
                "profile": profile,
                "movie_count": int(len(group)),
                "average_rating": round(average_rating, 3),
                "average_year": round(average_year, 1),
                "average_rating_count": int(round(average_votes)),
                "top_genres": "、".join(genre_tokens.index.astype(str)),
                "top_countries": "、".join(country_tokens.index.astype(str)),
                "example_titles": "、".join(group.sort_values(["rating", "rating_count"], ascending=[False, False]).head(4)["title"].astype(str)),
            }
        )

    profiles = pd.DataFrame(profile_rows).sort_values(["average_year", "average_rating"], ascending=[True, False]).reset_index(drop=True)
    profile_map = profiles.set_index("cluster")["profile"].to_dict()
    clustered["cluster_profile"] = clustered["cluster"].map(profile_map)
    return clustered, profiles, pd.DataFrame(coords, columns=["pca_x", "pca_y"])


def infer_cluster_profile(genre_tokens: pd.Series, country_tokens: pd.Series) -> str:
    top_genres = set(genre_tokens.index.astype(str))
    top_countries = set(country_tokens.index.astype(str))
    chinese_regions = {"中国大陆", "中国香港", "中国台湾"}
    if top_countries & chinese_regions:
        return "华语剧情高口碑片"
    if {"动画", "奇幻", "冒险"} & top_genres:
        return "动画奇幻与冒险片"
    if {"悬疑", "惊悚", "犯罪"} & top_genres:
        return "悬疑惊悚与犯罪片"
    if "日本" in top_countries and "美国" not in top_countries:
        return "日本与亚洲口碑片"
    return "欧美剧情经典片"


def _configure_matplotlib() -> None:
    font_name = select_chinese_font()
    plt.rcParams.update({"font.family": font_name, "font.sans-serif": [font_name], "axes.unicode_minus": False, "figure.dpi": 120})


def _finish_plot(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()


def plot_model_metrics(model_summary: dict[str, Any], path: Path) -> None:
    names = list(model_summary["models"].keys())
    values = [model_summary["models"][name]["mae_mean"] for name in names]
    display_names = {
        "Baseline mean rating": "平均分基线",
        "Ridge regression": "岭回归",
        "Random forest": "随机森林",
    }
    colors = ["#9CA3AF", "#2E74B5", "#16A34A"]
    plt.figure(figsize=(8.8, 5.0))
    bars = plt.bar([display_names.get(name, name) for name in names], values, color=colors)
    plt.title("评分预测模型交叉验证 MAE 对比")
    plt.ylabel("MAE（越低越好）")
    plt.ylim(0, max(values) * 1.25)
    for bar, value in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width() / 2, value + 0.006, f"{value:.3f}", ha="center", va="bottom")
    plt.xticks(rotation=0)
    _finish_plot(path)


def plot_feature_importance(importance: pd.DataFrame, path: Path) -> None:
    translated = importance.copy()
    translated["feature"] = translated["feature"].map(translate_feature_name)
    ordered = translated.sort_values("importance")
    plt.figure(figsize=(9, 5.4))
    plt.barh(ordered["feature"], ordered["importance"], color="#2E74B5")
    plt.title("随机森林置换重要性 Top12")
    plt.xlabel("MAE 增量（越高说明影响越大）")
    _finish_plot(path)


def plot_clusters(clustered: pd.DataFrame, profiles: pd.DataFrame, path: Path) -> None:
    plt.figure(figsize=(9.4, 6.0))
    palette = ["#2E74B5", "#16A34A", "#D97706", "#7C3AED"]
    for i, row in enumerate(profiles.itertuples(index=False)):
        group = clustered[clustered["cluster"] == row.cluster]
        plt.scatter(group["pca_x"], group["pca_y"], s=58, alpha=0.75, label=f"{row.profile}（{len(group)}部）", color=palette[i % len(palette)], edgecolors="white", linewidths=0.4)
    plt.title("电影画像分群（PCA 二维投影）")
    plt.xlabel("主成分 1")
    plt.ylabel("主成分 2")
    plt.legend(loc="best", fontsize=9)
    _finish_plot(path)


def translate_feature_name(feature: str) -> str:
    mapping = {
        "year": "上映年份",
        "movie_age": "距今年数",
        "log_rating_count": "评价人数（对数）",
        "genre_count": "类型标签数",
        "country_count": "国家/地区数",
    }
    if feature in mapping:
        return mapping[feature]
    if feature.startswith("genre_"):
        return "类型：" + feature.removeprefix("genre_")
    if feature.startswith("country_"):
        return "地区：" + feature.removeprefix("country_")
    return mapping.get(feature, feature)


def build_summary_payload(model_summary: dict[str, Any], importance: pd.DataFrame, profiles: pd.DataFrame, top_genres: list[str], top_countries: list[str]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "feature_scope": {
            "numeric_features": ["year", "movie_age", "log_rating_count", "genre_count", "country_count"],
            "top_genres": top_genres,
            "top_countries": top_countries,
        },
        "model_summary": model_summary,
        "feature_importance": [
            {
                "feature": row.feature,
                "display_name": translate_feature_name(row.feature),
                "importance": round(float(row.importance), 5),
                "importance_std": round(float(row.importance_std), 5),
            }
            for row in importance.itertuples(index=False)
            if not math.isnan(float(row.importance))
        ],
        "cluster_profiles": profiles.to_dict(orient="records"),
    }


def run_ml_extension(processed_dir: Path, figures_dir: Path) -> dict[str, Path]:
    movies, genres, countries = load_processed_tables(processed_dir)
    features, target, top_genres, top_countries = build_feature_matrix(movies, genres, countries)
    model_summary = evaluate_rating_models(features, target)
    importance = compute_feature_importance(features, target)
    clustered, profiles, _ = cluster_movies(movies, features, genres, countries)
    summary = build_summary_payload(model_summary, importance, profiles, top_genres, top_countries)

    processed_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    summary_path = processed_dir / "ml_summary.json"
    clusters_path = processed_dir / "movie_ml_clusters.csv"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    clustered.drop(columns=["pca_x", "pca_y"]).to_csv(clusters_path, index=False, encoding="utf-8-sig")

    _configure_matplotlib()
    metric_figure = figures_dir / "08_机器学习评分预测对比.png"
    importance_figure = figures_dir / "09_机器学习特征重要性.png"
    cluster_figure = figures_dir / "10_电影画像分群.png"
    plot_model_metrics(model_summary, metric_figure)
    plot_feature_importance(importance, importance_figure)
    plot_clusters(clustered, profiles, cluster_figure)

    return {
        "summary": summary_path,
        "clusters": clusters_path,
        "model_metrics": metric_figure,
        "feature_importance": importance_figure,
        "clusters_figure": cluster_figure,
    }
