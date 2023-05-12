
import re
from pathlib import Path
from pprint import pprint

import cv2
from paddleocr import PaddleOCR, PPStructure, draw_ocr
from PIL import Image
from src.lib.bookmark import transform_toc_file

def center_y(elem):
    return (elem[0][0][1]+elem[0][3][1])/2

def write_ocr_result(ocr_results, output_path: str, offset: int = 5):
    # 按照 y中点 坐标排序
    sorted_by_y = sorted(ocr_results, key=lambda x: center_y(x))
    results = []
    temp_row = [sorted_by_y[0]]
    for i in range(1, len(sorted_by_y)):
        # 如果和前一个元素的 y 坐标差值小于偏移量，则视为同一行
        if abs(center_y(sorted_by_y[i]) - center_y(sorted_by_y[i-1])) < offset:
            temp_row.append(sorted_by_y[i])
        else:
            # 按照 x 坐标排序，将同一行的元素按照 x 坐标排序
            temp_row = sorted(temp_row, key=lambda x: x[0][0])
            # 将同一行的元素添加到结果列表中
            results.append(temp_row)
            temp_row = [sorted_by_y[i]]
    # 将最后一行的元素添加到结果列表中
    temp_row = sorted(temp_row, key=lambda x: x[0][0])
    results.append(temp_row)
    with open(output_path, "w") as f:
        for row in results:
            line = ""
            for item in row:
                pos, (text, prob) = item
                line += f"{text} "
            line = line.rstrip()
            f.write(f"{line}\n")

def ocr_from_image(input_path: str, lang: str = 'ch', output_path: str = None):
    ocr_engine = PaddleOCR(use_angle_cls=True, lang=lang) # need to run only once to download and load model into memory
    img = cv2.imread(input_path)
    result = ocr_engine.ocr(img, cls=False)[0]

    image  = Image.open(input_path).convert('RGB')
    boxes  = [line[0] for line in result]
    txts   = [line[1][0] for line in result]
    scores = [line[1][1] for line in result]
    im_show = draw_ocr(image, boxes, txts, scores, font_path='src/assets/SIMKAI.TTF')
    im_show = Image.fromarray(im_show)

    p = Path(input_path)
    if output_path is None:
        output_dir = p.parent / "ocr"
    else:
        output_dir = Path(output_path)    
    output_dir.mkdir(parents=True, exist_ok=True)
    img_output_path = str(output_dir / f"{p.stem}-ocr.png")
    text_output_path = str(output_dir / f"{p.stem}-ocr.txt")

    im_show.save(img_output_path)
    write_ocr_result(result, text_output_path)


if __name__ == "__main__":
    input_path = "/home/likai/code/pdf_tocgen/assets/toc2.png"
    # input_path = "/home/likai/code/pdf_tocgen/assets/page4.png"
    lang = 'ch'
    output_path = "output"
    # ocr_from_image(input_path, lang, output_path)
    transform_toc_file("/home/likai/code/pdf_tocgen/output/toc2-ocr.txt")