# Pdf工具箱
## 安装
xx

## 用法
### 书签管理
#### 添加书签
##### 从目录文件中导入  
假设你有一个类似下面格式的目录文件(例如从网上书城复制目录文本等)，你可以使用下面命令导入目录：  
> 每行的格式要求：|{标题} {页码}|  
> 即：每行的最后的数字会被解释为页码，页码前面的部分都会被当作标题内容(首尾可以包含空白符，程序后面会自动清除)，内容与页码之间用空格隔开

![](https://minio.kevin2li.top/image-bed/vanblog/img/10a971312aeb6dd55681414f8826429d.image.png)

```bash
python main.py bookmark add -t file --toc-file {toc_file_path} --offset {offset} -o {output_path} {pdf_path}
```

##### 从ocr中自动识别 

```bash
# 单栏pdf
python main.py bookmark add -t ocr -l ch -o {output_path} {pdf_path}

# 双栏pdf
python main.py bookmark add -t ocr -l ch -d -o {output_path} {pdf_path}
```

#### 提取书签 

除了自动提取目录外，本工具还支持将**已有目录**的pdf文件的目录导出为txt文件，命令如下：

```bash
python main.py bookmark extract -o {toc_path} {pdf_path}
```

导出的目录txt文件类似如下：  
![](https://minio.kevin2li.top/image-bed/202305102236751.png)

#### 书签文件清洗
```bash
# 添加缩进
python main.py bookmark clean -i bookmark.txt

# 移除尾部多余的.
python main.py bookmark clean -r bookmark.txt

# 页码同一添加5
python main.py bookmark clean -d 5 bookmark.txt

# 组合使用
python main.py bookmark clean -ir -d 5 bookmark.txt
```

### pdf合并
```bash
# 将多个文件合并成1个文件
python main.py a.pdf b.pdf -o merged.pdf

# 将指定目录下的pdf文件合并成1个文件
python main.py path_to_pdf_dir/ -o merged.pdf
```
### pdf拆分
```bash
# 将pdf文件按照每个部分最大10页进行拆分(最后一个部分可能不足10页)，每个部分单独存一个文件
python main.py split -p 10 -o output_dir a.pdf
```
### pdf切片
```bash
# 选取1-3页
python main.py slice -r "1-3" -o a_1_3.pdf a.pdf

# 选取第3页，第7-9页
python main.py slice -r "3,7-9" -o a_1_3.pdf a.pdf

# 调整页面顺序：将第7页调到第2页后面
python main.py slice -r "1-2,7,3-6,8-n" -o reordered.pdf a.pdf

# 拆分pdf：将","分隔的每个范围都存到单独文件
python main.py slice -m -r "1,2-10,11-20" -o output_dir -a a.pdf

```
### pdf插入
```bash
# 将b.pdf插入到a.pdf的第2页后面
python main.py insert -p 2 a.pdf b.pdf
```
### pdf旋转
```bash
# 将所有页面顺时针旋转90度
python main.py rotate -a 90 -o rotated.pdf a.pdf
```
### pdf水印
```bash
# pdf添加文本水印
python main.py watermark -t pdf --mark-text "翻版必究"  -o watermarked.pdf a.pdf

# 图片添加文本水印
python main.py watermark -t image --mark-text "翻版必究"  -o watermarked.png a.png

# pdf去除水印
python main.py watermark -t pdf --remove --watermark-color "#808080" watermark.pdf

# 图片去水印
python main.py watermark -t image --remove --watermark-color "#808080" watermark.png

```

### pdf加/解密
```bash
# 加密
python main.py encrypt --user-pass 123456 -o encrypted.pdf a.pdf

# 解密
python main.py encrypt -d --user-pass 123456 -o decrypted.pdf a.pdf

```
### pdf提取
```bash
# 提取文本
python main.py extract -t text -l ch -o output_dir a.pdf

# 提取中文pdf前10页图片
python main.py extract -t figure -l ch -r "1-10" -o output_dir a.pdf

# 提取表格
python main.py extract -t table -l ch -o output_dir a.pdf

# 提取公式
python main.py extract -t equation -l ch -o output_dir a.pdf


```
### pdf转换
```bash
# pdf转图片
python main.py convert -t pdf-to-image -o output_dir a.pdf

# 图片转pdf
python main.py convert -t image-to-pdf -o output.pdf image_dir

```
### ocr识别
```bash
# ocr识别图片
python main.py ocr -l ch -o output_dir a.png

# ocr识别pdf
python main.py ocr -l ch -r "1-4" -o output_dir a.pdf
```

### 调试
```bash
# 判断标题检测效果
python main.py debug -t title -o output_dir a.pdf

# 判断图片检测效果
python main.py debug -t figure -o output_dir a.pdf
```