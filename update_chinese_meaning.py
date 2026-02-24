from app import app, db
from sqlalchemy import text

with app.app_context():
    # 모든 한자의 meaning을 "뜻 음" 형식으로 업데이트
    query = text("""
        UPDATE words_rows
        SET meaning = meaning + ' ' + pronunciation
        WHERE language = 'chinese'
        AND pronunciation IS NOT NULL
        AND pronunciation != ''
        AND meaning NOT LIKE '% ' + pronunciation
    """)
    
    result = db.session.execute(query)
    db.session.commit()
    
    print(f"✅ {result.rowcount}개의 한자 meaning을 '뜻 음' 형식으로 업데이트 완료")
    
    # 확인
    check = db.session.execute(
        text("SELECT TOP 5 word, meaning, pronunciation FROM words_rows WHERE language='chinese'")
    ).fetchall()
    
    print("\n업데이트 후 데이터:")
    print("-" * 60)
    for r in check:
        print(f"한자: {r.word} | 의미: {r.meaning} | 발음: {r.pronunciation}")
