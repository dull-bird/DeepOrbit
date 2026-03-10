import pdfplumber
import sys
import os

def extract_pdf_images(pdf_path):
    output_dir = pdf_path.replace('.pdf', '_assets')
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Processing: {pdf_path}")
    print(f"Saving images to: {output_dir}\n")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            img_count = 0
            
            for page_num, page in enumerate(pdf.pages):
                # 1. 提取原生嵌入图像 (Photographs/Scans)
                for img_idx, img in enumerate(page.images):
                    try:
                        # 转换坐标系统：pdfplumber 的 images 坐标与 crop 期望的坐标可能有所不同
                        # 确保不超出边界
                        x0 = max(0, img["x0"])
                        top = max(0, page.height - img["y1"])
                        x1 = min(page.width, img["x1"])
                        bottom = min(page.height, page.height - img["y0"])
                        
                        # 过滤无效边界
                        if x0 >= x1 or top >= bottom:
                            continue
                            
                        bbox = (x0, top, x1, bottom)
                        cropped_page = page.crop(bbox)
                        pil_img = cropped_page.to_image(resolution=300).original
                        img_path = os.path.join(output_dir, f"page{page_num+1}_img{img_idx+1}.png")
                        pil_img.save(img_path)
                        print(f"- Extracted Raw Image: {img_path}")
                        img_count += 1
                    except Exception as e:
                        print(f"  [Warning] Failed to extract raw image on page {page_num+1}: {e}")

                # 2. 启发式提取矢量图表 (Figures/Charts)
                # 寻找 'Figure' 或 'Fig.' 开头的文字块作为锚点
                words = page.extract_words()
                figure_anchors = []
                
                for i, word in enumerate(words):
                    text = word['text']
                    if text.startswith('Figure') or text.startswith('Fig.'):
                        figure_anchors.append(word)

                if figure_anchors:
                    print(f"  Found {len(figure_anchors)} potential figure captions on page {page_num+1}")
                    
                    for idx, anchor in enumerate(figure_anchors):
                        # 智能判断单双栏 (以页面中线为界)
                        is_left_column = anchor['x0'] < page.width / 2
                        is_right_column = anchor['x0'] > page.width / 2
                        
                        # 判断排版系双栏还是单栏：如果页面很宽(>500)通常是双栏，否则视为单栏
                        is_two_column_format = page.width > 500
                        
                        # 确定 X 轴边界
                        if is_two_column_format and is_left_column:
                            x0, x1 = 0, page.width / 2
                        elif is_two_column_format and is_right_column:
                            x0, x1 = page.width / 2, page.width
                        else:
                            # 单栏排版，X轴覆盖全宽
                            x0, x1 = 0, page.width

                        # 确定 Y 轴边界：向上追溯到页面顶部
                        # 学术图表通常在页面顶部或者段落之间。为了简单，直接裁剪到页顶。
                        # （如果同一栏有多个图，则从上一个图的 Caption 底部开始）
                        bottom_y = anchor['top']
                        
                        # 寻找在当前图表上方的最近的一个图表 caption（如果在同一栏）
                        top_y = 0
                        for prev_anchor in figure_anchors[:idx]:
                            # 如果之前的图也在同一栏，并且位置在当前图上方
                            if abs(prev_anchor['x0'] - anchor['x0']) < 100 and prev_anchor['bottom'] < bottom_y:
                                top_y = max(top_y, prev_anchor['bottom'])
                        
                        # 裁剪区域
                        try:
                            bbox = (max(0, x0 - 10), max(0, top_y), min(page.width, x1 + 10), min(page.height, bottom_y))
                            
                            # 过滤无效边界
                            if bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
                                continue
                                
                            cropped = page.crop(bbox)
                            img_path = os.path.join(output_dir, f"page{page_num+1}_figure{idx+1}_rendered.png")
                            cropped.to_image(resolution=300).save(img_path)
                            print(f"- Rendered Figure Box: {img_path}")
                            img_count += 1
                        except Exception as e:
                            print(f"  [Warning] Failed to crop figure on page {page_num+1}: {e}")

            print(f"\nTotal images extracted: {img_count}")

    except Exception as e:
        print(f"Error processing PDF: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python extract_images_pdfplumber.py <pdf_path>")
        sys.exit(1)
    extract_pdf_images(sys.argv[1])