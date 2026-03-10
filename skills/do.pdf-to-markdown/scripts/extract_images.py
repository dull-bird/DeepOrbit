#!/usr/bin/env python3
"""
Extract all embedded images from a PDF file.

Usage:
    python extract_images.py <input.pdf> [--output-dir <dir>]

Output:
    Saves images to <input_name>_assets/ (or specified dir).
    Prints a manifest of extracted images as Markdown list.

Dependencies:
    pip install PyMuPDF
"""

import argparse
import os
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF is required. Install via: pip install PyMuPDF", file=sys.stderr)
    sys.exit(1)


def extract_images(pdf_path: str, output_dir: str) -> list[dict]:
    """Extract all images from a PDF, saving to output_dir.
    
    Returns a list of dicts with keys: page, index, filename, width, height, ext
    """
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    results = []
    seen_xrefs = set()  # avoid extracting the same image twice (shared across pages)

    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)

        for img_idx, img_info in enumerate(image_list):
            xref = img_info[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            try:
                base_image = doc.extract_image(xref)
            except Exception:
                continue

            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            width = base_image["width"]
            height = base_image["height"]

            filename = f"page{page_num + 1}_img{img_idx + 1}.{image_ext}"
            filepath = os.path.join(output_dir, filename)

            with open(filepath, "wb") as f:
                f.write(image_bytes)

            results.append({
                "page": page_num + 1,
                "index": img_idx + 1,
                "filename": filename,
                "width": width,
                "height": height,
                "ext": image_ext,
            })

    doc.close()
    return results


def main():
    parser = argparse.ArgumentParser(description="Extract images from a PDF file")
    parser.add_argument("pdf", help="Path to the input PDF file")
    parser.add_argument("--output-dir", "-o", default=None,
                        help="Output directory (default: <pdf_name>_assets/)")
    args = parser.parse_args()

    pdf_path = args.pdf
    if not os.path.isfile(pdf_path):
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    if args.output_dir:
        output_dir = args.output_dir
    else:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_dir = os.path.join(os.path.dirname(pdf_path), f"{base_name}_assets")

    results = extract_images(pdf_path, output_dir)

    if not results:
        print("No images found in the PDF.")
        return

    # Print manifest as Markdown
    print(f"## Extracted {len(results)} images to `{output_dir}/`\n")
    for img in results:
        rel_path = f"{os.path.basename(output_dir)}/{img['filename']}"
        print(f"- Page {img['page']}: `{img['filename']}` ({img['width']}x{img['height']} {img['ext']})")
        print(f"  - Markdown: `![Page {img['page']} Figure {img['index']}]({rel_path})`")

    print(f"\nTotal: {len(results)} images")


if __name__ == "__main__":
    main()
