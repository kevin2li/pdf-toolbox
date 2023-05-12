FROM paddlecloud/paddleocr:2.6-cpu-latest
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple -r requirements.txt
CMD ["python3", "src/pdf_toolbox/__main__.py"]
