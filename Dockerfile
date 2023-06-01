FROM python:3.10
RUN apt update && apt install ffmpeg libsm6 libxext6 -y && pip install git+https://github.com/kevin2li/pdf-toolbox.git
WORKDIR /data
ENTRYPOINT [ "pdf_toolbox" ]
