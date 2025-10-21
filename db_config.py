import os
import urllib.parse
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    # ✅ 환경변수 불러오기 (Render 대시보드의 Environment 탭에서 설정)
    DB_SERVER = os.getenv("DB_SERVER", "ms1901.gabiadb.com")
    DB_NAME = os.getenv("DB_NAME", "yujincast")
    DB_USER = os.getenv("DB_USER", "pinkyj81")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "zoskek38!!")

    # ✅ 비밀번호 URL 인코딩 (특수문자 포함 시 안전하게 처리)
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD)

    # ✅ SQLAlchemy 연결 문자열 (SSL 인증 문제 해결 포함)
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mssql+pyodbc://{DB_USER}:{encoded_password}@{DB_SERVER}/{DB_NAME}"
        "?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes"
    )

    # ✅ 기타 설정
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
