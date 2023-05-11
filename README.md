# Pdf自动目录生成器
## 安装
xx

## 用法
### 从目录文件中导入  
假设你有一个类似下面格式的目录文件(例如从网上书城复制目录文本等)，你可以使用下面命令导入目录：  
> 每行的格式要求：|{标题} {页码}|  
> 即：每行的最后的数字会被解释为页码，页码前面的部分都会被当作标题内容(首尾可以包含空白符，程序后面会自动清除)，内容与页码之间用空格隔开

![](https://minio.kevin2li.top/image-bed/vanblog/img/10a971312aeb6dd55681414f8826429d.image.png)

```bash
python main.py -t {toc_path} --offset {offset} -o {output_path} {pdf_path}
```

### 自动识别标题生成目录  

```bash
python main.py -o {output_path} {pdf_path}
```

### 提取目录  

除了自动提取目录外，本工具还支持将**已有目录**的pdf文件的目录导出为txt文件，命令如下：

```bash
python main.py -x -o {toc_path} {pdf_path}
```

导出的目录txt文件类似如下：  
![](https://minio.kevin2li.top/image-bed/202305102236751.png)