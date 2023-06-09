import glob
import json
import re
import shutil
import traceback
from pathlib import Path

import cv2
import fitz
import numpy as np
from loguru import logger
from paddleocr import PaddleOCR
from tqdm import tqdm

from pdf_toolbox.utils import ppstructure_analysis


def title_preprocess(title: str):
    """提取标题层级和标题内容
    """
    try:
        title = title.rstrip()
        res = {}
        # 匹配：1.1.1 标题
        m = re.match("\s*((\d+\.?)+)\s*(.+)", title)
        if m is not None:
            res['text'] = f"{m.group(1)} {m.group(3)}"
            res['level'] = len([v for v in m.group(1).split(".") if v])
            return res
        
        # 匹配：第1章 标题
        m = re.match("\s*(第.+[章|编])\s*(.+)", title)
        if m is not None:
            res['text'] = f"{m.group(1)} {m.group(2)}"
            res['level'] = 1
            return res

        # 匹配：第1节 标题
        m = re.match("\s*(第.+节)\s*(.+)", title)
        if m is not None:
            res['text'] = f"{m.group(1)} {m.group(2)}"
            res['level'] = 2
            return res
        
        # 根据缩进匹配
        m = re.match("(\t*)\s*(.+)", title)
        res['text'] = f"{m.group(2)}".rstrip()
        res['level'] = len(m.group(1))+1
        return res
    except:
        logger.error(f"error for title: {title}")
        traceback.print_exc()
        return {'level': 1, "text": title}

def extract_title(input_path: str, lang: str = 'ch', use_double_columns: bool = False) -> list:
    # TODO: 存在标题识别不全bug
    ocr_engine = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False) # need to run only once to download and load model into memory
    img = cv2.imread(input_path)
    result = ppstructure_analysis(input_path)
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

def add_toc_from_ocr(doc_path: str, lang: str='ch', use_double_columns: bool = False, output_path: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    tmp_dir = p.parent / 'tmp'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    
    toc = []
    for page in tqdm(doc, total=doc.page_count):
        pix: fitz.Pixmap = page.get_pixmap()  # render page to an image
        savepath = str(tmp_dir / f"page-{page.number+1}.png")
        # pix.save(savepath)  # store image as a PNG
        pix.pil_save(savepath, quality=100, dpi=(1800,1800))
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
        output_path = str(p.parent / f"{p.stem}-toc.pdf")
    doc.save(output_path)
    shutil.rmtree(tmp_dir)

def add_toc_from_file(toc_path: str, doc_path: str, offset: int, output_path: str = None):
    """从目录文件中导入书签到pdf文件(若文件中存在行没指定页码则按1算)

    Args:
        toc_path (str): 目录文件路径
        doc_path (str): pdf文件路径
        offset (int): 偏移量, 计算方式: “pdf文件实际页码” - “目录文件标注页码”
    """
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    toc_path = Path(toc_path)
    toc = []
    if toc_path.suffix == ".txt":
        with open(toc_path, "r", encoding="utf-8") as f:
            for line in f:
                pno = 1
                title = line
                m = re.search("(\d+)(?=\s*$)", line) # 把最右侧的数字当作页码，如果解析的数字超过pdf总页数，就从左边依次删直到小于pdf总页数为止
                if m is not None:
                    pno = int(m.group(1))
                    while pno > doc.page_count:
                        pno = int(str(pno)[1:])
                    title = line[:m.span()[0]]
                pno = pno + offset
                if not title.strip(): # 标题为空跳过
                    continue
                res = title_preprocess(title)
                level, title = res['level'], res['text']
                toc.append([level, title, pno])
    elif toc_path.suffix == ".json":
        with open(toc_path, "r", encoding="utf-8") as f:
            toc = json.load(f)
    else:
        raise ValueError("不支持的toc文件格式!")
    # 校正层级
    levels = [v[0] for v in toc]
    diff = np.diff(levels)
    indices = np.where(diff>1)[0]
    for idx in indices:
        toc[idx][0] = toc[idx+1][0]

    doc.set_toc(toc)
    if output_path is None:
        output_path = str(p.parent / f"{p.stem}-toc.pdf")
    doc.save(output_path)

def extract_toc(doc_path: str, format: str = "txt", output_path: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    toc = doc.get_toc(simple=False)
    if format == "txt":
        if output_path is None:
            output_path = str(p.parent / f"{p.stem}-toc.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            for line in toc:
                indent = (line[0]-1)*"\t"
                f.writelines(f"{indent}{line[1]} {line[2]}\n")
    elif format == "json":
        if output_path is None:
            output_path = str(p.parent / f"{p.stem}-toc.json")
        for i in range(len(toc)):
            try:
                toc[i][-1] = toc[i][-1]['to'].y
            except:
                toc[i][-1] = 0
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(toc, f)

def transform_toc_file(toc_path: str, is_add_indent: bool = True, is_remove_trailing_dots: bool = True, add_offset: int = 0, output_path: str = None):
    if output_path is None:
        p = Path(toc_path)
        output_path = str(p.parent / f"{p.stem}-toc-clean.txt")
    with open(toc_path, "r", encoding="utf-8") as f, open(output_path, "w", encoding="utf-8") as f2:
        for line in f:
            new_line = line
            if is_remove_trailing_dots:
                new_line = re.sub("(\.\s*)+(?=\d*\s*$)", " ", new_line)
                new_line = new_line.rstrip() + "\n"
            if is_add_indent:
                res = title_preprocess(new_line)
                new_line = (res['level']-1)*'\t' + res['text'] + "\n"
            if add_offset:
                m = re.search("(\d+)(?=\s*$)", new_line)
                if m is not None:
                    pno = int(m.group(1))
                    pno = pno + add_offset
                    new_line = new_line[:m.span()[0]-1] + f" {pno}\n"
            f2.write(new_line)
