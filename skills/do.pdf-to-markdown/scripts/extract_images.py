import fitz
from pathlib import Path
import sys

doc = fitz.open(sys.argv[1])
out_dir = Path(sys.argv[1]).stem + "_assets"
out_dir.mkdir(exist_ok=True)

for page_num in range(doc.page_count):
    page = doc[page_num]
    for img_idx, img in enumerate(page.get_images(full=True)):
        xref = img[0]
        pix = fitz.Pixmap(doc, xref)
        if pix.n > 4:  # CMYK → RGB
            pix = fitz.Pixmap(fitz.csRGB, pix)
        fname = f"page{page_num+1}_img{img_idx+1}.png"
        pix.save(str(out_dir / fname))
        print(f"  [{fname}] bbox={page.get_image_bbox(img)}")

doc.close()
