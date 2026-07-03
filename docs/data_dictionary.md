# Data Dictionary

## 原始数据

### `data/raw/douban_top200_raw.csv`

| 字段 | 类型 | 说明 |
|---|---|---|
| `rank` | integer | 榜单排名，范围为 1-200。 |
| `title` | string | 中文片名或页面主标题。 |
| `original_title` | string | 原始片名或外文片名。 |
| `people_info` | string | 导演、主演等页面文本。 |
| `year` | integer | 影片年份。 |
| `country_text` | string | 页面中的国家/地区文本，可能包含多个值。 |
| `genre_text` | string | 页面中的类型文本，可能包含多个值。 |
| `rating` | float | 豆瓣评分。 |
| `rating_count` | integer | 评价人数。 |
| `quote` | string | 榜单短评或引用文本。 |
| `detail_url` | string | 电影详情页链接。 |
| `source_url` | string | 榜单来源页链接。 |
| `fetched_at` | datetime string | 本次采集时间。 |

## 清洗数据

### `data/processed/movies_clean.csv`

| 字段 | 类型 | 说明 |
|---|---|---|
| `rank` | integer | 清洗后的唯一排名。 |
| `title` | string | 标准化后的片名。 |
| `original_title` | string | 原始片名。 |
| `people_info` | string | 主创信息文本。 |
| `year` | integer | 影片年份。 |
| `country_text` | string | 原始国家/地区文本。 |
| `genre_text` | string | 原始类型文本。 |
| `rating` | float | 评分。 |
| `rating_count` | integer | 评价人数。 |
| `quote` | string | 页面短评。 |
| `detail_url` | string | 详情页链接。 |
| `source_url` | string | 来源页链接。 |
| `fetched_at` | datetime string | 采集时间。 |
| `decade` | integer | 年代分组，例如 1990、2000。 |

## 展开表

### `data/processed/movies_by_genre.csv`

一部电影可能有多个类型，因此该表采用一电影多行结构。

| 字段 | 类型 | 说明 |
|---|---|---|
| `rank` | integer | 电影排名。 |
| `title` | string | 片名。 |
| `year` | integer | 年份。 |
| `rating` | float | 评分。 |
| `rating_count` | integer | 评价人数。 |
| `genre` | string | 单个类型标签。 |

### `data/processed/movies_by_country.csv`

一部电影可能对应多个国家/地区，因此该表采用一电影多行结构。

| 字段 | 类型 | 说明 |
|---|---|---|
| `rank` | integer | 电影排名。 |
| `title` | string | 片名。 |
| `year` | integer | 年份。 |
| `rating` | float | 评分。 |
| `rating_count` | integer | 评价人数。 |
| `country` | string | 单个国家或地区标签。 |

## 汇总文件

| 文件 | 说明 |
|---|---|
| `data/processed/analysis_summary.json` | 统计摘要，包括评分、年份、类型、国家/地区和相关关系。 |
| `data/processed/data_quality_report.json` | 数据质量检查结果，包括记录数、缺失值、重复情况和评分范围。 |
| `data/processed/decade_summary.csv` | 按年代聚合的电影数量和平均评分。 |

## 输出图表

| 文件 | 说明 |
|---|---|
| `output/figures/01_评分分布.png` | Top200 评分分布。 |
| `output/figures/02_热门电影类型.png` | 出现次数最多的电影类型。 |
| `output/figures/03_主要制片国家地区.png` | 出现次数最多的国家/地区。 |
| `output/figures/04_不同年代电影数量.png` | 不同年代电影数量。 |
| `output/figures/05_不同年代平均评分.png` | 不同年代平均评分。 |
| `output/figures/06_评分与评价人数关系.png` | 评分与评价人数关系。 |
| `output/figures/07_排名与评分关系.png` | 排名与评分关系。 |
