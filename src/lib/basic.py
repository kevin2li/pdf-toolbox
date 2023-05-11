import glob
import os
from pathlib import Path
from typing import List

import fitz
from tqdm import tqdm

from src.utils import parse_range


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
