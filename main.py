import argparse
import os
import re
import shutil
from pathlib import Path
from pprint import pprint
from typing import List

import cv2
import fitz
import numpy as np
from paddleocr import PaddleOCR, PPStructure
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
    title = title.rstrip()
    res = {}
    # 匹配：1.1.1 标题
    m = re.match("\s*((\d+\.?)+)\s*(.+)", title)
    if m is not None:
        res['text'] = f"{m.group(1)} {m.group(3)}"
        res['level'] = len(m.group(1).split("."))
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
    res['text'] = f"{m.group(2)}"
    res['level'] = len(m.group(1))
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
    if output_path is None:
        output_path = str(p.parent / f"{p.stem}-[toc].txt")
    with open(output_path, "w") as f:
        for line in out:
            indent = (line[0]-1)*"\t"
            f.writelines(f"{indent}{line[1]} {line[2]}\n")

def parse_range(page_range: str):
    # e.g.: "1-3,5-6,7-10"
    page_range = page_range.strip()
    parts = page_range.split(",")
    roi_indices = []
    for part in parts:
        a, b = list(map(int, part.split("-")))
        roi_indices.extend(list(range(a-1, b)))
    return roi_indices

def slice_pdf(doc_path: str, page_range: str = "all", output_path: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    if page_range == "all":
        roi_indices = list(range(len(doc)))
    else:
        roi_indices = parse_range(page_range)
    doc.select(roi_indices)
    if output_path is None:
        output_path = str(p.parent / f"{p.stem}-[slice].pdf")
    doc.save(output_path)

def merge_pdf(doc_path_list: List[str], output_path: str = None):
    doc = fitz.open(doc_path_list[0])
    p = Path(doc_path_list[0])
    for doc_path in doc_path_list[1:]:
        doc_temp = fitz.open(doc_path)
        doc.insert_pdf(doc_temp)
    if output_path is None:
        output_path = str(p.parent / f"{p.stem}-[merged].pdf")
    doc.save(output_path)

def rotate_pdf(doc_path: str, angle: int, page_range: str = "all", output_path: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    if page_range=="all":
        roi_indices = list(range(len(doc)))
    else:
        roi_indices = parse_range(page_range)
    for page_index in roi_indices: # iterate over pdf pages
        page = doc[page_index] # get the page
        page.set_rotation(angle) # rotate the page
    if output_path is None:
        output_path = str(p.parent / f"{p.stem}-[rotated].pdf")
    doc.save(output_path)

def insert_pdf(doc_path1: str, doc_path2: str, pos: int, output_path: str = None):
    p = Path(doc_path1)
    doc: fitz.Document = fitz.open(doc_path1)
    doc2: fitz.Document = fitz.open(doc_path2)
    doc.insert_pdf(doc2)
    n1, n2 = doc.page_count, doc2.page_count
    page_range = f"1-{pos},{n1+1}-{n1+n2},{pos+1}-{n1}"
    roi_indices =  page_range(page_range)
    doc.select(roi_indices)
    if output_path is None:
        output_path = str(p.parent / f"{p.stem}-[inserted].pdf")
    doc.save(output_path)

def delete_pdf(doc_path: str, page_range: str, output_path: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    if page_range=="all":
        roi_indices = list(range(len(doc)))
    else:
        roi_indices = parse_range(page_range)
    doc.delete_pages(roi_indices)
    if output_path is None:
        output_path = str(p.parent / f"{p.stem}-[rotated].pdf")
    doc.save(output_path)

def encrypt_pdf(doc_path: str, user_password: str, owner_password: str = None, output_path: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    perm = int(
        fitz.PDF_PERM_ACCESSIBILITY # always use this
        | fitz.PDF_PERM_PRINT # permit printing
        | fitz.PDF_PERM_COPY # permit copying
        | fitz.PDF_PERM_ANNOTATE # permit annotations
    )
    encrypt_meth = fitz.PDF_ENCRYPT_AES_256 # strongest algorithm
    if output_path is None:
        output_path = str(p.parent / f"{p.stem}-[encrypt].pdf")
    doc.save(
        output_path,
        encryption=encrypt_meth, # set the encryption method
        owner_pw=owner_password, # set the owner password
        user_pw=user_password, # set the user password
        permissions=perm, # set permissions
    )

def decrypt_pdf(doc_path: str, password: str, output_path: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    if doc.isEncrypted:
        doc.authenticate(password)
        n = doc.page_count
        doc.select(range(n))
    if output_path is None:
        output_path = str(p.parent / f"{p.stem}-[decrypt].pdf")
    doc.save(output_path)

def extract_text_from_pdf(doc_path: str, output_dir: str = None):
    pass

def extract_images_from_pdf(doc_path: str, page_range: str = 'all', output_dir: str = None):
    doc = fitz.open(doc_path) # open a document
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if page_range=="all":
        roi_indices = list(range(len(doc)))
    else:
        roi_indices = parse_range(page_range)
    for page_index in roi_indices: # iterate over pdf pages
        page = doc[page_index] # get the page
        image_list = page.get_images()

        # print the number of images found on the page
        if image_list:
            print(f"Found {len(image_list)} images on page {page_index}")
        else:
            print("No images found on page", page_index)

        for image_index, img in enumerate(image_list, start=1): # enumerate the image list
            xref = img[0] # get the XREF of the image
            pix = fitz.Pixmap(doc, xref) # create a Pixmap
            if pix.n - pix.alpha > 3: # CMYK: convert to RGB first
                pix = fitz.Pixmap(fitz.csRGB, pix)
            savepath = str(output_dir / f"page_{page_index}-image_{image_index}.png")
            pix.save(savepath) # save the image as png
            pix = None

def add_watermark(doc_path: str, watermark_path: str, output_path: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    for page_index in range(len(doc)): # iterate over pdf pages
        page = doc[page_index] # get the page
        # insert an image watermark from a file name to fit the page bounds
        page.insert_image(page.bound(),filename=watermark_path, overlay=False)
    if output_path is None:
        output_path = str(p.parent / f"{p.stem}-[watermark].pdf")
    doc.save(output_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path", type=str)
    parser.add_argument("-o", "--output", type=str, default=None, dest="output_path", help="结果保存路径")
    parser.add_argument("-r", "--range", type=str, default="all", dest="page_range", help="指定页面范围,例如: '1-3,7-19'")
    
    # 书签
    group = parser.add_argument_group('书签')
    
    group.add_argument("--lang", type=str, default="ch", choices=['ch', 'en', 'fr', 'german', 'it', 'japan', 'korean', 'ru', 'chinese_cht'], dest="lang", help="pdf语言(使用ocr方式生成目录建议指定)")
    group.add_argument("--double-columns", action="store_true", dest='use_double_column', default=False, help="是否双栏(使用ocr方式生成目录建议指定)")

    group.add_argument("--toc-file", type=str,default=None, dest='toc_path', help="目录文件路径(使用目录文件方式需要指定)")
    group.add_argument("--offset", type=int, default=0, dest="offset", help="偏移量，默认为0(使用目录文件方式需要指定)，计算方式：实际页码-标注页码")

    group.add_argument("-x", "--extract-toc", action="store_true", dest='extract_toc', default=False, help="提取目录到txt文件")

    # 书签/合并/插入/删除/截取/旋转/水印等
    group3 = parser.add_mutually_exclusive_group()
    group3.add_argument("--bookmark",  action="store_true", dest='toc', default=False, help="生成书签")
    group3.add_argument("--merge",  action="store_true", dest='merge', default=False, help="合并页面")
    group3.add_argument("--insert",  action="store_true", dest='insert', default=False, help="插入页面")
    group3.add_argument("--slice",  action="store_true", dest='slice', default=False, help="截取页面")
    group3.add_argument("--remove",  action="store_true", dest='remove', default=False, help="删除页面")
    group3.add_argument("--rotate",  action="store_true", dest='rotate', default=False, help="旋转页面")
    group3.add_argument("--extract-images",  action="store_true", dest='extract_image', default=False, help="提取图片")
    group3.add_argument("--watermark",  action="store_true", dest='rotate', default=False, help="添加水印")
    group3.add_argument("--encrypt",  action="store_true", dest='rotate', default=False, help="加密pdf")
    group3.add_argument("--decrypt",  action="store_true", dest='rotate', default=False, help="解密pdf")

    # 水印
    group4 = parser.add_argument_group('水印')
    group4.add_argument("-w", "--watermark-path", type=str, default=None, dest="watermark_path", help="水印图片路径")


    # 加解密
    group2 = parser.add_argument_group('加解密')
    group2.add_argument("-p", "--user-pass", type=str, default="", dest="user_pass", help="指定用户密码")
    group2.add_argument("--owner-pass", type=str, default="", dest="owner_pass", help="指定所有者密码")


    args = parser.parse_args()

    pprint(args)
    assert False, "debug"
    if args.toc_path is not None:
        add_toc_from_file(args.toc_path, args.input_path, offset=args.offset, output_path=args.output_path)
    elif args.extract_toc:
        extract_toc(args.input_path, args.output_path)
    else:
        add_toc(args.input_path, lang=args.lang, use_double_columns=args.use_double_column, output_path=args.output_path)
