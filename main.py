import argparse
import os
import re
import shutil
from pathlib import Path
from pprint import pprint

import cv2
import fitz
import numpy as np
from paddleocr import PaddleOCR, PPStructure
from PIL import Image
from tqdm import tqdm


def plot_roi_region(input_path, type: str = 'title', output_path: str = "result.png"):
    img = cv2.imread(input_path)
    structure_engine = PPStructure(table=False, ocr=False, show_log=False)
    result = structure_engine(img)
    for item in result:
        if item['type'] == type:
            x1, y1, x2, y2 = item['bbox']
            cv2.rectangle(img, (x1, y1), (x2, y2), color=(255, 0, 0), thickness=2)
    cv2.imwrite(output_path, img)

def title_preprocess(title: str):
    title = title.strip()
    res = {
        "level": 1,
        "text": title
    }
    m = re.match("((\d+\.?)+)\s*(.+)", title)
    if m is not None:
        res['text'] = f"{m.group(1)} {m.group(3)}"
        res['level'] = len(m.group(1).split("."))
        return res
    m = re.match("(第\d+[章|节])\s*(.+)", title) 
    if m is not None:
        res['text'] = f"{m.group(1)} {m.group(2)}"
        res['level'] = 1
        return res
    return res


def extract_title(input_path: str, lang: str = 'ch', use_double_columns: bool = False) -> list:
    ocr_engine = PaddleOCR(use_angle_cls=True, lang=lang) # need to run only once to download and load model into memory
    structure_engine = PPStructure(table=False, ocr=False, show_log=False)

    img = cv2.imread(input_path)
    result = structure_engine(img)
    title_items = [v for v in result if v['type']=='title']       # 提取title项
    title_items = sorted(title_items, key=lambda x: x['bbox'][1]) # 从上往下排序
    if use_double_columns:
        height, width = img.shape[:2]
        mid = width / 2
        left_title_items = [v for v in title_items if v['bbox'][2]<mid]
        right_title_items = [v for v in title_items if v['bbox'][2]>=mid]
        left_title_items = sorted(left_title_items, key=lambda x: x['bbox'][1]) # 从上往下排序
        right_title_items = sorted(right_title_items, key=lambda x: x['bbox'][1]) # 从上往下排序
        title_items = left_title_items + right_title_items
    x_delta = 10
    y_delta = 5
    out = []
    for item in title_items:
        x1, y1, x2, y2 = item['bbox']
        result = ocr_engine.ocr(img[y1-y_delta: y2+y_delta, x1-x_delta: x2+x_delta], cls=False)
        for idx in range(len(result)):
            res = result[idx]
            for line in res:
                pos, (title, prob) = line
                new_pos = []
                for p in pos:
                    new_pos.append([p[0]+x1-x_delta, p[1]+y1-y_delta])
                out.append([new_pos, (title, prob)])
    return out

def add_toc(doc_path: str, lang: str='ch', use_double_columns: bool = False, output_path: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    tmp_dir = p.parent / 'tmp'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    
    toc = []
    for page in tqdm(doc, total=doc.page_count):
        pix = page.get_pixmap()  # render page to an image
        savepath = str(tmp_dir / f"page-{page.number}.png")
        pix.save(savepath)  # store image as a PNG

        # plot_roi_region(savepath, output_path=str(tmp_dir / f"plot-page-{page.number}.png"))
        result = extract_title(savepath, lang, use_double_columns)
        for item in result:
            pos, (title, prob) = item
            # 书签格式：[|v|, title, page [, dest]]  (层级，标题，页码，高度)
            res = title_preprocess(title)
            level, title = res['level'], res['text']
            height = pos[0][1] # 左上角点的y坐标
            toc.append([level, title, page.number+1, height])
    
    # 校正层级
    levels = [v[0] for v in toc]
    diff = np.diff(levels)
    indices = np.where(diff>1)[0]
    for idx in indices:
        toc[idx][0] = toc[idx+1][0]

    # 设置目录
    doc.set_toc(toc)
    if output_path is None:
        output_path = str(p.parent / f"{p.stem}-[toc].pdf")
    doc.save(output_path)
    shutil.rmtree(tmp_dir)

def add_toc_from_file(toc_path: str, doc_path: str, offset: int, output_path: str = None):
    """从目录文件中导入书签到pdf文件

    Args:
        toc_path (str): 目录文件路径
        doc_path (str): pdf文件路径
        offset (int): 偏移量, 计算方式: “pdf文件实际页码” - “目录文件标注页码”
    """    
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    toc = []
    with open(toc_path, "r") as f:
        for line in f:
            parts = line.split()
            pno = int(parts[-1]) + offset
            title = " ".join(map(lambda x: x.strip(), parts[:-1]))
            res = title_preprocess(title)
            level, title = res['level'], res['text']
            toc.append([level, title, pno])
    
    # 校正层级
    levels = [v[0] for v in toc]
    diff = np.diff(levels)
    indices = np.where(diff>1)[0]
    for idx in indices:
        toc[idx][0] = toc[idx+1][0]

    doc.set_toc(toc)
    if output_path is None:
        output_path = str(p.parent / f"{p.stem}-[toc].pdf")
    doc.save(output_path)

def extract_toc(doc_path: str, output_path: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    out = doc.get_toc()
    print(out)
    if output_path is None:
        output_path = str(p.parent / f"{p.stem}-[toc].txt")
    with open(output_path, "w") as f:
        for line in out:
            indent = (line[0]-1)*"\t"
            f.writelines(f"{indent}{line[1]} {line[2]}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path", type=str)
    parser.add_argument("-l", "--lang", type=str, default="ch", choices=['ch', 'en', 'fr', 'german', 'it', 'japan', 'korean', 'ru', 'chinese_cht'], dest="lang")
    parser.add_argument("-o", "--output", type=str, default=None, dest="output_path")
    parser.add_argument("--offset", type=int, default=0, dest="offset")
    parser.add_argument("-d", "--double-columns", action="store_true", dest='use_double_column', default=False)
    parser.add_argument("-x", "--extract-toc", action="store_true", dest='extract_toc', default=False)
    parser.add_argument("-t", "--toc-file", type=str,default=None, dest='toc_path')
    args = parser.parse_args()

    if args.toc_path is not None:
        add_toc_from_file(args.toc_path, args.input_path, offset=args.offset, output_path=args.output_path)
    elif args.extract_toc:
        extract_toc(args.input_path, args.output_path)
    else:
        add_toc(args.input_path, lang=args.lang, use_double_columns=args.use_double_column, output_path=args.output_path)
