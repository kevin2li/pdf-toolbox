# Pdf工具箱
## 安装
### 使用pip
```bash
pip install git+https://github.com/kevin2li/pdf-toolbox.git

# or 使用国内镜像源
pip install git+https://github.com/kevin2li/pdf-toolbox.git -i https://mirrors.aliyun.com/pypi/simple
```

### 使用docker
```bash
docker pull kevin2li/pdf-toolbox

# 使用(切到目标pdf所在文件夹打开终端，以切片为例)
docker run --rm -v ${PWD}:/data kevin2li/pdf-toolbox slice -r 1-10 /data/xxx.pdf
```
## 用法
### 书签管理
#### 添加书签
1. 目录来自网上渠道  
适用场景：书籍类  
方法：从网上书城找到目标书籍，一般详情页会提供目录，拷贝到本地文件再导入

1. 目录来自原始文件  
适用场景：扫描件  
方法：从原始文件(pdf、word等)提取目录，保存到本地再导入


3. 目录来自pdf本身  
适用场景：pdf自身含有目录页  
方法：用ocr识别目录文字，保存到本地再导入

**有目录**

页码文件格式如下：(通过缩进控制层级，每行最后标注页码)

![](https://minio.kevin2li.top/image-bed/blog/20230604094627.png)

命令示例：  
```bash
pdf_toolbox bookmark add from_file -t {toc_file_path} -d {offset} -o {output_path} {pdf_path}
```


**无目录**  
方法：用ocr遍历每页找到标题并记录页码，自动生成目录

命令示例：  
```bash
# 单栏pdf
pdf_toolbox bookmark add from_ocr -l ch -o {output_path} {pdf_path}

# 双栏pdf
pdf_toolbox bookmark add from_ocr -l ch -d -o {output_path} {pdf_path}
```

#### 提取目录书签 

除了自动提取目录外，本工具还支持将**已有目录**的pdf文件的目录导出为txt文件，命令如下：

```bash
# 提取为txt文件
pdf_toolbox bookmark extract -o {toc_path} {pdf_path}

# 提取为json文件(可以保留高度信息)
pdf_toolbox bookmark extract -f json -o {toc_path} {pdf_path}
```

#### 书签文件清洗
```bash
# 添加缩进
pdf_toolbox bookmark clean -i bookmark.txt

# 移除尾部多余的.
pdf_toolbox bookmark clean -r bookmark.txt

# 页码同一添加5
pdf_toolbox bookmark clean -d 5 bookmark.txt

# 组合使用
pdf_toolbox bookmark clean -ir -d 5 bookmark.txt
```

### pdf合并
```bash
# 将多个文件合并成1个文件
pdf_toolbox a.pdf b.pdf -o merged.pdf

# 将指定目录下的pdf文件合并成1个文件
pdf_toolbox path_to_pdf_dir/ -o merged.pdf

# 按照配置文件顺序合并文件(每行一个pdf文件路径)
pdf_toolbox -f seq.txt -o merged.pdf
```
### pdf拆分
```bash
# 将pdf文件按照每个部分最大10页进行拆分(最后一个部分可能不足10页)，每个部分单独存一个文件
pdf_toolbox split -p 10 -o output_dir a.pdf
```
### pdf切片
```bash
# 选取1-3页
pdf_toolbox slice -r "1-3" -o a_1_3.pdf a.pdf

# 选取第3页，第7-9页
pdf_toolbox slice -r "3,7-9" -o a_1_3.pdf a.pdf

# 调整页面顺序：将第7页调到第2页后面
pdf_toolbox slice -r "1-2,7,3-6,8-n" -o reordered.pdf a.pdf

# 拆分pdf：将","分隔的每个范围都存到单独文件
pdf_toolbox slice -m -r "1,2-10,11-20" -o output_dir -a a.pdf

```
### pdf插入
```bash
# 将b.pdf插入到a.pdf的第2页后面
pdf_toolbox insert -p 2 a.pdf b.pdf
```
### pdf旋转
```bash
# 将所有页面顺时针旋转90度
pdf_toolbox rotate -a 90 -o rotated.pdf a.pdf
```
### pdf水印
```bash
# pdf添加文本水印
pdf_toolbox watermark -t pdf --mark-text "翻版必究"  -o watermarked.pdf a.pdf

# 图片添加文本水印
pdf_toolbox watermark -t image --mark-text "翻版必究"  -o watermarked.png a.png

# pdf去除水印
pdf_toolbox watermark -t pdf --remove --watermark-color "#808080" watermark.pdf

# 图片去水印
pdf_toolbox watermark -t image --remove --watermark-color "#808080" watermark.png

```

### pdf加/解密
```bash
# 加密
pdf_toolbox encrypt --user-pass 123456 -o encrypted.pdf a.pdf

# 解密
pdf_toolbox encrypt -d --user-pass 123456 -o decrypted.pdf a.pdf

```
### pdf提取
```bash
# 提取文本
pdf_toolbox extract -t text -l ch -o output_dir a.pdf

# 提取中文pdf前10页图片
pdf_toolbox extract -t figure -l ch -r "1-10" -o output_dir a.pdf

# 提取表格
pdf_toolbox extract -t table -l ch -o output_dir a.pdf

# 提取公式
pdf_toolbox extract -t equation -l ch -o output_dir a.pdf


```
### pdf转换
```bash
# pdf转图片
pdf_toolbox convert -t pdf-to-image -o output_dir a.pdf

# 图片转pdf
pdf_toolbox convert -t image-to-pdf -o output.pdf image_dir

```
### ocr识别
```bash
# ocr识别图片
pdf_toolbox ocr -l ch -o output_dir a.png

# ocr识别pdf
pdf_toolbox ocr -l ch -r "1-4" -o output_dir a.pdf
```

### 调试
```bash
# 判断标题检测效果
pdf_toolbox debug -t title -o output_dir a.pdf

# 判断图片检测效果
pdf_toolbox debug -t figure -o output_dir a.pdf
```