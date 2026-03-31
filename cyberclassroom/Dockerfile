FROM python:3.8
#RUN mkdir /app
WORKDIR /app
ADD . /app/
COPY requirements.txt /
# RUN pip install -U pip \
#     && pip install -r /requirements.txt
RUN pip install -U pip && pip install -r /requirements.txt && pip install uwsgi
# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# ไม่ใส่ CMD ใน Dockerfile — ให้ใช้ docker-compose เป็นตัวกำหนด