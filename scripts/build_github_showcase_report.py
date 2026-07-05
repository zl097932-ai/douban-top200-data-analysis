"""Build the GitHub showcase DOCX report for the Douban Top200 project."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "output" / "figures"
REPORT = ROOT / "output" / "报告" / "豆瓣电影Top200数据分析报告_GitHub展示版.docx"

NAVY = "0B2545"
BLUE = "2E74B5"
SOFT_BLUE = "E8EEF5"
LIGHT_GRAY = "F2F4F7"
BODY = "333333"
MUTED = "666666"
FONT_LATIN = "Calibri"
FONT_CJK = "Microsoft YaHei"
MODEL_DISPLAY_NAMES = {
    "Baseline mean rating": "平均分基线",
    "Ridge regression": "岭回归",
    "Random forest": "随机森林",
}


def set_run_font(run, size: float | None = None, bold: bool | None = None, color: str | None = None) -> None:
    run.font.name = FONT_LATIN
    run._element.rPr.rFonts.set(qn("w:ascii"), FONT_LATIN)
    run._element.rPr.rFonts.set(qn("w:hAnsi"), FONT_LATIN)
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CJK)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def set_style(style, size: float, color: str, bold: bool, before: float, after: float, line_spacing: float) -> None:
    style.font.name = FONT_LATIN
    style._element.rPr.rFonts.set(qn("w:ascii"), FONT_LATIN)
    style._element.rPr.rFonts.set(qn("w:hAnsi"), FONT_LATIN)
    style._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CJK)
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = RGBColor.from_string(color)
    style.paragraph_format.space_before = Pt(before)
    style.paragraph_format.space_after = Pt(after)
    style.paragraph_format.line_spacing = line_spacing


def set_cell_fill(cell, fill: str) -> None:
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    cell._tc.get_or_add_tcPr().append(shading)


def set_cell_margins(cell, top: int = 80, start: int = 120, bottom: int = 80, end: int = 120) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    margins = tc_pr.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        tc_pr.append(margins)
    for side, value in {"top": top, "start": start, "bottom": bottom, "end": end}.items():
        node = margins.find(qn(f"w:{side}"))
        if node is None:
            node = OxmlElement(f"w:{side}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths: list[float]) -> None:
    table.autofit = False
    table.allow_autofit = False
    widths_dxa = [round(width * 1440) for width in widths]
    tbl_pr = table._tbl.tblPr

    tbl_w = tbl_pr.first_child_found_in("w:tblW")
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(sum(widths_dxa)))
    tbl_w.set(qn("w:type"), "dxa")

    layout = tbl_pr.first_child_found_in("w:tblLayout")
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tbl_pr.append(layout)
    layout.set(qn("w:type"), "fixed")

    indent = tbl_pr.first_child_found_in("w:tblInd")
    if indent is None:
        indent = OxmlElement("w:tblInd")
        tbl_pr.append(indent)
    indent.set(qn("w:w"), "120")
    indent.set(qn("w:type"), "dxa")

    for grid_column, width_dxa in zip(table._tbl.tblGrid.gridCol_lst, widths_dxa):
        grid_column.set(qn("w:w"), str(width_dxa))

    for row in table.rows:
        for cell, width_dxa in zip(row.cells, widths_dxa):
            cell.width = Inches(width_dxa / 1440)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.first_child_found_in("w:tcW")
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(width_dxa))
            tc_w.set(qn("w:type"), "dxa")
            set_cell_margins(cell)


def style_table(table, widths: list[float]) -> None:
    set_table_geometry(table, widths)
    for i, row in enumerate(table.rows):
        for cell in row.cells:
            if i == 0:
                set_cell_fill(cell, LIGHT_GRAY)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.1
                for run in paragraph.runs:
                    set_run_font(run, 10.5, bold=(i == 0), color=NAVY if i == 0 else BODY)


def add_paragraph(doc: Document, text: str, *, style: str | None = None, bold_lead: str | None = None) -> None:
    paragraph = doc.add_paragraph(style=style)
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph.paragraph_format.line_spacing = 1.1
    if bold_lead and text.startswith(bold_lead):
        lead = paragraph.add_run(bold_lead)
        set_run_font(lead, 11, True, NAVY)
        rest = paragraph.add_run(text[len(bold_lead) :])
        set_run_font(rest, 11, False, BODY)
        return
    run = paragraph.add_run(text)
    set_run_font(run, 11, False, BODY)


def add_bullets(doc: Document, items: Iterable[str]) -> None:
    for item in items:
        paragraph = doc.add_paragraph(style="List Bullet")
        paragraph.paragraph_format.space_after = Pt(4)
        paragraph.paragraph_format.line_spacing = 1.1
        run = paragraph.add_run(item)
        set_run_font(run, 10.5, False, BODY)


def add_key_value_table(doc: Document, rows: list[tuple[str, str]], widths: list[float] | None = None) -> None:
    widths = widths or [1.8, 4.7]
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "项目"
    table.rows[0].cells[1].text = "说明"
    for label, value in rows:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = value
    style_table(table, widths)


def add_category_matrix(doc: Document, genres: pd.Series, countries: pd.Series) -> None:
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    headers = ["类型", "出现次数", "国家/地区", "出现次数"]
    for cell, header in zip(table.rows[0].cells, headers):
        cell.text = header
    pairs = list(zip(genres.items(), countries.items()))
    for (genre, genre_count), (country, country_count) in pairs:
        cells = table.add_row().cells
        cells[0].text = str(genre)
        cells[1].text = f"{genre_count} 次"
        cells[2].text = str(country)
        cells[3].text = f"{country_count} 次"
    style_table(table, [1.8, 1.2, 2.1, 1.4])


def add_ml_model_table(doc: Document, models: dict[str, dict[str, float]]) -> None:
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    headers = ["模型", "MAE", "RMSE", "R²"]
    for cell, header in zip(table.rows[0].cells, headers):
        cell.text = header
    for model_name, values in models.items():
        cells = table.add_row().cells
        cells[0].text = MODEL_DISPLAY_NAMES.get(model_name, model_name)
        cells[1].text = f"{values['mae_mean']:.4f}"
        cells[2].text = f"{values['rmse_mean']:.4f}"
        cells[3].text = f"{values['r2_mean']:.4f}"
    style_table(table, [2.4, 1.3, 1.3, 1.5])


def add_cluster_profile_table(doc: Document, profiles: list[dict]) -> None:
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    headers = ["分群画像", "数量", "平均评分", "代表影片"]
    for cell, header in zip(table.rows[0].cells, headers):
        cell.text = header
    for profile in profiles:
        cells = table.add_row().cells
        cells[0].text = str(profile["profile"])
        cells[1].text = str(profile["movie_count"])
        cells[2].text = f"{profile['average_rating']:.3f}"
        cells[3].text = str(profile["example_titles"])
    style_table(table, [1.6, 0.8, 0.9, 3.2])


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("第 ")
    set_run_font(run, 9, False, MUTED)
    fld_run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = "PAGE"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    fld_run._r.append(begin)
    fld_run._r.append(instruction)
    fld_run._r.append(end)
    run = paragraph.add_run(" 页")
    set_run_font(run, 9, False, MUTED)


def add_caption(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(8)
    run = paragraph.add_run(text)
    set_run_font(run, 9, False, MUTED)


def load_data() -> dict:
    movies = pd.read_csv(PROCESSED / "movies_clean.csv", encoding="utf-8-sig")
    genres = pd.read_csv(PROCESSED / "movies_by_genre.csv", encoding="utf-8-sig")
    countries = pd.read_csv(PROCESSED / "movies_by_country.csv", encoding="utf-8-sig")
    decades = pd.read_csv(PROCESSED / "decade_summary.csv", encoding="utf-8-sig")
    ml_summary_path = PROCESSED / "ml_summary.json"
    ml_summary = json.loads(ml_summary_path.read_text(encoding="utf-8")) if ml_summary_path.exists() else None
    return {
        "movies": movies,
        "genres": genres,
        "countries": countries,
        "decades": decades,
        "top_genres": genres["genre"].value_counts().head(8),
        "top_countries": countries["country"].value_counts().head(8),
        "ml_summary": ml_summary,
    }


def configure_document(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    set_style(doc.styles["Normal"], 11, BODY, False, 0, 6, 1.1)
    set_style(doc.styles["Heading 1"], 16, BLUE, True, 16, 8, 1.1)
    set_style(doc.styles["Heading 2"], 13, BLUE, True, 12, 6, 1.1)
    set_style(doc.styles["Heading 3"], 12, NAVY, True, 8, 4, 1.1)

    footer = section.footer.paragraphs[0]
    add_page_number(footer)


def build_report() -> Path:
    data = load_data()
    movies = data["movies"]
    decades = data["decades"]
    ml_summary = data["ml_summary"]

    doc = Document()
    configure_document(doc)
    doc.core_properties.author = "GitHub Showcase"
    doc.core_properties.title = "豆瓣电影 Top200 数据分析项目展示报告"
    doc.core_properties.subject = "Python 数据采集、清洗、分析与可视化"

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(4)
    run = title.add_run("豆瓣电影 Top200 数据分析项目")
    set_run_font(run, 24, True, NAVY)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(16)
    run = subtitle.add_run("结果展示在前，复现流程在后")
    set_run_font(run, 12, False, MUTED)

    doc.add_heading("1. 结果总览", level=1)
    add_paragraph(
        doc,
        "本项目分析豆瓣电影 Top250 公开榜单前 200 部影片，重点呈现评分分布、类型结构、国家/地区来源、年代分布和排名关系。下表为本次数据快照的核心结果。",
    )
    add_key_value_table(
        doc,
        [
            ("电影数量", f"{len(movies)} 部"),
            ("年份跨度", f"{int(movies['year'].min())}-{int(movies['year'].max())}"),
            ("平均评分", f"{movies['rating'].mean():.2f}"),
            ("中位评分", f"{movies['rating'].median():.2f}"),
            ("评分范围", f"{movies['rating'].min():.1f}-{movies['rating'].max():.1f}"),
            ("累计评价人数", f"{int(movies['rating_count'].sum()):,}"),
            ("出现最多的类型", str(data["top_genres"].index[0])),
            ("出现最多的国家/地区", str(data["top_countries"].index[0])),
            ("数量最多的年代", f"{int(decades.sort_values('movie_count', ascending=False).iloc[0]['decade'])} 年代"),
        ],
    )

    doc.add_heading("2. 主要发现", level=1)
    findings = [
        "Top200 电影评分集中在 8.8-9.3 区间，整体评分水平很高。",
        "剧情片出现 150 次，是榜单中最突出的类型标签。",
        "美国电影出现 110 次，在国家/地区来源中占比最高。",
        "1990 年代、2000 年代和 2010 年代影片构成榜单主体，其中 2000 年代数量最多。",
        "排名越靠前评分整体越高；评分与评价人数之间的线性相关性较弱。",
    ]
    if ml_summary:
        model_summary = ml_summary["model_summary"]
        findings.append(
            f"机器学习扩展中，{MODEL_DISPLAY_NAMES.get(model_summary['best_model'], model_summary['best_model'])} 的 5 折交叉验证 MAE 为 {model_summary['best_mae']:.4f}，优于平均分基线 {model_summary['baseline_mae']:.4f}。"
        )
        findings.append("KMeans 分群形成华语剧情、欧美剧情、悬疑惊悚、动画奇幻等电影画像，可作为结果展示补充。")
    add_bullets(doc, findings)

    doc.add_heading("3. 类型与地区结构", level=1)
    add_paragraph(doc, "类型分布显示，剧情片是 Top200 中最主要的标签，喜剧、爱情、冒险、奇幻和犯罪等类型也具有较高出现频次。国家/地区分布中，美国电影数量最多，日本、英国、中国香港、中国大陆和法国等也形成较明显的代表性。")
    add_category_matrix(doc, data["top_genres"], data["top_countries"])

    doc.add_section(WD_SECTION_START.NEW_PAGE)
    if ml_summary:
        doc.add_heading("4. 机器学习探索", level=1)
        model_summary = ml_summary["model_summary"]
        add_paragraph(
            doc,
            "该扩展使用年份、距今年数、评价人数对数、类型标签数、国家/地区数，以及热门类型和国家/地区的多热编码，进行评分预测和电影画像分群。由于样本量只有 200 条且评分范围较窄，模型定位为探索性分析，不作为真实评分预测服务。",
        )
        add_ml_model_table(doc, model_summary["models"])
        add_paragraph(
            doc,
            "特征重要性显示，评价人数（对数）、上映年份、距今年数和类型标签数对模型误差影响最大，说明榜单内评分差异与热度、年代及类型结构存在一定关系。",
        )
        add_cluster_profile_table(doc, ml_summary["cluster_profiles"])

        doc.add_section(WD_SECTION_START.NEW_PAGE)

    doc.add_heading("5. 可视化结果", level=1)
    figures = [
        ("01_评分分布.png", "图 1 Top200 电影评分分布"),
        ("02_热门电影类型.png", "图 2 热门电影类型出现次数"),
        ("03_主要制片国家地区.png", "图 3 主要制片国家/地区出现次数"),
        ("04_不同年代电影数量.png", "图 4 不同年代电影数量"),
        ("07_排名与评分关系.png", "图 5 排名与评分关系"),
    ]
    if ml_summary:
        figures.extend(
            [
                ("08_机器学习评分预测对比.png", "图 6 机器学习评分预测 MAE 对比"),
                ("09_机器学习特征重要性.png", "图 7 随机森林置换特征重要性"),
                ("10_电影画像分群.png", "图 8 电影画像分群二维投影"),
            ]
        )
    for file_name, caption in figures:
        doc.add_picture(str(FIGURES / file_name), width=Inches(5.9))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_caption(doc, caption)

    doc.add_heading("6. 项目输出", level=1)
    add_key_value_table(
        doc,
        [
            ("清洗数据", "data/processed/movies_clean.csv"),
            ("类型展开表", "data/processed/movies_by_genre.csv"),
            ("国家/地区展开表", "data/processed/movies_by_country.csv"),
            ("统计摘要", "data/processed/analysis_summary.json"),
            ("机器学习摘要", "data/processed/ml_summary.json"),
            ("电影分群结果", "data/processed/movie_ml_clusters.csv"),
            ("分析图表", "output/figures/*.png"),
            ("展示报告", "GitHub 展示版 DOCX/PDF"),
        ],
    )

    doc.add_section(WD_SECTION_START.NEW_PAGE)
    doc.add_heading("7. 可复现操作", level=1)
    add_key_value_table(
        doc,
        [
            ("安装依赖", "python -m venv .venv；.venv\\Scripts\\python.exe -m pip install -r requirements.txt"),
            ("离线复现", "python run_pipeline.py --skip-fetch --student-name ... --student-id ... --class-name ..."),
            ("重新采集", "python run_pipeline.py --fetch --student-name ... --student-id ... --class-name ..."),
            ("运行 ML 扩展", "python scripts/run_ml_extension.py"),
            ("重建展示报告", "python scripts/build_github_showcase_report.py"),
            ("运行测试", "python -m pytest -q"),
        ],
    )

    doc.add_heading("8. 项目实现说明", level=1)
    add_key_value_table(
        doc,
        [
            ("采集层", "分页访问公开榜单页面，解析排名、片名、年份、国家/地区、类型、评分和评价人数。"),
            ("清洗层", "统一字段类型，处理多值字段，移除重复项，并输出一电影一行的主表。"),
            ("分析层", "生成评分、类型、国家/地区、年代和相关关系统计。"),
            ("建模层", "执行评分预测交叉验证、随机森林特征重要性分析和 KMeans 电影分群。"),
            ("输出层", "保存 CSV/JSON、PNG 图表、Word 报告和 PDF 报告。"),
        ],
    )

    doc.add_section(WD_SECTION_START.NEW_PAGE)
    doc.add_heading("9. 局限性", level=1)
    add_bullets(
        doc,
        [
            "榜单数据代表公开页面的一次快照，不能直接外推到全部电影市场。",
            "类型与国家/地区为多值字段，当前按出现次数统计。",
            "机器学习扩展使用小样本高分榜单数据，适合展示建模流程与特征解释，不适合作为真实评分预测系统。",
            "后续可加入交互式看板、自动化 CI 和更丰富的文本分析。",
        ],
    )

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(REPORT)
    return REPORT


if __name__ == "__main__":
    print(build_report())
