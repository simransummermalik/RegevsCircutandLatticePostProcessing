#!/usr/bin/env python3
"""Build the browseable poster-graphics package and validate exported assets."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import textwrap
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
START = ROOT / "00_START_HERE"
CONTACTS = ROOT / "13_CONTACT_SHEETS"
ZIP_PATH = REPO / "Poster_Graphics_Library.zip"

SCIENTIFIC_FOLDERS = [
    "01_HEADLINE_CARDS",
    "02_BEGINNER_BACKGROUND",
    "03_PIPELINE",
    "04_CERTIFICATE_AND_FIBERS",
    "05_FROZEN_EXPERIMENT",
    "06_PRIMARY_RESULTS",
    "07_RESOURCE_SAVINGS",
    "08_ROBUSTNESS_AND_DIAGNOSTICS",
    "09_LIMITATIONS_AND_CLAIMS",
    "14_SUPPLEMENTAL_VETO_OPTIONS",
    "16_SIMPLE_GENERAL_AUDIENCE",
]

DECORATIVE_FOLDERS = ["10_DECORATIVE_VECTORS", "12_DECORATIVE_AI_CONCEPTS"]

RECOMMENDED = [
    "01_HEADLINE_CARDS/H02_one_layer_result.png",
    "16_SIMPLE_GENERAL_AUDIENCE/Shor_vs_Regev_SIMPLE_GENERAL_AUDIENCE.png",
    "03_PIPELINE/P01_full_endpoint.png",
    "04_CERTIFICATE_AND_FIBERS/C03_fiber_cancellation.png",
    "04_CERTIFICATE_AND_FIBERS/C05_certificate_barrier.png",
    "05_FROZEN_EXPERIMENT/E01_frozen_protocol.png",
    "06_PRIMARY_RESULTS/R01_primary_heatmap.png",
    "06_PRIMARY_RESULTS/R02_all_paired_differences.png",
    "07_RESOURCE_SAVINGS/G01_M32_resource_bars.png",
    "09_LIMITATIONS_AND_CLAIMS/L01_scope_grid.png",
]

COLORS = {
    "navy": "#13294B",
    "orange": "#FF5F05",
    "blue": "#0072B2",
    "cyan": "#28A9C7",
    "purple": "#7E57C2",
    "teal": "#009E73",
    "red": "#D55E00",
    "cream": "#F7F8FA",
    "slate": "#526273",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    choices = [
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in choices:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def raster_paths(folders: list[str]) -> list[Path]:
    result: list[Path] = []
    for folder in folders:
        result.extend(sorted((ROOT / folder).glob("*.png")))
    return result


def contact_sheet(paths: list[Path], destination: Path, title: str, columns: int = 4) -> None:
    cell_w, cell_h = 700, 480
    margin, header = 50, 150
    rows = (len(paths) + columns - 1) // columns
    canvas = Image.new("RGB", (margin * 2 + columns * cell_w, header + margin + rows * cell_h), COLORS["cream"])
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 35), title, font=font(46, True), fill=COLORS["navy"])
    draw.text(
        (margin, 96),
        f"{len(paths)} choices — browse here, then use the original PNG/SVG/PDF in its labeled folder",
        font=font(21),
        fill=COLORS["slate"],
    )
    for index, path in enumerate(paths):
        row, col = divmod(index, columns)
        x = margin + col * cell_w
        y = header + row * cell_h
        with Image.open(path) as source:
            image = source.convert("RGB")
            thumb = ImageOps.contain(image, (cell_w - 40, cell_h - 95), Image.Resampling.LANCZOS)
        px = x + (cell_w - thumb.width) // 2
        py = y + 10 + (cell_h - 95 - thumb.height) // 2
        draw.rounded_rectangle(
            (x + 10, y, x + cell_w - 10, y + cell_h - 50),
            radius=12,
            fill="white",
            outline="#D9E3EA",
            width=2,
        )
        canvas.paste(thumb, (px, py))
        stem = path.stem if len(path.stem) <= 52 else path.stem[:49] + "..."
        label = f"{path.parent.name}\n{stem}"
        draw.multiline_text(
            (x + 18, y + cell_h - 49),
            label,
            font=font(14, True),
            fill=COLORS["navy"],
            spacing=2,
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, quality=94, optimize=True)


def style_guide() -> None:
    width, height = 2400, 1500
    image = Image.new("RGB", (width, height), COLORS["cream"])
    draw = ImageDraw.Draw(image)
    draw.text((120, 80), "Poster visual system", font=font(72, True), fill=COLORS["navy"])
    draw.text((120, 175), "High contrast, direct labels, and evidence status on every scientific panel", font=font(30), fill=COLORS["slate"])
    swatches = [
        ("Navy · main text", "navy"),
        ("Orange · truncation", "orange"),
        ("Blue · exact QFT", "blue"),
        ("Cyan · hard box", "cyan"),
        ("Purple · finite Gaussian", "purple"),
        ("Teal · empirical pass", "teal"),
        ("Vermilion · caution", "red"),
    ]
    for i, (label, key) in enumerate(swatches):
        row, col = divmod(i, 4)
        x, y = 120 + col * 560, 310 + row * 220
        draw.rounded_rectangle((x, y, x + 150, y + 150), radius=18, fill=COLORS[key])
        draw.text((x + 180, y + 20), label, font=font(26, True), fill=COLORS["navy"])
        draw.text((x + 180, y + 75), COLORS[key], font=font(24), fill=COLORS["slate"])
    draw.rounded_rectangle((120, 800, 2280, 1330), radius=22, fill="white", outline="#D9E3EA", width=3)
    draw.text((170, 850), "Evidence labels", font=font(42, True), fill=COLORS["navy"])
    labels = [
        ("VERIFIED", "A proof, implementation check, or frozen-data result", "teal"),
        ("SECONDARY", "A sensitivity analysis or mechanism diagnostic", "purple"),
        ("ILLUSTRATIVE", "A schematic or deliberately controlled example", "orange"),
        ("DECORATIVE — NOT DATA", "Artwork only; never use it as scientific evidence", "red"),
    ]
    for i, (tag, explanation, color) in enumerate(labels):
        y = 950 + i * 85
        draw.rounded_rectangle((170, y, 590, y + 54), radius=12, fill=COLORS[color])
        draw.text((190, y + 10), tag, font=font(23, True), fill="white")
        draw.text((640, y + 11), explanation, font=font(25), fill=COLORS["navy"])
    image.save(START / "style_guide.png", optimize=True)
    image.save(START / "style_guide.pdf", resolution=200)


def build_master_manifest() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    manifest = ROOT / "ASSET_MANIFEST.csv"
    if manifest.exists():
        with manifest.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                key = (row["folder"], row["id"])
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "id": row["id"],
                    "folder": row["folder"],
                    "evidence_level": row["evidence_level"],
                    "caption": row["caption"],
                    "source": row["source"],
                    "formats": row["files"],
                })

    supplemental = ROOT / "14_SUPPLEMENTAL_VETO_OPTIONS" / "SUPPLEMENTAL_MANIFEST.csv"
    if supplemental.exists():
        with supplemental.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                key = ("14_SUPPLEMENTAL_VETO_OPTIONS", row["asset"])
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "id": row["asset"],
                    "folder": key[0],
                    "evidence_level": row["evidence_level"],
                    "caption": row["caption"],
                    "source": row["source"],
                    "formats": ".png; .svg; .pdf",
                })

    extras = [
        ("15_POSTER_LAYOUT_OPTIONS", "L01_story_first_48x36_LAYOUT_MOCKUP", "Layout mockup; not data"),
        ("15_POSTER_LAYOUT_OPTIONS", "L02_result_first_48x36_LAYOUT_MOCKUP", "Layout mockup; not data"),
        ("15_POSTER_LAYOUT_OPTIONS", "L03_beginner_first_48x36_LAYOUT_MOCKUP", "Layout mockup; not data"),
        ("16_SIMPLE_GENERAL_AUDIENCE", "Shor_vs_Regev_SIMPLE_GENERAL_AUDIENCE", "Primary-literature background comparison; not an empirical result"),
        ("13_POSTER_REFERENCE", "original_poster_page1_REFERENCE_ONLY", "Supplied poster reference; not a result"),
    ]
    for folder, stem, evidence in extras:
        key = (folder, stem)
        if key in seen:
            continue
        seen.add(key)
        formats = "; ".join(p.suffix for p in sorted((ROOT / folder).glob(stem + ".*")))
        rows.append({
            "id": stem,
            "folder": folder,
            "evidence_level": evidence,
            "caption": "Placement/reference option; consult the folder README.",
            "source": "Poster packaging",
            "formats": formats,
        })

    rows.sort(key=lambda row: (row["folder"], row["id"]))
    output = START / "asset_manifest.csv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "folder", "evidence_level", "caption", "source", "formats"])
        writer.writeheader()
        writer.writerows(rows)
    return rows


def validate_assets() -> dict[str, object]:
    failures: list[str] = []
    raster_count = 0
    svg_count = 0
    pdf_count = 0
    min_width = 10**9
    min_height = 10**9

    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        suffix = path.suffix.lower()
        try:
            if suffix in {".png", ".jpg", ".jpeg"}:
                with Image.open(path) as image:
                    image.load()
                    width, height = image.size
                raster_count += 1
                min_width = min(min_width, width)
                min_height = min(min_height, height)
            elif suffix == ".svg":
                ElementTree.parse(path)
                svg_count += 1
            elif suffix == ".pdf":
                import fitz

                with fitz.open(path) as document:
                    if document.page_count < 1:
                        raise ValueError("zero-page PDF")
                pdf_count += 1
        except Exception as exc:  # pragma: no cover - validation path
            failures.append(f"{path.relative_to(ROOT)}: {exc}")

    completion_path = ROOT / "_SOURCE_DATA" / "completion.json"
    hash_checks = 0
    if completion_path.exists():
        completion = json.loads(completion_path.read_text(encoding="utf-8"))
        for name, expected in completion.get("sha256", {}).items():
            copied = ROOT / "_SOURCE_DATA" / name
            if not copied.exists():
                continue
            observed = hashlib.sha256(copied.read_bytes()).hexdigest()
            hash_checks += 1
            if observed != expected:
                failures.append(f"_SOURCE_DATA/{name}: frozen SHA-256 mismatch")

    return {
        "raster_count": raster_count,
        "svg_count": svg_count,
        "pdf_count": pdf_count,
        "minimum_raster_width": 0 if raster_count == 0 else min_width,
        "minimum_raster_height": 0 if raster_count == 0 else min_height,
        "frozen_source_hashes_checked": hash_checks,
        "failures": failures,
    }


def write_validation_report(rows: list[dict[str, str]], validation: dict[str, object]) -> None:
    scientific = sum(row["folder"] in SCIENTIFIC_FOLDERS for row in rows)
    decorative = sum(row["folder"] in DECORATIVE_FOLDERS for row in rows)
    failures = validation["failures"]
    status = "PASS" if not failures else "FAIL"
    text = f"""# Poster graphics validation report

**Overall status: {status}**

- Distinct catalogued choices: {len(rows)}
- Scientific/explanatory choices: {scientific}
- Decorative choices: {decorative}
- Raster files opened successfully: {validation['raster_count']}
- SVG files parsed successfully: {validation['svg_count']}
- PDF files opened successfully: {validation['pdf_count']}
- Frozen source hashes checked: {validation['frozen_source_hashes_checked']}
- Smallest raster dimensions encountered: {validation['minimum_raster_width']} × {validation['minimum_raster_height']} pixels

The validation is mechanical: it checks file integrity, vector/PDF parsing, and copied frozen-data hashes. Scientific claims were also manually compared with the frozen protocol and result tables. Decorative AI images remain explicitly labeled as not data.

## Failures

{chr(10).join('- ' + item for item in failures) if failures else '- None.'}
"""
    (START / "VALIDATION_REPORT.md").write_text(text, encoding="utf-8")


def write_checksums() -> None:
    lines: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.name == "checksums.sha256":
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(ROOT)}")
    (START / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_zip() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.name == ".DS_Store":
                continue
            archive.write(path, Path("poster graphics") / path.relative_to(ROOT))


def main() -> None:
    START.mkdir(parents=True, exist_ok=True)
    CONTACTS.mkdir(parents=True, exist_ok=True)

    recommended = [ROOT / relative for relative in RECOMMENDED]
    missing = [str(path.relative_to(ROOT)) for path in recommended if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing recommended assets: " + ", ".join(missing))

    contact_sheet(recommended, START / "contact_sheet_recommended.png", "Recommended poster set", columns=2)
    contact_sheet(raster_paths(SCIENTIFIC_FOLDERS), START / "contact_sheet_scientific.png", "Scientific and explanatory graphics", columns=4)
    contact_sheet(raster_paths(DECORATIVE_FOLDERS), START / "contact_sheet_decorative.png", "Decorative graphics — not data", columns=3)

    all_contact = CONTACTS / "CONTACT_ALL_ASSETS.jpg"
    if all_contact.exists():
        shutil.copy2(all_contact, START / "contact_sheet_all.jpg")

    style_guide()
    rows = build_master_manifest()
    validation = validate_assets()
    write_validation_report(rows, validation)
    write_checksums()
    build_zip()

    if validation["failures"]:
        raise RuntimeError("Poster asset validation failed; inspect 00_START_HERE/VALIDATION_REPORT.md")

    print(json.dumps({
        "catalogued_choices": len(rows),
        "raster_files": validation["raster_count"],
        "svg_files": validation["svg_count"],
        "pdf_files": validation["pdf_count"],
        "zip": str(ZIP_PATH),
    }, indent=2))


if __name__ == "__main__":
    main()
