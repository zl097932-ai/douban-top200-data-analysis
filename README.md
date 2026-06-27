# 豆瓣电影 Top200 数据分析项目

本项目是一个 Python 课程作业项目，围绕豆瓣电影 Top250 公开榜单的前 200 名电影，完成数据采集、清洗、统计分析、可视化和中文报告生成。项目支持离线复现：在已保存原始 CSV 的基础上，可以不访问网络重新生成清洗数据、图表和报告。

## 项目内容

- 分页采集公开榜单中的前 200 名电影信息。
- 清洗排名、片名、年份、国家/地区、类型、评分、评价人数等字段。
- 拆分国家/地区和类型等多值字段，生成可分析的展开表。
- 生成评分分布、类型分布、国家/地区分布、年代分布、相关关系等 7 张图表。
- 自动生成中文 DOCX 报告，并使用桌面 LibreOffice 导出 PDF。
- 使用 pytest 覆盖页面解析、数据清洗、去重和统计摘要等核心流程。

## 仓库结构

```text
.
├── data/
│   ├── raw/                  # 已保存的 Top200 原始 CSV
│   └── processed/            # 清洗后数据和统计摘要
├── output/
│   ├── figures/              # 自动生成的分析图表
│   ├── logs/                 # 数据处理追溯日志
│   └── 报告/                 # DOCX/PDF 报告
├── src/                      # 爬取、清洗、分析、报告生成代码
├── tests/                    # 自动化测试
├── run_pipeline.py           # 一键运行入口
├── requirements.txt          # Python 依赖
└── README.md
```

## 环境安装

在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

如果只查看源码、数据和报告，不需要安装环境；如果要重新生成 PDF，电脑需要安装桌面版 LibreOffice。

## 运行方式

基于仓库中已保存的原始数据离线复现：

```powershell
.\.venv\Scripts\python.exe run_pipeline.py --skip-fetch --student-name "你的姓名" --student-id "你的学号" --class-name "你的班级"
```

重新访问公开榜单页面并更新数据：

```powershell
.\.venv\Scripts\python.exe run_pipeline.py --fetch --student-name "你的姓名" --student-id "你的学号" --class-name "你的班级"
```

如程序没有自动找到 LibreOffice，可手动指定：

```powershell
.\.venv\Scripts\python.exe run_pipeline.py --skip-fetch --soffice "C:\Program Files\LibreOffice\program\soffice.com"
```

## 主要输出

| 路径 | 内容 |
|---|---|
| `data/raw/douban_top200_raw.csv` | 豆瓣榜单前 200 名原始数据 |
| `data/processed/movies_clean.csv` | 清洗后一电影一行的主表 |
| `data/processed/movies_by_country.csv` | 国家/地区展开分析表 |
| `data/processed/movies_by_genre.csv` | 类型展开分析表 |
| `data/processed/analysis_summary.json` | 统计摘要 |
| `output/figures/` | 自动生成的 7 张 PNG 图表 |
| `output/报告/豆瓣电影Top200数据分析报告.pdf` | 课程提交版报告 |
| `output/报告/豆瓣电影Top200数据分析报告_GitHub展示版.pdf` | 去除个人身份信息的 GitHub 展示版报告 |

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

当前测试覆盖 HTML 页面解析、清洗、去重、国家/地区与类型拆分、统计摘要等核心流程。

## 数据使用说明

数据仅用于课程作业与学习展示。爬虫只访问无需登录的公开列表页，页间随机等待 1.2 至 2.0 秒，单页最多重试 3 次；榜单内容会随网站更新而变化，报告会记录运行时的实际统计结果。

公开仓库中不包含虚拟环境、缓存文件、原始 HTML 页面、渲染中间页图、历史 Top250 旧报告和本地过程日志。
