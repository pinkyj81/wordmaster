FROM python:3.12-slim

# 필수 패키지 설치
RUN apt-get update && apt-get install -y curl apt-transport-https gnupg unixodbc unixodbc-dev

# Microsoft GPG 키 추가 (Render 환경에서도 안전하게 동작)
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -

# MS SQL 리포지토리 등록
RUN echo "deb [arch=amd64] https://packages.microsoft.com/ubuntu/22.04/prod jammy main" > /etc/apt/sources.list.d/mssql-release.list

# 드라이버 설치
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 복사
COPY . /app
WORKDIR /app

# Render 환경용 포트 지정
CMD gunicorn app:app --bind 0.0.0.0:$PORT
