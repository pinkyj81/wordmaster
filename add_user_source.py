from app import app, db
from sqlalchemy import text

with app.app_context():
    # 박영진 사용자에게 박영진 출처 추가
    check = db.session.execute(
        text("SELECT id FROM word_users WHERE user_name = :user AND source = :src"),
        {"user": "박영진", "src": "박영진"}
    ).fetchone()
    
    if not check:
        db.session.execute(
            text("INSERT INTO word_users (user_name, source) VALUES (:user, :src)"),
            {"user": "박영진", "src": "박영진"}
        )
        db.session.commit()
        print("✅ 박영진-박영진 출처 매핑 추가 완료")
    else:
        print("✅ 이미 존재합니다")
