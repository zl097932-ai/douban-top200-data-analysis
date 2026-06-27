"""豆瓣电影 Top200（原榜前 200 名）期末作业的一键运行入口。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.crawler import TOP_N, crawl_top200, reparse_saved_pages, write_offline_lineage_log
from src.processing import build_summary, clean_movies, create_figures, write_processed_data
from src.reporting import export_pdf_with_desktop_libreoffice, generate_report, render_pdf_pages


ROOT = Path(__file__).resolve().parent
RAW_CSV = ROOT / "data" / "raw" / "douban_top200_raw.csv"
PAGES_DIR = ROOT / "data" / "raw" / "pages"
LOG_PATH = ROOT / "output" / "logs" / "crawl_log.jsonl"
PROCESSED_DIR = ROOT / "data" / "processed"
FIGURES_DIR = ROOT / "output" / "figures"
REPORT_DIR = ROOT / "output" / "报告"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行豆瓣电影 Top200（原榜前 200 名）数据爬取、清洗、分析、可视化与报告生成流程。")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fetch", action="store_true", help="重新访问公开榜单页面，保存原始 HTML 与 CSV 后继续全流程。")
    mode.add_argument("--skip-fetch", action="store_true", help="不访问网络，直接基于 data/raw 中已保存的原始 CSV 重建全部结果。")
    parser.add_argument("--student-name", default="________", help="封面学生姓名。")
    parser.add_argument("--student-id", default="________", help="封面学号。")
    parser.add_argument("--class-name", default="________", help="封面班级。")
    parser.add_argument("--course", default="大数据技术基础", help="封面课程名称。")
    parser.add_argument("--soffice", default=None, help="桌面 LibreOffice 的 soffice.com 绝对路径；不填则自动查找。")
    return parser.parse_args()


def _validate_outputs(summary: dict, figures: dict[str, Path], pdf_path: Path, rendered_pages: list[Path]) -> None:
    quality = summary["quality"]
    if not quality["rank_is_unique"]:
        raise RuntimeError("数据验证失败：清洗后的排名不唯一。")
    if quality["output_records"] != TOP_N:
        raise RuntimeError(f"数据验证失败：清洗后记录数为 {quality['output_records']}，预期为 {TOP_N}。")
    missing_figures = [str(path) for path in figures.values() if not path.exists() or path.stat().st_size == 0]
    if missing_figures:
        raise RuntimeError(f"图表输出不完整：{missing_figures}")
    if not pdf_path.exists() or not rendered_pages:
        raise RuntimeError("报告输出不完整：未生成 PDF 或页面渲染图。")


def _result_text(summary: dict, docx_path: Path, pdf_path: Path, page_count: int) -> str:
    overall = summary["overall"]
    quality = summary["quality"]
    return "\n".join(
        [
            "豆瓣电影 Top200 数据分析管道运行完成", 
            f"原始记录数：{quality['input_records']}",
            f"清洗后记录数：{quality['output_records']}",
            f"平均评分：{overall['average_rating']:.3f}",
            f"报告 DOCX：{docx_path}",
            f"报告 PDF：{pdf_path}",
            f"PDF 渲染页数：{page_count}",
        ]
    )


def main() -> None:
    args = parse_args()
    if args.fetch:
        crawl_top200(RAW_CSV, PAGES_DIR, LOG_PATH)
    else:
        reparse_saved_pages(RAW_CSV, PAGES_DIR, TOP_N)
        write_offline_lineage_log(LOG_PATH, RAW_CSV, PAGES_DIR, TOP_N)

    raw_df = pd.read_csv(RAW_CSV, encoding="utf-8-sig")
    clean_df, country_df, genre_df, quality = clean_movies(raw_df)
    summary, decade_table = build_summary(clean_df, country_df, genre_df, quality)
    write_processed_data(clean_df, country_df, genre_df, quality, summary, decade_table, PROCESSED_DIR)
    figures = create_figures(clean_df, country_df, genre_df, FIGURES_DIR)

    student = {"name": args.student_name, "student_id": args.student_id, "class_name": args.class_name, "course": args.course}
    raw_preview = raw_df.head(5).to_dict(orient="records")
    docx_path = generate_report(REPORT_DIR / "豆瓣电影Top200数据分析报告.docx", summary, figures, student, ROOT / "src", raw_preview)
    pdf_path = export_pdf_with_desktop_libreoffice(docx_path, REPORT_DIR, args.soffice)
    rendered_pages = render_pdf_pages(pdf_path, ROOT / "output" / "rendered_pages")
    _validate_outputs(summary, figures, pdf_path, rendered_pages)

    result_text = _result_text(summary, docx_path, pdf_path, len(rendered_pages))
    result_path = ROOT / "output" / "运行结果.txt"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(result_text + "\n", encoding="utf-8")
    print(result_text)


if __name__ == "__main__":
    main()
