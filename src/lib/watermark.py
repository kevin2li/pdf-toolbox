# adapted from: https://github.com/2Dou/watermarker/blob/master/marker.py
import math
from pathlib import Path
from PIL import Image, ImageFont, ImageDraw, ImageEnhance, ImageChops, ImageOps


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
    font_height_crop: str="1.2",
    font_family     : str = "src/assets/SIMKAI.TTF"
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


def add_mark(img_path, mark_func, quality: int = 80, output_path: str = None):
    im = Image.open(img_path)
    im = ImageOps.exif_transpose(im)

    image = mark_func(im)
    if output_path is None:
        p = Path(img_path)
        output_path = p.parent / f"{p.stem}-watermarked{p.suffix}"
    image.save(output_path, quality=quality)

if __name__ == "__main__":
    mark_func = gen_mark("绝版", size=50)
    add_mark("/home/likai/code/pdf_tocgen/assets/test.png", mark_func)