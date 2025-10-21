import os
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    DB_SERVER = os.getenv("DB_SERVER", "ms1901.gabiadb.com")
    DB_NAME = os.getenv("DB_NAME", "yujincast")
    DB_USER = os.getenv("DB_USER", "pinkyj81")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "zoskek38!!")

    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}/{DB_NAME}"
        "?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
