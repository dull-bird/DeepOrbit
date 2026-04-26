# 问题：do.pdf-to-markdown 图片提取方案改进

## 现状

当前 skill 第 61 行引用了 `scripts/extract_images_pdfplumber.py`，但这个脚本存在两个问题：

1. **`scripts/` 目录没有打包到技能包中**，实际运行时报错
2. **pdfplumber 不适合做图片提取**——它的 `page.images` 只能检测图片占位区域（bbox），没有直接导出图片像素数据的能力，需要额外依赖 Pillow 做转码

## 建议方案

### 库选择：pdfplumber → PyMuPDF (fitz)

| 能力 | pdfplumber | PyMuPDF |
|------|-----------|---------|
| 图片发现 | page.images（只返回元数据） | page.get_images(full=True)（返回 xref 对象引用） |
| 像素导出 | 需 Pillow 二次处理 | Pixmap(doc, xref).save() 一行导出 |
| CMYK→RGB | 不支持 | 内建转换 |
| 全页渲染 | 不支持 | page.get_pixmap() 可兜底矢量图 |
| installed size | ~3MB | ~30MB |

### 提取脚本

用 `scripts/extract_images.py` 替换原来的 `extract_images_pdfplumber.py`：

```python
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
```

### SKILL.md 改动

**Phase 1 中修改**（第 58-68 行）：

```
- pip install pdfplumber
+ pip install PyMuPDF

- python {skill_path}/scripts/extract_images_pdfplumber.py <input.pdf>
+ python {skill_path}/scripts/extract_images.py <input.pdf>
```

**Prerequisites 中修改**（第 20-23 行）：

```bash
- pip install pdfplumber
+ pip install PyMuPDF
```

### 仍存在的限制：矢量图

该方案只能提取 **内嵌位图**（PNG/JPEG/TIFF）。学术论文中的矢量图（PDF 绘图命令画的图表）无法作为独立图片提取。对策：

1. **全页渲染兜底**（已内置）：Phase 2 中用 `page.get_pixmap()` 渲染全页作为备选
2. **LLM 多模态识别**（已有）：Ralph Loop 中读全页截图，LLM 自动分辨图表区域，在输出中用 `![](assets/page3_full.png)` 引用整图并标注裁剪建议

矢量图的精确裁剪是 PDF 处理的公认难题，现有方案都无法完美解决。LLM 视觉方案虽然不能精确裁剪，但能理解图中内容并正确描述，实用性足够了。

---

## 关联文件清单

需开发者修改的文件：

| 文件 | 操作 |
|------|------|
| `skills/do.pdf-to-markdown/SKILL.md` | 修改第 20-23 行（Prerequisites）、第 61 行（脚本名） |
| `skills/do.pdf-to-markdown/scripts/extract_images_pdfplumber.py` | 删除 |
| `skills/do.pdf-to-markdown/scripts/extract_images.py` | 新建 |

## Prerequisites

用户需要安装 `PyMuPDF`：
```bash
pip install PyMuPDF
```
