FROM python:3.13-alpine3.24

WORKDIR /tmp

COPY app.py index.html ./

EXPOSE 3000

RUN apk update && apk --no-cache add openssl bash curl &&\
    chmod +x app.py
    
CMD ["python3", "app.py"]
