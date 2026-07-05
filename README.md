# Douban Movie Top200 Analysis Results

本项目分析了豆瓣电影 Top250 公开榜单前 200 部影片，重点展示榜单电影的评分分布、类型结构、国家/地区来源、年代分布、排名关系，并补充了一个轻量机器学习扩展：用特征工程、交叉验证和分群画像探索电影评分与内容属性之间的关系。仓库后半部分提供完整可复现流程，可以从已保存原始数据重新生成清洗数据、图表、机器学习结果和展示版报告。

## Download Release

原始 CSV、展示版报告和机器学习扩展结果已放在 GitHub Release 中，适合直接下载查看：

- [Release: Douban Top200 results and reproducible dataset](https://github.com/zl097932-ai/douban-top200-data-analysis/releases/tag/v1.0.0-results)
- `douban_top200_raw.csv`：原始榜单 CSV，用于离线复现。
- `douban_top200_github_showcase_report.pdf`：结果展示版 PDF。
- `douban_top200_github_showcase_report.docx`：可编辑的结果展示版 Word。
- `douban_top200_ml_summary.json`：机器学习模型评估、特征重要性和分群摘要。
- `douban_top200_movie_ml_clusters.csv`：每部电影的分群结果。

## Results At A Glance

当前数据集包含 **200** 部电影，年份跨度为 **1936-2023**，平均评分为 **9.01**，累计评价人数约 **1.89 亿**。

| 指标 | 结果 |
|---|---:|
| 电影数量 | 200 |
| 平均评分 | 9.01 |
| 中位评分 | 9.00 |
| 评分范围 | 8.5-9.7 |
| 年份跨度 | 1936-2023 |
| 累计评价人数 | 188,548,326 |
| 出现最多的类型 | 剧情 |
| 出现最多的国家/地区 | 美国 |
| 影片最多的年代 | 2000 年代 |
| 机器学习最佳模型 | 随机森林 |
| 最佳交叉验证 MAE | 0.1459 |
| 电影画像分群 | 4 类 |

## Key Findings

- **高分段集中**：Top200 电影评分集中在 8.8-9.3 区间，整体评分水平很高，平均分为 9.01。
- **剧情片占据主体**：剧情类型出现 150 次，显著高于喜剧、爱情、冒险、奇幻等类型。
- **地区来源集中**：美国电影出现 110 次，英国、日本、中国香港、中国大陆、法国等也有较高出现频次。
- **年代分布明显**：1990 年代、2000 年代和 2010 年代影片构成榜单主体，其中 2000 年代数量最多。
- **排名与评分相关**：排名越靠前评分整体越高；评分与评价人数之间的线性相关性较弱。
- **机器学习结果适合做探索**：随机森林在 5 折交叉验证中 MAE 为 0.1459，优于平均分基线的 0.2034，但由于样本只有 200 条，结论用于解释特征关系，不用于真实评分预测服务。
- **分群结果有展示价值**：KMeans 将电影划分为华语剧情高口碑片、欧美剧情经典片、悬疑惊悚与犯罪片、动画奇幻与冒险片 4 类，适合作为项目结果页的电影画像补充。

## Machine Learning Extension

机器学习部分是 GitHub 展示版扩展，定位为“可复现的数据建模探索”，不是对电影市场的强预测。特征包括年份、距今年数、评价人数对数、类型标签数、国家/地区数，以及热门类型和国家/地区的多热编码。

| 模型 | 5 折 CV MAE | RMSE | R² |
|---|---:|---:|---:|
| 平均分基线 | 0.2034 | 0.2426 | -0.0088 |
| 岭回归 | 0.1700 | 0.2172 | 0.1814 |
| 随机森林 | 0.1459 | 0.1837 | 0.4171 |

特征重要性显示，评价人数（对数）、上映年份、距今年数和类型标签数对模型误差影响最大。这说明榜单内电影的评分差异虽然很窄，但热度、年代和类型结构仍能解释一部分评分波动。

| 分群画像 | 数量 | 平均评分 | 代表影片 |
|---|---:|---:|---|
| 华语剧情高口碑片 | 26 | 8.946 | 霸王别姬、背靠背，脸对脸、活着、鬼子来了 |
| 欧美剧情经典片 | 98 | 9.074 | 肖申克的救赎、泰坦尼克号、阿甘正传、美丽人生 |
| 悬疑惊悚与犯罪片 | 31 | 8.910 | 控方证人、盗梦空间、无间道、蝙蝠侠：黑暗骑士 |
| 动画奇幻与冒险片 | 45 | 8.978 | 千与千寻、星际穿越、大闹天宫、疯狂动物城 |

## Visual Results

### 评分分布

![评分分布](output/figures/01_评分分布.png)

### 热门类型

![热门电影类型](output/figures/02_热门电影类型.png)

### 主要国家/地区

![主要制片国家地区](output/figures/03_主要制片国家地区.png)

### 年代分布

![不同年代电影数量](output/figures/04_不同年代电影数量.png)

### 排名与评分关系

![排名与评分关系](output/figures/07_排名与评分关系.png)

### 机器学习评分预测

![机器学习评分预测对比](output/figures/08_机器学习评分预测对比.png)

### 机器学习特征重要性

![机器学习特征重要性](output/figures/09_机器学习特征重要性.png)

### 电影画像分群

![电影画像分群](output/figures/10_电影画像分群.png)

## What Was Produced

| 输出 | 说明 |
|---|---|
| `data/processed/movies_clean.csv` | 清洗后一电影一行的主数据表 |
| `data/processed/movies_by_genre.csv` | 类型展开表，用于统计多类型电影 |
| `data/processed/movies_by_country.csv` | 国家/地区展开表，用于统计合拍片来源 |
| `data/processed/analysis_summary.json` | 自动生成的统计摘要 |
| `data/processed/data_quality_report.json` | 数据质量检查结果 |
| `data/processed/ml_summary.json` | 机器学习模型评估、特征重要性和分群摘要 |
| `data/processed/movie_ml_clusters.csv` | 每部电影所属分群和画像标签 |
| `output/figures/` | 10 张分析图表，其中 8-10 为机器学习扩展图 |
| `output/报告/豆瓣电影Top200数据分析报告_GitHub展示版.docx` | 面向 GitHub 展示的 Word 报告 |
| `output/报告/豆瓣电影Top200数据分析报告_GitHub展示版.pdf` | 面向 GitHub 展示的 PDF 报告 |

常用交付文件已整理到 [Release assets](https://github.com/zl097932-ai/douban-top200-data-analysis/releases/tag/v1.0.0-results)，其中包含原始 CSV、展示版 PDF、展示版 Word、机器学习摘要和分群 CSV。

## Reproducible Workflow

项目支持两种复现方式：使用仓库内已保存的原始 CSV 离线复现，或重新访问公开榜单页面刷新数据。机器学习扩展基于清洗后的数据运行。

```mermaid
flowchart LR
    A["raw CSV / 公开榜单页面"] --> B["清洗与质量核验"]
    B --> C["统计摘要"]
    B --> D["图表生成"]
    B --> E["机器学习扩展"]
    C --> F["Word/PDF 报告"]
    D --> F
    E --> F
```

### 1. 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. 离线复现基础分析

```powershell
.\.venv\Scripts\python.exe run_pipeline.py --skip-fetch --student-name "你的姓名" --student-id "你的学号" --class-name "你的班级"
```

### 3. 重新采集并刷新基础分析

```powershell
.\.venv\Scripts\python.exe run_pipeline.py --fetch --student-name "你的姓名" --student-id "你的学号" --class-name "你的班级"
```

### 4. 运行机器学习扩展

```powershell
.\.venv\Scripts\python.exe scripts\run_ml_extension.py
```

### 5. 单独重建 GitHub 展示版报告

```powershell
.\.venv\Scripts\python.exe scripts\build_github_showcase_report.py
```

如需导出 PDF，电脑需要安装桌面版 LibreOffice；主流程也支持通过 `--soffice` 指定 `soffice.com` 路径。

## Project Structure

```text
.
├── data/
│   ├── raw/                  # 原始 Top200 CSV
│   └── processed/            # 清洗结果、展开表、质量报告、统计摘要和 ML 结果
├── docs/
│   ├── project_overview.md
│   └── data_dictionary.md
├── output/
│   ├── figures/              # 分析图表与 ML 图表
│   ├── logs/                 # 运行追溯日志
│   └── 报告/                 # DOCX/PDF 报告
├── scripts/
│   ├── build_github_showcase_report.py
│   └── run_ml_extension.py
├── src/
│   ├── crawler.py            # 页面抓取与解析
│   ├── processing.py         # 清洗、统计和图表生成
│   ├── ml_extension.py       # 评分预测、特征重要性和电影分群
│   └── reporting.py          # 课程版报告生成与 PDF 导出
├── tests/                    # 自动化测试
├── run_pipeline.py
└── requirements.txt
```

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

测试覆盖 HTML 页面解析、字段清洗、重复处理、类型/国家地区拆分、统计摘要生成和机器学习特征构造。

## Data Use Notes

数据仅用于课程学习与项目展示。采集逻辑只访问无需登录的公开列表页，并设置随机等待、失败重试和离线复现机制。榜单内容会随网站更新而变化，因此本仓库中的数据和报告代表当次运行结果，不代表电影市场或平台整体分布。机器学习扩展基于小样本榜单数据，结果用于探索和展示建模流程，不应解释为可泛化的评分预测系统。
