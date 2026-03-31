FROM python:3.8
#RUN mkdir /app
WORKDIR /app
ADD . /app/
COPY requirements.txt /
RUN pip install -U pip \
    && pip install -r /requirements.txt

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# EXPOSE 8080
#CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
#CMD ["uwsgi", "--http", ":8000" ,"--module" ,"cyberclassroom.wsgi"]
CMD ["uwsgi", "web1.ini"]
# CMD ["uwsgi","--http-socket" ,":8080" ,"--module" ,"webapp.wsgi","--chmod-socket=664"]
#OK
# CMD ["uwsgi","--socket" ,":8080" ,"--wsgi-file" ,"test.py"] 
# CMD ["uwsgi","--socket" ,":8080" ,"--module" ,"cyberclassroom.wsgi","--chmod-socket=664"]