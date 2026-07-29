#!/usr/bin/env python3
"""Create non-destructive crops of the two decorative concept illustrations."""

from pathlib import Path

from PIL import Image, ImageEnhance


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "12_DECORATIVE_AI_CONCEPTS"


def crop_to_ratio(image: Image.Image, ratio: float, center_x: float = 0.5) -> Image.Image:
    width, height = image.size
    current = width / height
    if current > ratio:
        crop_width = int(round(height * ratio))
        left = int(round((width - crop_width) * center_x))
        left = max(0, min(left, width - crop_width))
        return image.crop((left, 0, left + crop_width, height))
    crop_height = int(round(width / ratio))
    top = max(0, (height - crop_height) // 2)
    return image.crop((0, top, width, top + crop_height))


def save_variant(
    source: Path,
    destination: str,
    ratio: float,
    size: tuple[int, int],
    center_x: float = 0.5,
    contrast: float = 1.0,
) -> None:
    image = Image.open(source).convert("RGB")
    image = crop_to_ratio(image, ratio, center_x=center_x)
    if contrast != 1.0:
        image = ImageEnhance.Contrast(image).enhance(contrast)
    image = image.resize(size, Image.Resampling.LANCZOS)
    image.save(ART / destination, quality=95, optimize=True)


def main() -> None:
    dark = ART / "D01_quantum_to_lattice_hero_dark_DECORATIVE_NOT_DATA.png"
    light = ART / "D02_certificate_fiber_lattice_hero_light_DECORATIVE_NOT_DATA.png"
    save_variant(
        dark,
        "D01a_dark_header_4x1_DECORATIVE_NOT_DATA.png",
        4.0,
        (1800, 450),
        center_x=0.5,
        contrast=1.05,
    )
    save_variant(
        dark,
        "D01b_dark_panel_3x2_DECORATIVE_NOT_DATA.png",
        1.5,
        (1600, 1067),
        center_x=0.55,
    )
    save_variant(
        dark,
        "D01c_dark_lattice_square_DECORATIVE_NOT_DATA.png",
        1.0,
        (1200, 1200),
        center_x=0.9,
    )
    save_variant(
        light,
        "D02a_light_header_4x1_DECORATIVE_NOT_DATA.png",
        4.0,
        (1800, 450),
        center_x=0.55,
    )
    save_variant(
        light,
        "D02b_light_panel_3x2_DECORATIVE_NOT_DATA.png",
        1.5,
        (1600, 1067),
        center_x=0.52,
    )
    save_variant(
        light,
        "D02c_light_lattice_square_DECORATIVE_NOT_DATA.png",
        1.0,
        (1200, 1200),
        center_x=0.85,
    )
    print("Wrote six decorative crop variants.")


if __name__ == "__main__":
    main()
