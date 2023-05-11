import argparse
import copy
import glob
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
from PIL import Image
from tqdm import tqdm


def ppstructure_analysis(input_path: str):
    img = cv2.imread(input_path)
    structure_engine = PPStructure(table=False, ocr=False, show_log=False)
    result = structure_engine(img)
    return result

def plot_roi_region(input_path, type: str = 'title', output_path: str = None):
    img = cv2.imread(input_path)
    result = ppstructure_analysis(input_path)
    for item in result:
        if item['type'] == type:
            x1, y1, x2, y2 = item['bbox']
            cv2.rectangle(img, (x1, y1), (x2, y2), color=(255, 0, 0), thickness=2)
    if output_path is None:
        p = Path(input_path)
        savedir = p.parent / type
        savedir.mkdir(exist_ok=True, parents=True)
        output_path = str(savedir / p.name)
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
    res['level'] = len(m.group(1))+1
    return res

def extract_title(input_path: str, lang: str = 'ch', use_double_columns: bool = False) -> list:
    # TODO: 存在标题识别不全bug
    ocr_engine = PaddleOCR(use_angle_cls=True, lang=lang) # need to run only once to download and load model into memory
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
            print('title:', title)
            res = title_preprocess(title)
            level, title = res['level'], res['text']
            height = pos[0][1] # 左上角点的y坐标
            toc.append([level, title, page.number+1, height])
    print('-'*30)
    pprint(toc)
    print('-'*30)
    # 校正层级
    levels = [v[0] for v in toc]
    diff = np.diff(levels)
    indices = np.where(diff>1)[0]
    for idx in indices:
        toc[idx][0] = toc[idx+1][0]

    pprint(toc)
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

def parse_range(page_range: str, is_multiple: bool = False):
    # e.g.: "1-3,5-6,7-10", "1,4-5"
    page_range = page_range.strip()
    parts = page_range.split(",")
    roi_indices = []
    for part in parts:
        out = list(map(int, part.split("-")))
        if len(out) == 2:
            roi_indices.append(list(range(out[0]-1, out[1])))
        elif len(out) == 1:
            roi_indices.append([out[0]-1])
    if is_multiple:
        return roi_indices
    result = [j for i in roi_indices for j in i]
    return result

def slice_pdf(doc_path: str, page_range: str = "all", is_multiple: bool = False, output_path: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    if page_range == "all":
        roi_indices = list(range(len(doc)))
    else:
        roi_indices = parse_range(page_range, is_multiple)
    if not is_multiple:
        doc.select(roi_indices)
        if output_path is None:
            output_path = str(p.parent / f"{p.stem}-[slice].pdf")
        doc.save(output_path)
    else:
        if output_path is None:
            output_dir = p.parent / "parts"
            output_dir.mkdir(parents=True, exist_ok=True)
        for indices in roi_indices:
            doc: fitz.Document = fitz.open(doc_path)
            doc.select(indices)
            doc.save(str(output_dir / f"{p.stem}-[{indices[0]+1}-{indices[-1]+1}].pdf"))

def merge_pdf(doc_path_list: List[str], output_path: str = None):
    doc = fitz.open(doc_path_list[0])
    p = Path(doc_path_list[0])
    for doc_path in doc_path_list[1:]:
        doc_temp = fitz.open(doc_path)
        doc.insert_pdf(doc_temp)
    if output_path is None:
        output_path = str(p.parent / f"[all-merged].pdf")
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
    n1, n2 = doc.page_count, doc2.page_count
    doc.insert_pdf(doc2)
    page_range = f"1-{pos},{n1+1}-{n1+n2},{pos+1}-{n1}"
    roi_indices = parse_range(page_range)
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
        output_path = str(p.parent / f"{p.stem}-[removed].pdf")
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

def extract_text_from_pdf(doc_path: str, output_path: str = None):
    doc = fitz.open(doc_path)  # open document
    if output_path is None:
        p = Path(doc_path)
        output_path = p.parent / f'{p.stem}-text.txt'
    with open(output_path, "wb") as f:  # open text output
        for page in doc:  # iterate the document pages
            text = page.get_text().encode("utf8")  # get plain text (is in UTF-8)
            f.write(text)  # write text of page
            f.write(bytes((12,)))  # write page delimiter (form feed 0x0C)

def extract_images_from_pdf(doc_path: str, page_range: str = 'all', output_dir: str = None):
    # TODO: 提取的图片显示不全
    doc = fitz.open(doc_path) # open a document
    if output_dir is None:
        p = Path(doc_path)
        output_dir = p.parent / f"{p.stem}-images"
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

def debug_item_from_pdf(doc_path: str, page_range: str = 'all', type: str = "figure", output_dir: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    tmp_dir = p.parent / 'tmp'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    if output_dir is None:
        output_dir = p.parent / type
    else:
        output_dir = Path(output_dir) / type
    output_dir.mkdir(parents=True, exist_ok=True)
    if page_range=="all":
        roi_indices = list(range(len(doc)))
    else:
        roi_indices = parse_range(page_range)
    for page_index in tqdm(roi_indices, total=len(roi_indices)):
        page = doc[page_index] # get the page
        pix = page.get_pixmap()  # render page to an image
        savepath = str(tmp_dir / f"page-{page.number}.png")
        pix.save(savepath)  # store image as a PNG
        plot_roi_region(savepath, type, str(output_dir / f"page-{page.number}-{type}.png"))
    shutil.rmtree(tmp_dir)

def extract_item_from_pdf(doc_path: str, page_range: str = 'all', type: str = "figure", output_dir: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    tmp_dir = p.parent / 'tmp'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    if output_dir is None:
        output_dir = p.parent / type
    else:
        output_dir = Path(output_dir) / type
    output_dir.mkdir(parents=True, exist_ok=True)
    if page_range=="all":
        roi_indices = list(range(len(doc)))
    else:
        roi_indices = parse_range(page_range)
    for page_index in tqdm(roi_indices, total=len(roi_indices)):
        page = doc[page_index] # get the page
        pix = page.get_pixmap()  # render page to an image
        savepath = str(tmp_dir / f"page-{page.number}.png")
        pix.save(savepath)  # store image as a PNG
        result = ppstructure_analysis(savepath)
        result = [v for v in result if v['type']==type]
        
        idx = 1
        for item in result:
            im_show = Image.fromarray(item['img'])
            im_show.save(str(output_dir / f"page-{page.number}-{type}-{idx}.png"))
            idx += 1

def add_image_watermark(doc_path: str, watermark_path: str, page_range: str = 'all', output_path: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    if page_range=="all":
        roi_indices = list(range(len(doc)))
    else:
        roi_indices = parse_range(page_range)
    for page_index in roi_indices: # iterate over pdf pages
        page = doc[page_index] # get the page
        # insert an image watermark from a file name to fit the page bounds
        page.insert_image(page.bound(),filename=watermark_path, overlay=False)
    if output_path is None:
        output_path = str(p.parent / f"{p.stem}-[watermark].pdf")
    doc.save(output_path)

def add_text_watermark(doc_path: str, watermark_text: str, page_range: str = 'all', output_path: str = None):
    # TODO: 中文显示，样式设置，水印分散分布
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    font = fitz.Font('Helvetica')
    pos = fitz.Point(100, 100)
    if page_range=="all":
        roi_indices = list(range(len(doc)))
    else:
        roi_indices = parse_range(page_range)
    for page_index in roi_indices: # iterate over pdf pages
        page = doc[page_index] # get the page
        # page.insert_text(pos, watermark_text, fontname=font.name, fontsize=24, render_mode=3, rotate=90)
        page.insert_text(pos, watermark_text)

    if output_path is None:
        output_path = str(p.parent / f"{p.stem}-[watermark].pdf")
    doc.save(output_path)

def convert_pdf_to_images(doc_path: str, page_range: str = 'all', output_path: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    if page_range=="all":
        roi_indices = list(range(len(doc)))
    else:
        roi_indices = parse_range(page_range)

    if output_path is None:
        output_dir = p.parent / "images"
        output_dir.mkdir(parents=True, exist_ok=True)

    for page_index in roi_indices: # iterate over pdf pages
        page = doc[page_index] # get the page
        pix = page.get_pixmap()  # render page to an image
        savepath = str(output_dir / f"page-{page.number}.png")
        pix.save(savepath)  # store image as a PNG

def convert_images_to_pdf(input_path: str, format_list=["png", "jpg"], output_path: str = None):
    if output_path is None:
        p = Path(input_path)
        output_path = str(p.parent / f"[image-to-pdf].pdf")
    doc = fitz.open()
    if not os.path.isfile(input_path):
        path_list = []
        for format in format_list:
            pattern = os.path.join(input_path, f"*.{format}")
            path_list = path_list + glob.glob(pattern)
        path_list = sorted(path_list)
        for path in tqdm(path_list):
            img = fitz.open(path)  # open pic as document
            rect = img[0].rect  # pic dimension
            pdfbytes = img.convert_to_pdf()  # make a PDF stream
            img.close()  # no longer needed
            imgPDF = fitz.open("pdf", pdfbytes)  # open stream as PDF
            page = doc.new_page(width = rect.width,  # new page with ...
                            height = rect.height)  # pic dimension
            page.show_pdf_page(rect, imgPDF, 0)  # image fills the page
    else:
        img = fitz.open(input_path)
        rect = img[0].rect  # pic dimension
        pdfbytes = img.convert_to_pdf()  # make a PDF stream
        img.close()  # no longer needed
        imgPDF = fitz.open("pdf", pdfbytes)  # open stream as PDF
        page = doc.new_page(width = rect.width,  # new page with ...
                        height = rect.height)  # pic dimension
        page.show_pdf_page(rect, imgPDF, 0)  # image fills the page
    doc.save(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    
    sub_parsers = parser.add_subparsers()

    bookmark_parser = sub_parsers.add_parser("bookmark", help="书签")
    merge_parser = sub_parsers.add_parser("merge", help="合并")
    insert_parser = sub_parsers.add_parser("insert", help="插入")
    slice_parser = sub_parsers.add_parser("slice", help="切片")
    remove_parser = sub_parsers.add_parser("remove", help="删除")
    rotate_parser = sub_parsers.add_parser("rotate", help="旋转")
    watermark_parser = sub_parsers.add_parser("watermark", help="水印")
    encrypt_parser = sub_parsers.add_parser("encrypt", help="加/解密")
    extract_parser = sub_parsers.add_parser("extract", help="提取")
    convert_parser = sub_parsers.add_parser("convert", help="转换")
    debug_parser = sub_parsers.add_parser("debug", help="调试")

    # 书签
    ocr_group = bookmark_parser.add_argument_group('ocr方式')
    ocr_group.add_argument("-l", "--lang", type=str, default="ch", choices=['ch', 'en', 'fr', 'german', 'it', 'japan', 'korean', 'ru', 'chinese_cht'], dest="lang", help="pdf语言")
    ocr_group.add_argument("-d", "--double-columns", action="store_true", dest='use_double_column', default=False, help="是否双栏")
    ocr_group.add_argument("-r", "--range", type=str, default="all", dest="page_range", help="指定页面范围,例如: '1-3,7-19'")

    toc_group = bookmark_parser.add_argument_group('toc文件方式')
    toc_group.add_argument("--toc-file", type=str,default=None, dest='toc_path', help="目录文件路径")
    toc_group.add_argument("--offset", type=int, default=0, dest="offset", help="偏移量, 默认为0，计算方式：实际页码-标注页码")

    extract_group = bookmark_parser.add_argument_group('提取目录')
    extract_group.add_argument("-x", "--extract-toc", action="store_true", dest='extract_toc', default=False, help="提取目录到txt文件")

    bookmark_parser.add_argument("-o", "--output", type=str, default=None, dest="output_path", help="结果保存路径")
    bookmark_parser.add_argument("input_path", type=str, help="输入文件路径")

    bookmark_parser.set_defaults(which='bookmark')

    # 水印
    watermark_group = watermark_parser.add_mutually_exclusive_group(required=True)
    watermark_group.add_argument("-w", "--watermark-path", type=str, default=None, dest="watermark_path", help="水印图片路径")
    watermark_group.add_argument("-t", "--text", type=str, default=None, dest="watermark_text", help="水印文本")

    watermark_parser.add_argument("-r", "--range", type=str, default="all", dest="page_range", help="指定页面范围,例如: '1-3,7-19'")
    watermark_parser.add_argument("-o", "--output", type=str, default=None, dest="output_path", help="结果保存路径")
    watermark_parser.add_argument("input_path", type=str, help="输入文件路径")
    watermark_parser.set_defaults(which='watermark')

    # 加/解密
    encrypt_parser.add_argument("--user-pass", type=str, default=None, required=True, dest="user_pass", help="指定用户密码")
    encrypt_parser.add_argument("--owner-pass", type=str, default=None, dest="owner_pass", help="指定所有者密码")
    encrypt_parser.add_argument("-o", "--output", type=str, default=None, dest="output_path", help="结果保存路径")
    encrypt_parser.add_argument("-d", "--decrypt", action="store_true", dest='decrypt', default=False, help="是否解密")
    encrypt_parser.add_argument("input_path", type=str, help="输入文件路径")
    encrypt_parser.set_defaults(which='encrypt')
    
    # 旋转
    rotate_parser.add_argument("-r", "--range", type=str, default="all", dest="page_range", help="指定页面范围,例如: '1-3,7-19'")
    rotate_parser.add_argument("-o", "--output", type=str, default=None, dest="output_path", help="结果保存路径")
    rotate_parser.add_argument("-a", "--angle", type=int, default=90, choices=[90, -90, 180], dest="angle", help="旋转角度, 90表示顺时针转, -90表示逆时针转")
    rotate_parser.add_argument("input_path", type=str, help="输入文件路径")
    rotate_parser.set_defaults(which='rotate')

    # 插入
    insert_parser.add_argument("-o", "--output", type=str, default=None, dest="output_path", help="结果保存路径")
    insert_parser.add_argument("-p", "--position", type=int, default=None, required=True, dest="pos", help="插入位置(该页后面)")
    insert_parser.add_argument("input_path1", type=str, help="输入文件路径")
    insert_parser.add_argument("input_path2", type=str, help="输入文件路径")
    insert_parser.set_defaults(which='insert')

    # 切片
    slice_parser.add_argument("-r", "--range", type=str, default="all", dest="page_range", help="指定页面范围,例如: '1-3,7-19'")
    slice_parser.add_argument("-o", "--output", type=str, default=None, dest="output_path", help="结果保存路径")
    slice_parser.add_argument("-m", "--multiple", action="store_true", dest='is_multiple', default=False, help="是否分开保存")
    slice_parser.add_argument("input_path", type=str, help="输入文件路径")
    slice_parser.set_defaults(which='slice')

    # 删除
    remove_parser.add_argument("-r", "--range", type=str, default="all", dest="page_range", help="指定页面范围,例如: '1-3,7-19'")
    remove_parser.add_argument("-o", "--output", type=str, default=None, dest="output_path", help="结果保存路径")
    remove_parser.add_argument("input_path", type=str, help="输入文件路径")
    remove_parser.set_defaults(which='remove')

    # 合并
    merge_parser.add_argument("-o", "--output", type=str, default=None, dest="output_path", help="结果保存路径")
    merge_group = merge_parser.add_mutually_exclusive_group(required=True)
    merge_group.add_argument("-p", "--input-path", type=str, default=None, dest='input_path', help="输入文件路径,多个路径用','隔开")
    merge_group.add_argument("-d", "--input-dir", type=str, default=None, dest='input_dir', help="输入文件目录")
    merge_parser.set_defaults(which='merge')

    # 提取
    extract_parser.add_argument("-t", "--type", type=str, default="figure", choices=['figure', 'text', 'title', 'table', 'equation', 'header', 'footer'], dest="type", help="提取类型")
    extract_parser.add_argument("-r", "--range", type=str, default="all", dest="page_range", help="指定页面范围,例如: '1-3,7-19'")
    extract_parser.add_argument("-l", "--lang", type=str, default="ch", choices=['ch', 'en', 'fr', 'german', 'it', 'japan', 'korean', 'ru', 'chinese_cht'], dest="lang", help="pdf语言")
    extract_parser.add_argument("-o", "--output", type=str, default=None, dest="output_path", help="结果保存路径")
    extract_parser.add_argument("input_path", type=str, help="输入文件路径")
    extract_parser.set_defaults(which='extract')

    # 转换
    convert_parser.add_argument("-t", "--type", type=str, default="pdf-to-image", choices=["pdf-to-image", "image-to-pdf"], dest="type", help="转换类型")
    convert_parser.add_argument("-o", "--output", type=str, default=None, dest="output_path", help="结果保存路径")

    convert_image_group = convert_parser.add_argument_group("图片转pdf")
    convert_image_group.add_argument("-f", "--format-list", type=str, nargs="+", default=['png', 'jpg'], help="图片格式列表")

    convert_pdf_group = convert_parser.add_argument_group("pdf转图片")
    convert_pdf_group.add_argument("-r", "--range", type=str, default="all", dest="page_range", help="指定页面范围,例如: '1-3,7-19'")

    convert_parser.add_argument("input_path", type=str, help="输入文件路径或目录")

    convert_parser.set_defaults(which='convert')

    # 调试
    debug_parser.add_argument("-o", "--output", type=str, default=None, dest="output_path", help="结果保存路径")
    debug_parser.add_argument("-r", "--range", type=str, default="all", dest="page_range", help="指定页面范围,例如: '1-3,7-19'")
    debug_parser.add_argument("-t", "--type", type=str, default="figure", choices=['figure', 'text', 'title', 'table', 'equation', 'header', 'footer'], dest="type", help="指定类型")
    debug_parser.add_argument("-l", "--lang", type=str, default="ch", choices=['ch', 'en', 'fr', 'german', 'it', 'japan', 'korean', 'ru', 'chinese_cht'], dest="lang", help="pdf语言")
    debug_parser.add_argument("input_path", type=str, help="输入文件路径")
    debug_parser.set_defaults(which='debug')

    args = parser.parse_args()

    pprint(args)
    # assert False, "debug"

    if args.which == "bookmark":
        if args.toc_path is not None:
            add_toc_from_file(args.toc_path, args.input_path, offset=args.offset, output_path=args.output_path)
        elif args.extract_toc:
            extract_toc(args.input_path, args.output_path)
        else:
            add_toc(args.input_path, lang=args.lang, use_double_columns=args.use_double_column, output_path=args.output_path)
    elif args.which == "merge":
        if args.input_path is not None:
            path_list = args.input_path.split(",")
        elif args.input_dir is not None:
            path_list = glob.glob(os.path.join(args.input_dir, "*.pdf"))
        merge_pdf(path_list, args.output_path)
    elif args.which == "insert":
        insert_pdf(args.input_path1, args.input_path2, args.pos, args.output_path)
    elif args.which == "slice":
        slice_pdf(args.input_path, args.page_range, args.is_multiple, args.output_path)
    elif args.which == "remove":
        delete_pdf(args.input_path, args.page_range, args.output_path)
    elif args.which == "rotate":
        rotate_pdf(args.input_path, args.angle, args.page_range, args.output_path)
    elif args.which == "watermark":
        if args.watermark_path is not None:
            add_image_watermark(args.input_path, args.watermark_path, args.page_range, args.output_path)
        elif args.watermark_text is not None:
            add_text_watermark(args.input_path, args.watermark_text, args.page_range, args.output_path)
    elif args.which == "encrypt":
        if args.decrypt:
            decrypt_pdf(args.input_path, args.user_pass, args.output_path)
        else:
            encrypt_pdf(args.input_path, args.user_pass, args.owner_pass, args.output_path)
    elif args.which == "extract":
        if args.type in ['figure', 'table', 'equation']:
            extract_item_from_pdf(args.input_path, args.page_range, args.type, args.output_path)
        elif args.type == 'text':
            extract_text_from_pdf(args.input_path, args.output_path)
    elif args.which == 'convert':
        if args.type == "image-to-pdf":
            convert_images_to_pdf(args.input_path, args.format_list, args.output_path)
        elif args.type == "pdf-to-image":
            convert_pdf_to_images(args.input_path, args.page_range, args.output_path)
    elif args.which == "debug":
        debug_item_from_pdf(args.input_path, args.page_range, args.type, args.output_path)
