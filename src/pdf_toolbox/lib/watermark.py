# partial adapted from: https://github.com/2Dou/watermarker/blob/master/marker.py
import math
import shutil
from itertools import product
from pathlib import Path
from typing import Tuple, Union

import fitz
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFont, ImageOps

from pdf_toolbox.lib.convert import convert_images_to_pdf

fontpath = str((Path(__file__).parent.parent / "assets" / "SIMKAI.TTF").absolute())

def set_opacity(im, opacity):
    '''
    设置水印透明度
    '''
    assert opacity >= 0 and opacity <= 1

    alpha = im.split()[3]
    alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
    im.putalpha(alpha)
    return im

def crop_image(im):
    '''裁剪图片边缘空白'''
    bg = Image.new(mode='RGBA', size=im.size)
    diff = ImageChops.difference(im, bg)
    del bg
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)
    return im


def gen_mark(
    mark_text       : str,
    size            : int = 50,
    space           : int = 75,
    angle           : int = 30,
    color           : str = "#808080",
    opacity         : float=0.15,
    font_family     : str = fontpath,
    font_height_crop: str="1.2",
    ): 
    """生成水印图片，返回添加水印的函数

    Args:
        mark_text (str): 水印文本
        size (int, optional): font size of text. Defaults to 50.
        space (int, optional): space between watermarks. Defaults to 75.
        angle (int, optional): rotate angle of watermarks. Defaults to 30.
        color (str, optional): text color. Defaults to "#808080".
        opacity (float, optional): opacity of watermarks. Defaults to 0.15.
        font_height_crop (float, optional): change watermark font height crop float will be parsed to factor; int will be parsed to value default is '1.2', meaning 1.2 times font size
                       this useful with CJK font, because line height may be higher than size. Defaults to 1.2.
        font_family (str, optional): font family of text. Defaults to "../assets/青鸟华光简琥珀.ttf".
    """    
    # 字体宽度、高度
    is_height_crop_float = '.' in font_height_crop  # not good but work
    width = len(mark_text) * size
    if is_height_crop_float:
        height = round(size * float(font_height_crop))
    else:
        height = int(font_height_crop)

    # 创建水印图片(宽度、高度)
    mark = Image.new(mode='RGBA', size=(width, height))

    # 生成文字
    draw_table = ImageDraw.Draw(im=mark)
    draw_table.text(xy=(0, 0),
                    text=mark_text,
                    fill=color,
                    font=ImageFont.truetype(font_family,
                                            size=size))
    del draw_table

    # 裁剪空白
    mark = crop_image(mark)

    # 透明度
    set_opacity(mark, opacity)

    def mark_im(im):
        ''' 在im图片上添加水印 im为打开的原图'''

        # 计算斜边长度
        c = int(math.sqrt(im.size[0] * im.size[0] + im.size[1] * im.size[1]))

        # 以斜边长度为宽高创建大图（旋转后大图才足以覆盖原图）
        mark2 = Image.new(mode='RGBA', size=(c, c))

        # 在大图上生成水印文字，此处mark为上面生成的水印图片
        y, idx = 0, 0
        while y < c:
            # 制造x坐标错位
            x = -int((mark.size[0] + space) * 0.5 * idx)
            idx = (idx + 1) % 2

            while x < c:
                # 在该位置粘贴mark水印图片
                mark2.paste(mark, (x, y))
                x = x + mark.size[0] + space
            y = y + mark.size[1] + space

        # 将大图旋转一定角度
        mark2 = mark2.rotate(angle)

        # 在原图上添加大图水印
        if im.mode != 'RGBA':
            im = im.convert('RGBA')
        im.paste(mark2,  # 大图
                 (int((im.size[0] - c) / 2), int((im.size[1] - c) / 2)),  # 坐标
                 mask=mark2.split()[3])
        del mark2
        return im

    return mark_im


def add_mark_to_image(img_path, mark_text: str, quality: int = 80, output_path: str = None, **mark_args):
    im = Image.open(img_path)
    im = ImageOps.exif_transpose(im)
    mark_func = gen_mark(mark_text, **mark_args)
    image = mark_func(im)
    if output_path is None:
        p = Path(img_path)
        output_path = p.parent / f"{p.stem}-watermarked{p.suffix}"
    image.save(output_path, quality=quality)

def add_mark_to_pdf(doc_path: str, mark_text: str, quality: int = 80, output_path: str = None, **mark_args):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    tmp_dir = p.parent / 'tmp'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    page = doc.load_page(0)

    blank = np.ones((int(page.rect[3]), int(page.rect[2]), 3))
    blank_savepath = tmp_dir / "blank.png"
    plt.imsave(blank_savepath, blank)
    mark_savepath = tmp_dir / "watermark.png"
    add_mark_to_image(blank_savepath, mark_text, quality=quality, output_path=mark_savepath, **mark_args)

    for page_index in range(doc.page_count):
        page = doc[page_index]
        page.insert_image(
            page.rect,                  # where to place the image (rect-like)
            filename=mark_savepath,     # image in a file
            overlay=False,          # put in foreground
        )
    if output_path is None:
        p = Path(doc_path)
        output_path = p.parent / f"{p.stem}-watermarked{p.suffix}"
    doc.save(output_path)

def color_to_rgb(color):
    import re

    from matplotlib import colors

    if isinstance(color, str):
        # 检查是否为颜色名称
        if color in colors.CSS4_COLORS:
            return colors.to_rgb(color)
        # 检查是否为十六进制码
        elif re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color):
            return colors.to_rgb(color)
        else:
            raise ValueError('Unsupported color format')
    elif isinstance(color, tuple):
        # 检查是否为 RGB 或 RGBA 值
        if len(color) in [3, 4] and all(isinstance(c, int) and 0 <= c <= 255 for c in color):
            return colors.to_rgb(color)
        else:
            raise ValueError('Unsupported color format')
    else:
        raise TypeError('Invalid argument type')

def remove_mark_from_image(img_path: str, water_mark_color: Union[str, Tuple[int, int, int], Tuple[int, int, int, float]], output_path: str = None):
    p = Path(img_path)
    threshold = sum(np.array(color_to_rgb(water_mark_color))*255)
    img = Image.open(img_path)
    width, height = img.size
    for y in range(height):
        for x in range(width):
            if sum(img.getpixel((x, y))) >= threshold:
                img.putpixel((x, y), (255, 255, 255))
    if output_path is None:
        p = Path(img_path)
        output_path = p.parent / f"{p.stem}-remove-watermark{p.suffix}"
    img.save(output_path, quality=100, dpi=(1800,1800))

def remove_mark_from_pdf(doc_path: str, water_mark_color: Union[str, Tuple[int, int, int], Tuple[int, int, int, float]], output_path: str = None):
    doc: fitz.Document = fitz.open(doc_path)
    p = Path(doc_path)
    threshold = sum(np.array(color_to_rgb(water_mark_color))*255)
    tmp_dir = p.parent / 'tmp'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    for page_index in range(doc.page_count):
        page = doc[page_index]
        pix = page.get_pixmap()
        #遍历图片中的宽和高，如果像素的rgb值总和大于510，就认为是水印，转换成255，255,255-->即白色
        for pos in product(range(pix.width), range(pix.height)):
            if sum(pix.pixel(pos[0], pos[1])) >= threshold:
                pix.set_pixel(pos[0], pos[1], (255, 255, 255))
        savepath = tmp_dir / f"{page.number+1}.png"
        pix.pil_save(savepath, quality=100, dpi=(page.rect[3], page.rect[2]))

    if output_path is None:
        p = Path(doc_path)
        output_path = p.parent / f"{p.stem}-remove-watermark{p.suffix}"
    convert_images_to_pdf(tmp_dir, ['png'], output_path)
    shutil.rmtree(tmp_dir)

