#!/usr/bin/env python3
"""
PDF Translation Script - Replace text in PDF while preserving structure and style.

Usage:
    python translate_pdf.py <input.pdf> <translations.json> <output.pdf> [--font <fontname>]

Arguments:
    input.pdf         Input PDF file path
    translations.json JSON file with translation mappings: {"original": "translated", ...}
    output.pdf        Output PDF file path
    --font            Font name for target language (default: helv, use china-ss for Chinese, japan for Japanese)
"""

import json
import sys
import argparse

try:
    import pymupdf
except ImportError:
    print("Error: pymupdf not installed. Run: pip install pymupdf")
    sys.exit(1)


def translate_pdf(input_path: str, translations: dict, output_path: str, fontname: str = "helv"):
    """
    Translate text in PDF using provided translation mappings.

    Args:
        input_path: Path to input PDF
        translations: Dict mapping original text to translated text
        output_path: Path for output PDF
        fontname: Font name for translated text (helv, china-ss, japan, korea, etc.)
    """
    doc = pymupdf.open(input_path)

    translated_count = 0
    total_spans = 0

    for page in doc:
        text_dict = page.get_text("dict")
        replacements = []

        for block in text_dict["blocks"]:
            if block.get("type") != 0:
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    total_spans += 1
                    original_text = span.get("text", "")

                    if not original_text.strip():
                        continue

                    if original_text in translations:
                        new_text = translations[original_text]

                        if new_text != original_text:
                            bbox = span["bbox"]
                            font_size = span["size"]
                            color = span.get("color", 0)

                            if isinstance(color, int):
                                r = (color >> 16 & 0xFF) / 255
                                g = (color >> 8 & 0xFF) / 255
                                b = (color & 0xFF) / 255
                                text_color = (r, g, b)
                            else:
                                text_color = (0, 0, 0)

                            replacements.append({
                                "bbox": bbox,
                                "new_text": new_text,
                                "font_size": font_size,
                                "text_color": text_color
                            })
                            translated_count += 1

        # Step 1: Remove old text with transparent fill
        for repl in replacements:
            rect = pymupdf.Rect(repl["bbox"])
            page.add_redact_annot(rect, fill=False)

        page.apply_redactions()

        # Step 2: Insert translated text
        for repl in replacements:
            bbox = repl["bbox"]
            text_point = pymupdf.Point(bbox[0], bbox[3] - 1)

            # Slightly reduce font size for CJK languages to fit
            fs = repl["font_size"]
            if fontname in ["china-ss", "china-ts", "japan", "korea"]:
                fs *= 0.9

            page.insert_text(
                text_point,
                repl["new_text"],
                fontsize=fs,
                fontname=fontname,
                color=repl["text_color"],
            )

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

    return {"total_spans": total_spans, "translated": translated_count}


def extract_texts(input_path: str) -> list:
    """
    Extract all unique text strings from PDF.

    Args:
        input_path: Path to input PDF

    Returns:
        List of unique text strings
    """
    doc = pymupdf.open(input_path)
    all_texts = set()

    for page in doc:
        text_dict = page.get_text("dict")

        for block in text_dict["blocks"]:
            if block.get("type") != 0:
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if text:
                        all_texts.add(text)

    doc.close()
    return sorted(all_texts)


def main():
    parser = argparse.ArgumentParser(description="Translate PDF text while preserving structure")
    parser.add_argument("input_pdf", help="Input PDF file")
    parser.add_argument("translations_json", help="JSON file with translations")
    parser.add_argument("output_pdf", help="Output PDF file")
    parser.add_argument("--font", default="helv", help="Font name (helv, china-ss, japan, korea)")

    args = parser.parse_args()

    with open(args.translations_json, "r", encoding="utf-8") as f:
        translations = json.load(f)

    result = translate_pdf(args.input_pdf, translations, args.output_pdf, args.font)

    print(f"Translation complete!")
    print(f"Total text spans: {result['total_spans']}")
    print(f"Translated: {result['translated']}")
    print(f"Output: {args.output_pdf}")


if __name__ == "__main__":
    main()
