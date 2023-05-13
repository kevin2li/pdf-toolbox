import glob
import os
from pathlib import Path

import fitz
from tqdm import tqdm

from pdf_toolbox.utils import parse_range


def convert_pdf_to_images(doc_path: str, page_range: str = 'all', output_path: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    if page_range=="all":
        roi_indices = list(range(len(doc)))
    else:
        roi_indices = parse_range(page_range)

    if output_path is None:
        output_dir = p.parent / "images"
    else:
        output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    for page_index in roi_indices: # iterate over pdf pages
        page = doc[page_index] # get the page
        pix = page.get_pixmap()  # render page to an image
        savepath = str(output_dir / f"page-{page.number+1}.png")
        # pix.save(savepath)  # store image as a PNG
        pix.pil_save(savepath, quality=100, dpi=(1800,1800))

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
