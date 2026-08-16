FROM python:3.13-alpine3.24

WORKDIR /tmp

COPY app.py index.html __init__.py pyarmor_runtime.so ./

EXPOSE 3000

RUN apk update && apk --no-cache add openssl bash curl gcompat libgcc libstdc++ &&\
    chmod +x app.py
    
CMD ["python3", "app.py"]
