import argparse
import glob
import os
from pprint import pprint

from src.lib.basic import (delete_pdf, insert_pdf, merge_pdf, rotate_pdf,
                           slice_pdf)
from src.lib.bookmark import add_toc_from_ocr, add_toc_from_file, extract_toc, transform_toc_file
from src.lib.convert import convert_images_to_pdf, convert_pdf_to_images
from src.lib.encrypt import decrypt_pdf, encrypt_pdf
from src.lib.extract import (debug_item_from_pdf, extract_item_from_pdf,
                             extract_text_from_pdf)
from src.lib.watermark import (add_mark_to_image, add_mark_to_pdf,
                               remove_mark_from_image, remove_mark_from_pdf)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    
    sub_parsers = parser.add_subparsers()

    bookmark_parser  = sub_parsers.add_parser("bookmark", help="书签")
    merge_parser     = sub_parsers.add_parser("merge", help="合并")
    insert_parser    = sub_parsers.add_parser("insert", help="插入")
    slice_parser     = sub_parsers.add_parser("slice", help="切片")
    remove_parser    = sub_parsers.add_parser("remove", help="删除")
    rotate_parser    = sub_parsers.add_parser("rotate", help="旋转")
    watermark_parser = sub_parsers.add_parser("watermark", help="水印")
    encrypt_parser   = sub_parsers.add_parser("encrypt", help="加/解密")
    extract_parser   = sub_parsers.add_parser("extract", help="提取")
    convert_parser   = sub_parsers.add_parser("convert", help="转换")
    ocr_parser       = sub_parsers.add_parser("ocr", help="OCR识别")
    debug_parser     = sub_parsers.add_parser("debug", help="调试")

    # 书签
    bookmark_subparsers     = bookmark_parser.add_subparsers()
    bookmark_add_parser     = bookmark_subparsers.add_parser("add", help="添加书签")
    bookmark_extract_parser = bookmark_subparsers.add_parser("extract", help="提取书签")
    bookmark_clean_parser   = bookmark_subparsers.add_parser("clean", help="清洗书签文件")

    ## 书签添加
    bookmark_add_parser.add_argument("-t", "--type", type=str, choices=['ocr', 'file'], default='from_file', dest='type', help='添加方式类型')
    bookmark_add_parser.add_argument("input_path", type=str, help="输入文件路径")
    bookmark_add_parser.add_argument("-o", "--output", type=str, default=None, dest="output_path", help="结果保存路径")

    bookmark_add_ocr_group = bookmark_add_parser.add_argument_group('ocr方式')
    bookmark_add_ocr_group.add_argument("-l", "--lang", type=str, default="ch", choices=['ch', 'en', 'fr', 'german', 'it', 'japan', 'korean', 'ru', 'chinese_cht'], dest="lang", help="pdf语言")
    bookmark_add_ocr_group.add_argument("-d", "--double-columns", action="store_true", dest='use_double_column', default=False, help="是否双栏")
    bookmark_add_ocr_group.add_argument("-r", "--range", type=str, default="all", dest="page_range", help="指定页面范围,例如: '1-3,7-19'")

    bookmark_add_toc_group = bookmark_add_parser.add_argument_group('toc文件方式')
    bookmark_add_toc_group.add_argument("--toc-file", type=str,default=None, dest='toc_path', help="目录文件路径")
    bookmark_add_toc_group.add_argument("--offset", type=int, default=0, dest="offset", help="偏移量, 默认为0，计算方式：实际页码-标注页码")

    bookmark_add_parser.set_defaults(bookmark_which='add')

    ## 书签清洗
    bookmark_clean_group = bookmark_clean_parser.add_argument_group('toc文件清洗')
    bookmark_clean_group.add_argument("-i", "--add-indent", action="store_true", dest='is_add_indent', default=False, help="是否添加缩进")
    bookmark_clean_group.add_argument("-r", "--remove-trailing-dots", action="store_true", dest='is_remove_trailing_dots', default=False, help="是否移除尾部'.'")
    bookmark_clean_group.add_argument("-d", "--add-offset", type=int, dest='add_offset', default=0, help="页码加偏移量")

    bookmark_clean_parser.add_argument("input_path", type=str, help="输入文件路径")
    bookmark_clean_parser.add_argument("-o", "--output", type=str, default=None, dest="output_path", help="结果保存路径")
    bookmark_clean_parser.set_defaults(bookmark_which='clean')

    ## 书签提取
    bookmark_extract_parser.add_argument("input_path", type=str, help="输入文件路径")
    bookmark_extract_parser.add_argument("-o", "--output", type=str, default=None, dest="output_path", help="结果保存路径")
    bookmark_extract_parser.set_defaults(bookmark_which='extract')

    bookmark_parser.set_defaults(which='bookmark')

    # 水印
    watermark_text_group = watermark_parser.add_argument_group("文本水印")
    watermark_text_group.add_argument("--mark-text", type=str, default=None, dest="mark_text", help="水印文本")
    watermark_text_group.add_argument("--font-size", type=int, default=50, dest="font_size", help="水印字体大小")
    watermark_text_group.add_argument("--angle", type=int, default=30, dest="angle", help="水印旋转角度")
    watermark_text_group.add_argument("--space", type=int, default=75, dest="space", help="水印文本间距")
    watermark_text_group.add_argument("--color", type=str, default="#808080", dest="color", help="水印文本颜色")
    watermark_text_group.add_argument("--opacity", type=float, default=0.15, dest="opacity", help="水印不透明度")
    watermark_text_group.add_argument("--font-height-crop", type=str, default="1.2", dest="font_height_crop")
    watermark_text_group.add_argument("--font-family", type=str, default="src/assets/SIMKAI.TTF", dest="font_family", help="水印字体路径")
    watermark_text_group.add_argument("--quality", type=int, default=80, dest="quality", help="水印图片保存质量")
    
    watermark_remove_group = watermark_parser.add_argument_group("去除水印")
    watermark_remove_group.add_argument("--remove", action="store_true", dest='remove', default=False, help="是否去除水印")
    watermark_remove_group.add_argument("--watermark-color", type=str, default="#808080", dest="watermark_color", help="水印文本颜色")

    watermark_parser.add_argument("-t", "--type", type=str, default="pdf", choices=['pdf', 'image'], dest="type", help="被加水印对象类型")
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
    merge_parser.add_argument("input_path", type=str, nargs="+", default=None, help="输入文件路径或目录")
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

    # OCR
    ocr_parser.add_argument("-o", "--output", type=str, default=None, dest="output_path", help="结果保存路径")
    ocr_parser.add_argument("-r", "--range", type=str, default="all", dest="page_range", help="指定页面范围,例如: '1-3,7-19'")
    ocr_parser.add_argument("-l", "--lang", type=str, default="ch", choices=['ch', 'en', 'fr', 'german', 'it', 'japan', 'korean', 'ru', 'chinese_cht'], dest="lang", help="pdf语言")
    ocr_parser.add_argument("-d", "--offset", type=float, default=5., dest="offset", help="判断同一行的偏移量")
    ocr_parser.add_argument("input_path", type=str, help="输入文件路径")
    ocr_parser.set_defaults(which='ocr')

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
        if args.bookmark_which == "add":
            if args.type == 'ocr':
                add_toc_from_ocr(args.input_path, lang=args.lang, use_double_columns=args.use_double_column, output_path=args.output_path)
            elif args.type == 'file':
                add_toc_from_file(args.toc_path, args.input_path, offset=args.offset, output_path=args.output_path)
        elif args.bookmark_which == "clean":
            transform_toc_file(args.input_path, args.is_add_indent, args.is_remove_trailing_dots, args.add_offset, args.output_path)
        elif args.bookmark_which == "extract":
            extract_toc(args.input_path, args.output_path)
    elif args.which == "merge":
        if len(args.input_path) == 1:
            path_list = glob.glob(os.path.join(args.input_path[0], "*.pdf"))
        else:
            path_list = args.input_path
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
        if not args.remove:
            assert args.mark_text is None, "you must specify mark_text with '--mark-text'" 
            mark_args = {
                "size": args.font_size,
                "space": args.space,
                "angle": args.angle,
                "color": args.color,
                "opacity": args.opacity,
                "font_family": args.font_family,
                "font_height_crop": args.font_height_crop,
            }
            if args.type == "pdf":
                add_mark_to_pdf(args.input_path, args.mark_text, args.quality, **mark_args)
            elif args.type == "image":
                add_mark_to_image(args.input_path, args.mark_text, args.quality, **mark_args)
        else:
            if args.type == "pdf":
                remove_mark_from_pdf(args.input_path, args.watermark_color, args.output_path)
            elif args.type == "image":
                remove_mark_from_image(args.input_path, args.watermark_color, args.output_path)
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
    elif args.which == "ocr":
        # if args.input_path
        pass
    elif args.which == "debug":
        debug_item_from_pdf(args.input_path, args.page_range, args.type, args.output_path)
