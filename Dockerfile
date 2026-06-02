FROM python:3.12-alpine

WORKDIR /.t/tmp

COPY app.py requirements.txt index.html cooking.html home_decor.html mindfulness.html fitness.html travel.html ./

EXPOSE 3002

RUN apk update && apk --no-cache add openssl bash curl &&\
    chmod +x app.py &&\
    pip install -r requirements.txt
    
CMD ["python3", "app.py"]
