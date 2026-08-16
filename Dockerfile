FROM python:3.13-alpine3.22

WORKDIR /tmp

COPY app.py index.html pyarmor_runtime_000000 ./

EXPOSE 3000

RUN apk update && apk --no-cache add openssl bash curl &&\
    chmod +x app.py
    
CMD ["python3", "app.py"]
