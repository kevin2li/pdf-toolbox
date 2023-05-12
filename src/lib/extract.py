import shutil
from pathlib import Path

import cv2
import fitz
from PIL import Image
from tqdm import tqdm

from src.utils import parse_range, ppstructure_analysis


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
            # pix.save(savepath) # save the image as png
            pix.pil_save(savepath, quality=100, dpi=(1800,1800))
            pix = None


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
        # pix.save(savepath)  # store image as a PNG
        pix.pil_save(savepath, quality=100, dpi=(1800,1800))
        result = ppstructure_analysis(savepath)
        result = [v for v in result if v['type']==type]
        
        idx = 1
        for item in result:
            im_show = Image.fromarray(item['img'])
            im_show.save(str(output_dir / f"page-{page.number}-{type}-{idx}.png"))
            idx += 1


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
        # pix.save(savepath)  # store image as a PNG
        pix.pil_save(savepath, quality=100, dpi=(1800,1800))
        plot_roi_region(savepath, type, str(output_dir / f"page-{page.number+1}-{type}.png"))
    shutil.rmtree(tmp_dir)