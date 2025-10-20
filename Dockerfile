# Python 3.12 slim 이미지 기반
FROM python:3.12-slim

# 필수 시스템 패키지 설치
RUN apt-get update && \
    apt-get install -y curl apt-transport-https gnupg unixodbc unixodbc-dev && \
    mkdir -p /etc/apt/keyrings && \
    curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/keyrings/microsoft.gpg && \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/ubuntu/22.04/prod jammy main" > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 && \
    cp /opt/microsoft/msodbcsql18/lib64/libodbc.so.2 /usr/lib/x86_64-linux-gnu/ && \
    rm -rf /var/lib/apt/lists/*

# Python 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 복사 및 실행 준비
WORKDIR /app
COPY . /app

# 포트 및 실행 명령
EXPOSE 8080
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]
