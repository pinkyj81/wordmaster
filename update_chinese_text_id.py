from app import app, db
from sqlalchemy import text

with app.app_context():
    # 1. text_records_rows에 90-1 레코드가 있는지 확인
    check_query = text('SELECT id FROM text_records_rows WHERE id = :id')
    exists = db.session.execute(check_query, {'id': '90-1'}).fetchone()

    if not exists:
        # 레코드 생성
        insert_query = text('''
            INSERT INTO text_records_rows (id, title, content, source, word_count, created_at, updated_at)
            VALUES (:id, :title, :content, :source, 0, DATEADD(hour, 9, SYSUTCDATETIME()), DATEADD(hour, 9, SYSUTCDATETIME()))
        ''')
        db.session.execute(insert_query, {
            'id': '90-1',
            'title': '90-1 일본어 한자',
            'content': '일본어 학습용 한자 모음',
            'source': '박영진'
        })
        db.session.commit()
        print('✅ text_records_rows에 90-1 레코드 생성 완료')
    else:
        print('✅ text_records_rows에 90-1 레코드가 이미 존재합니다')

    # 2. 모든 한자의 text_id를 90-1로 업데이트
    update_query = text('''
        UPDATE words_rows
        SET text_id = :text_id, text_title = :text_title
        WHERE language = 'chinese'
    ''')
    result = db.session.execute(update_query, {
        'text_id': '90-1',
        'text_title': '90-1 일본어 한자'
    })
    db.session.commit()
    print(f'✅ {result.rowcount}개의 한자 text_id를 90-1로 업데이트 완료')
