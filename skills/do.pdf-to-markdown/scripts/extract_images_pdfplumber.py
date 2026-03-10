import pdfplumber
import sys
import os

def is_two_column_layout(page, words):
    """检测页面是否为双栏排版"""
    center_x = page.width / 2
    gutter_width = page.width * 0.05
    # 统计横跨中线的文字块比例
    crossing_words = [w for w in words if w['x0'] < (center_x - gutter_width/2) and w['x1'] > (center_x + gutter_width/2)]
    return len(crossing_words) < (len(words) * 0.03) # 只有不到 3% 的文字横跨中线，视为双栏

def extract_pdf_images(pdf_path):
    output_dir = pdf_path.replace('.pdf', '_assets')
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Processing: {pdf_path}")
    print(f"Saving images to: {output_dir}\n")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            img_count = 0
            
            for page_num, page in enumerate(pdf.pages):
                words = page.extract_words()
                if not words: continue
                
                is_2col = is_two_column_layout(page, words)
                center_x = page.width / 2
                
                # 1. 提取原生嵌入图像
                for img_idx, img in enumerate(page.images):
                    try:
                        x0, y0, x1, y1 = img["x0"], page.height - img["y1"], img["x1"], page.height - img["y0"]
                        if x0 >= x1 or y0 >= y1: continue
                        img_path = os.path.join(output_dir, f"page{page_num+1}_img{img_idx+1}.png")
                        page.crop((max(0, x0), max(0, y0), min(page.width, x1), min(page.height, y1))).to_image(resolution=300).save(img_path)
                        print(f"- Extracted Raw Image: {img_path}")
                        img_count += 1
                    except: pass

                # 2. 智能提取图表 (Figures)
                figure_anchors = [w for w in words if w['text'].lower().startswith(('figure', 'fig.'))]
                
                if figure_anchors:
                    print(f"  Page {page_num+1}: Found {len(figure_anchors)} figure captions. Layout: {'2-Col' if is_2col else '1-Col'}")
                    
                    for idx, anchor in enumerate(figure_anchors):
                        caption_top = anchor['top']
                        
                        # A. 向上寻找图形元素范围 (向上追溯约 400 pts)
                        search_limit = max(0, caption_top - 400)
                        # 寻找此范围内的图形对象
                        nearby_objs = [obj for obj in page.images + page.rects 
                                      if obj['bottom'] < caption_top and obj['top'] > search_limit]
                        
                        # B. 寻找顶部正文边界 (寻找上方最近的、不属于此图表的文字块)
                        objs_top = min([obj['top'] for obj in nearby_objs]) if nearby_objs else search_limit
                        words_above = [w for w in words if w['bottom'] < caption_top and w['bottom'] > search_limit - 50]
                        # 过滤掉可能是图表内标注的短文字 (简单启发式：离 Caption 很近且很短)
                        body_text_above = [w for w in words_above if w['bottom'] < objs_top - 10]
                        final_top = max([w['bottom'] for w in body_text_above]) if body_text_above else search_limit
                        
                        # C. 判定宽度类型 (Span-column check)
                        # 检查 Caption 或图形对象是否跨越中线
                        is_span = anchor['x1'] > center_x + 20 and anchor['x0'] < center_x - 20
                        if nearby_objs:
                            objs_x0 = min(o['x0'] for o in nearby_objs)
                            objs_x1 = max(o['x1'] for o in nearby_objs)
                            if objs_x0 < center_x - 20 and objs_x1 > center_x + 20:
                                is_span = True
                        
                        # 检查侧向冲突：在此高度区间，中线另一侧是否有文字
                        test_y_range = (max(final_top, objs_top), caption_top)
                        side_words = [w for w in words if w['top'] > test_y_range[0] and w['bottom'] < test_y_range[1]]
                        has_left_text = any(w['x1'] < center_x - 10 for w in side_words)
                        has_right_text = any(w['x0'] > center_x + 10 for w in side_words)
                        
                        if is_2col and has_left_text and has_right_text:
                            # 典型的双栏内嵌图
                            x0 = 0 if anchor['x0'] < center_x else center_x
                            x1 = center_x if anchor['x0'] < center_x else page.width
                        else:
                            # 跨栏图、全宽图或单栏论文图
                            x0, x1 = 0, page.width

                        # D. 执行裁剪
                        try:
                            bbox = (max(0, x0), max(0, final_top - 5), min(page.width, x1), min(page.height, caption_top))
                            if bbox[2] - bbox[0] < 50 or bbox[3] - bbox[1] < 50: continue # 过滤太小的区域
                            
                            img_path = os.path.join(output_dir, f"page{page_num+1}_figure{idx+1}_rendered.png")
                            page.crop(bbox).to_image(resolution=300).save(img_path)
                            print(f"- Rendered Figure Box: {img_path} (Span: {is_span})")
                            img_count += 1
                        except Exception as e:
                            print(f"  [Error] Page {page_num+1} Fig {idx+1}: {e}")

            print(f"\nTotal images extracted: {img_count}")

    except Exception as e:
        print(f"Error processing PDF: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit(1)
    extract_pdf_images(sys.argv[1])
