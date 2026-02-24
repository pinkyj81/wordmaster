from app import app, db
from sqlalchemy import text

with app.app_context():
    result = db.session.execute(
        text("SELECT TOP 5 word, meaning, pronunciation, language FROM words_rows WHERE language='chinese'")
    ).fetchall()
    
    print("한자 데이터 확인:")
    print("-" * 60)
    for r in result:
        print(f"한자: {r.word} | 뜻: {r.meaning} | 음독: {r.pronunciation} | 언어: {r.language}")
