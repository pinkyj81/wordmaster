from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import text
import uuid
from sqlalchemy import text

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = (
    'mssql+pyodbc://pinkyj81:zoskek38!!@ms1901.gabiadb.com/yujincast?driver=ODBC+Driver+18+for+SQL+Server'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ✅ WordsRow 모델
class WordsRow(db.Model):
    __tablename__ = 'words_rows'
    id = db.Column(db.String, primary_key=True)
    word = db.Column(db.String, nullable=False)
    meaning = db.Column(db.String, nullable=False)
    pronunciation = db.Column(db.String)
    sentence = db.Column(db.String)
    is_learned = db.Column(db.Boolean, nullable=False)
    text_id = db.Column(db.String, nullable=False)
    text_title = db.Column(db.String, nullable=False)
    added_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    example = db.Column(db.String)

# ✅ 테스트 결과 저장용 모델
class TestRecord(db.Model):
    __tablename__ = 'test_records_rows'
    id = db.Column(db.String, primary_key=True)
    test_name = db.Column(db.String)
    total_questions = db.Column(db.Integer)
    correct_answers = db.Column(db.Integer)
    score = db.Column(db.Numeric(5, 2))
    duration = db.Column(db.Integer)
    completed_at = db.Column(db.DateTime)
    test_words = db.Column(db.String)
    created_at = db.Column(db.DateTime)

# ✅ 홈 화면 (텍스트 목록)
@app.route('/')
def index():
    query = text("SELECT id, title, content, word_count, source FROM text_records_rows ORDER BY title ASC")
    texts = db.session.execute(query).fetchall()
    return render_template('index.html', texts=texts)


# ✅ 단어 테스트 페이지
@app.route('/test/<text_id>')
def word_test(text_id):
    words = WordsRow.query.filter_by(text_id=text_id).all()
    word_list = [
        {"word": w.word, "meaning": w.meaning, "text_title": w.text_title}
        for w in words
    ]
    return render_template('test_modal.html', words=word_list)

# ✅ 테스트 결과 저장 API
@app.route('/save_test_result', methods=['POST'])
def save_test_result():
    data = request.get_json()
    print("📩 받은 데이터:", data)

    import uuid
    record_id = str(uuid.uuid4())

    # ✅ 전체 제목 그대로 저장 (번호 포함)
    test_name = data.get('test_name', '')
    score = int(round(data.get('score', 0)))  # 정수 반올림
    total = data.get('total_questions', 0)
    correct = data.get('correct_answers', 0)
    duration = data.get('duration', 0)

    try:
        insert_query = text("""
            INSERT INTO test_records_rows 
                (id, test_name, total_questions, correct_answers, score, duration, test_words, completed_at, created_at)
            VALUES 
                (:id, :test_name, :total_questions, :correct_answers, :score, :duration, :test_words, SYSDATETIMEOFFSET(), SYSDATETIMEOFFSET())
        """)
        db.session.execute(insert_query, {
            "id": record_id,
            "test_name": test_name,  # ✅ 이제 '01-3 Incan and Mayan Civilizations' 전체 저장
            "total_questions": total,
            "correct_answers": correct,
            "score": score,  # ✅ DB에는 정수로 저장
            "duration": duration,
            "test_words": ""
        })
        db.session.commit()

        print(f"✅ 저장 완료: {test_name}, 점수={score}")
        return jsonify({"message": "저장 완료", "score": score})

    except Exception as e:
        db.session.rollback()
        print("❌ DB 저장 오류:", e)
        return jsonify({"error": str(e)}), 500

    
# ✅ 암기카드(Flashcards) 페이지
@app.route('/flashcards/<text_id>')
def flashcards(text_id):
    words = WordsRow.query.filter_by(text_id=text_id).all()
    word_list = [
        {"word": w.word, "meaning": w.meaning, "text_title": w.text_title}
        for w in words
    ]
    return render_template('flashcard_modal.html', words=word_list)


# ✅ 학습 대시보드 (학습기록 + 테스트횟수 요약)
@app.route('/learning_log')
def learning_log():
    # 테스트 기록 목록
    query = text("""
        SELECT test_name, total_questions, correct_answers, score, duration, completed_at
        FROM test_records_rows
        ORDER BY completed_at DESC
    """)
    logs = db.session.execute(query).fetchall()

    # 텍스트별 테스트 횟수 요약
    summary_query = text("""
        SELECT test_name, COUNT(*) AS test_count
        FROM test_records_rows
        GROUP BY test_name
        ORDER BY test_count DESC
    """)
    summary_rows = db.session.execute(summary_query).fetchall()

    # ✅ Row 객체를 JSON 직렬화 가능한 dict로 변환
    summary = [{"test_name": r.test_name, "test_count": r.test_count} for r in summary_rows]

    return render_template('learning_log.html', logs=logs, summary=summary)


    # 텍스트별 테스트 횟수 요약
    summary_query = text("""
        SELECT test_name, COUNT(*) AS test_count
        FROM test_records_rows
        GROUP BY test_name
        ORDER BY test_count DESC
    """)
    summary = db.session.execute(summary_query).fetchall()

    return render_template('learning_log.html', logs=logs, summary=summary)


# ✅ 서버 실행
if __name__ == '__main__':
    app.run(debug=True)

