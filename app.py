from flask import Flask, render_template, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from datetime import datetime
from gtts import gTTS
import io
import uuid
import json

app = Flask(__name__)

# ✅ SQL Server 연결 (SSL 인증서 허용)
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mssql+pyodbc://pinkyj81:zoskek38!!@ms1901.gabiadb.com/yujincast"
    "?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Convenience helper: low-level DBAPI connection context manager
from contextlib import contextmanager

@contextmanager
def get_conn():
    """Yield a raw DBAPI connection from SQLAlchemy's engine.

    Usage:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(...)
            rows = cur.fetchall()
    This mirrors the low-level connection style used in some `Quality/*` scripts.
    """
    conn = db.engine.raw_connection()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ✅ WordsRow 모델
class WordsRow(db.Model):
    __tablename__ = 'words_rows'
    id = db.Column(db.String, primary_key=True)
    word = db.Column(db.String, nullable=False)
    meaning = db.Column(db.String, nullable=False)
    pronunciation = db.Column(db.String)
    sentence = db.Column(db.String)
    is_learned = db.Column(db.Boolean, nullable=True)
    text_id = db.Column(db.String, nullable=True)
    text_title = db.Column(db.String, nullable=True)
    added_at = db.Column(db.String)
    created_at = db.Column(db.String)
    updated_at = db.Column(db.String)
    example = db.Column(db.String)


# ✅ 테스트 기록 모델
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

@app.route('/')
def index():
    query = text("""
        SELECT
    t.id,
    t.title,
    t.source,
    t.content,
    ISNULL(w.word_count, 0) AS word_count,
    ISNULL(l.learned_count, 0) AS learned_count,
    ISNULL(tc.test_count, 0) AS test_count
FROM text_records_rows t

LEFT JOIN (
    SELECT text_id, COUNT(*) AS word_count
    FROM words_rows
    GROUP BY text_id
) w ON t.id = w.text_id

LEFT JOIN (
    SELECT text_id, COUNT(*) AS learned_count
    FROM words_rows
    WHERE ISNULL(is_learned, 0) = 1
    GROUP BY text_id
) l ON t.id = l.text_id

LEFT JOIN (
    SELECT
        LEFT(test_name, CHARINDEX(' ', test_name + ' ') - 1) AS text_id,
        COUNT(*) AS test_count
    FROM test_records_rows
    GROUP BY LEFT(test_name, CHARINDEX(' ', test_name + ' ') - 1)
) tc ON t.id = tc.text_id

ORDER BY t.id ASC;

    """)
    texts = db.session.execute(query).fetchall()

    sources = db.session.execute(text("""
        SELECT DISTINCT source 
        FROM text_records_rows
        WHERE source IS NOT NULL AND source <> ''
    """)).fetchall()

    return render_template('index.html',
                           texts=texts,
                           sources=[row.source for row in sources])


@app.route('/text_records')
def text_records():
    # 기존 목록 쿼리
    records = db.session.execute(text("SELECT * FROM text_records_rows ORDER BY id")).fetchall()

    # ✅ 출처 목록 (중복 제거)
    sources = db.session.execute(text("""
        SELECT DISTINCT source FROM text_records_rows
        WHERE source IS NOT NULL AND source <> ''
    """)).fetchall()

    # ✅ sources를 템플릿으로 전달
    return render_template('text_records.html', 
                           records=records, 
                           sources=[row.source for row in sources])







# ✅ 단어 테스트 페이지
@app.route('/test/<text_id>')
def word_test(text_id):
    words = WordsRow.query.filter_by(text_id=text_id).all()
    word_list = [{"word": w.word, "meaning": w.meaning, "text_title": w.text_title} for w in words]
    return render_template('test_modal.html', words=word_list)


# ✅ 테스트 결과 저장
@app.route('/save_test_result', methods=['POST'])
def save_test_result():
    data = request.get_json()
    record_id = str(uuid.uuid4())
    test_name = data.get('test_name', '')
    score = int(round(data.get('score', 0)))
    total = data.get('total_questions', 0)
    correct = data.get('correct_answers', 0)
    duration = data.get('duration', 0)
    wrong_words = json.dumps(data.get('wrong_words', []), ensure_ascii=False)

    try:
        insert_query = text("""
            INSERT INTO test_records_rows 
                (id, test_name, total_questions, correct_answers, score, duration, test_words, completed_at, created_at)
            VALUES 
                (:id, :test_name, :total_questions, :correct_answers, :score, :duration, :test_words, SYSDATETIMEOFFSET(), SYSDATETIMEOFFSET())
        """)
        db.session.execute(insert_query, {
            "id": record_id,
            "test_name": test_name,
            "total_questions": total,
            "correct_answers": correct,
            "score": score,
            "duration": duration,
            "test_words": wrong_words
        })
        db.session.commit()
        return jsonify({"message": "저장 완료", "score": score})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ✅ 암기카드 페이지
@app.route('/flashcards/<text_id>')
def flashcards(text_id):
    words = WordsRow.query.filter_by(text_id=text_id).all()
    word_list = [{"word": w.word, "meaning": w.meaning, "text_title": w.text_title} for w in words]
    return render_template('flashcard_modal.html', words=word_list, text_id=text_id)


# ✅ API: refresh counts for a text (word_count, test_count)
@app.route('/_refresh_text_counts/<text_id>')
def refresh_text_counts(text_id):
    wc_row = db.session.execute(text("SELECT COUNT(*) AS cnt FROM words_rows WHERE text_id = :text_id"), {"text_id": text_id}).fetchone()
    word_count = wc_row.cnt if hasattr(wc_row, 'cnt') else (wc_row[0] if wc_row else 0)

    tc_row = db.session.execute(text("SELECT COUNT(*) AS cnt FROM test_records_rows WHERE LEFT(test_name, CHARINDEX(' ', test_name + ' ') - 1) = :text_id"), {"text_id": text_id}).fetchone()
    test_count = tc_row.cnt if hasattr(tc_row, 'cnt') else (tc_row[0] if tc_row else 0)

    return jsonify({"word_count": int(word_count), "test_count": int(test_count)})


# ✅ 학습 로그 페이지
@app.route('/learning_log')
def learning_log():
    q = request.args.get('q', '').strip()

    if q:
        logs_query = text("""
            SELECT id, test_name, total_questions, correct_answers, score, duration, completed_at, test_words
            FROM test_records_rows
            WHERE test_name LIKE :q
            ORDER BY completed_at DESC
        """)
        logs = db.session.execute(logs_query, {"q": f"%{q}%"}).fetchall()

        summary_query = text("""
            SELECT test_name, COUNT(*) AS test_count
            FROM test_records_rows
            WHERE test_name LIKE :q
            GROUP BY test_name
            ORDER BY test_count DESC
        """)
        summary_rows = db.session.execute(summary_query, {"q": f"%{q}%"}).fetchall()
    else:
        logs_query = text("""
            SELECT id, test_name, total_questions, correct_answers, score, duration, completed_at, test_words
            FROM test_records_rows
            ORDER BY completed_at DESC
        """)
        logs = db.session.execute(logs_query).fetchall()

        summary_query = text("""
            SELECT test_name, COUNT(*) AS test_count
            FROM test_records_rows
            GROUP BY test_name
            ORDER BY test_count DESC
        """)
        summary_rows = db.session.execute(summary_query).fetchall()

    summary = [{"test_name": r.test_name, "test_count": r.test_count} for r in summary_rows]

    # distinct test names for datalist/autocomplete
    tn_rows = db.session.execute(text("SELECT DISTINCT test_name FROM test_records_rows ORDER BY test_name")).fetchall()
    test_names = [r.test_name for r in tn_rows]

    formatted_logs = []
    for row in logs:
        try:
            wrong_list = json.loads(row.test_words) if row.test_words else []
        except:
            wrong_list = []
        formatted_logs.append({
            "id": row.id,
            "test_name": row.test_name,
            "total_questions": row.total_questions,
            "correct_answers": row.correct_answers,
            "score": float(row.score),
            "duration": row.duration,
            "completed_at": row.completed_at,
            "test_words": wrong_list
        })

    return render_template('learning_log.html', logs=formatted_logs, summary=summary, q=q, test_names=test_names)


# ✅ 발음 듣기 (미국식)
@app.route('/tts/<word>')
def tts(word):
    tts = gTTS(word, lang='en', tld='com')
    mp3_fp = io.BytesIO()
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)
    return send_file(mp3_fp, mimetype='audio/mpeg')


# ✅ 텍스트 수정 API
@app.route('/update_text', methods=['POST'])
def update_text():
    data = request.get_json()
    query = text("""
        UPDATE text_records_rows
        SET title = :title, content = :content
        WHERE id = :id
    """)
    db.session.execute(query, data)
    db.session.commit()
    return jsonify({"message": "텍스트 수정 완료"})


# ✅ 단어 목록 가져오기
@app.route('/get_words/<text_id>')
def get_words(text_id):
    words = WordsRow.query.filter_by(text_id=text_id).all()
    return jsonify([{"id": w.id, "word": w.word, "meaning": w.meaning} for w in words])


# ✅ 단어 수정 API
@app.route('/update_words', methods=['POST'])
def update_words():
    data = request.get_json()
    for w in data.get('words', []):
        update_query = text("""
            UPDATE words_rows
            SET word = :word, meaning = :meaning
            WHERE id = :id
        """)
        db.session.execute(update_query, {"id": w["id"], "word": w["word"], "meaning": w["meaning"]})
    db.session.commit()
    return jsonify({"message": "단어 수정 완료"})


# ✅ 텍스트 업로드
@app.route('/upload_text', methods=['POST'])
def upload_text():
    data = request.get_json()
    title = data.get('title', '')
    source = data.get('source', '')
    content = data.get('content', '')
    record_id = title.split(' ')[0][:4]

    query = text("""
        INSERT INTO text_records_rows (id, title, content, source, word_count, created_at, updated_at)
        VALUES (:id, :title, :content, :source, 0, SYSDATETIMEOFFSET(), SYSDATETIMEOFFSET())
    """)
    db.session.execute(query, {"id": record_id, "title": title, "content": content, "source": source})
    db.session.commit()
    return jsonify({"message": "텍스트 업로드 완료"})



# ✅ 단어 업로드 (날짜 필드 → 문자열 저장으로 수정)
@app.route('/upload_words', methods=['POST'])
def upload_words():
    try:
        data = request.get_json()
        text_id = data.get('text_id')
        words = data.get('words', [])

        if not text_id or not words:
            return jsonify({"error": "필수 데이터 누락"}), 400

        # 텍스트 제목
        title_query = text("SELECT title FROM text_records_rows WHERE id = :id")
        result = db.session.execute(title_query, {"id": text_id}).fetchone()
        text_title = result.title if result else "(제목 없음)"

        # ✅ 현재 가장 큰 id 값 가져오기
        last_id_query = text("SELECT MAX(CAST(id AS INT)) AS max_id FROM words_rows")
        result = db.session.execute(last_id_query).fetchone()
        current_max_id = result.max_id or 0  # 없으면 0부터 시작

        now = datetime.now().isoformat(timespec='seconds')

        for w in words:
            current_max_id += 1  # +1 증가
            insert_query = text("""
                INSERT INTO words_rows
                    (id, word, meaning, is_learned, text_id, text_title,
                     added_at, created_at, updated_at)
                VALUES
                    (:id, :word, :meaning, 0, :text_id, :text_title,
                     :now, :now, :now)
            """)
            db.session.execute(insert_query, {
                "id": str(current_max_id),
                "word": w["word"],
                "meaning": w["meaning"],
                "text_id": text_id,
                "text_title": text_title,
                "now": now
            })

        db.session.commit()
        return jsonify({"message": "단어 업로드 완료"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ✅ 텍스트 제목 리스트 반환
@app.route('/get_text_titles')
def get_text_titles():
    query = text("SELECT id, title FROM text_records_rows ORDER BY title ASC")
    result = db.session.execute(query).fetchall()
    return jsonify([{"id": r.id, "title": r.title} for r in result])


# ✅ 특정 텍스트의 단어 목록 반환
@app.route('/get_words_by_text/<text_id>')
def get_words_by_text(text_id):
    query = text("""
        SELECT id, word, meaning , ISNULL(is_learned, 0) AS is_learned
        FROM words_rows
        WHERE text_id = :text_id
        ORDER BY word ASC
    """)
    result = db.session.execute(query, {"text_id": text_id}).fetchall()
    return jsonify([{"id": r.id, "word": r.word, "meaning": r.meaning ,"is_learned": int(r.is_learned or 0)} for r in result])



# ✅ 단어 수정
@app.route('/update_word', methods=['POST'])
def update_word():
    data = request.get_json()
    word_id = data.get('id')
    word = data.get('word')
    meaning = data.get('meaning')

    query = text("""
        UPDATE words_rows
        SET word = :word,
            meaning = :meaning,
            updated_at = SYSDATETIMEOFFSET()
        WHERE id = :id
    """)
    db.session.execute(query, {"id": word_id, "word": word, "meaning": meaning})
    db.session.commit()
    return jsonify({"message": "단어가 수정되었습니다."})
# ✅ 단어 삭제
@app.route('/delete_word/<word_id>', methods=['DELETE'])
def delete_word(word_id):
    query = text("DELETE FROM words_rows WHERE id = :id")
    db.session.execute(query, {"id": word_id})
    db.session.commit()
    return jsonify({"message": "단어가 삭제되었습니다."})

@app.route('/get_sources')
def get_sources():
    query = text("""
        SELECT DISTINCT source
        FROM text_records_rows
        WHERE source IS NOT NULL AND source <> ''
        ORDER BY source
    """)
    result = db.session.execute(query).fetchall()
    return jsonify([{"source": r[0]} for r in result])


@app.route("/api/word/learned", methods=["POST"])
def api_word_learned():
    try:
        data = request.get_json(force=True)
        word_id = int(data["word_id"])
        is_learned = 1 if data["is_learned"] else 0

        db.session.execute(text("""
            UPDATE words_rows
            SET is_learned = :is_learned,
                updated_at = SYSDATETIMEOFFSET()
            WHERE id = :word_id
        """), {"is_learned": is_learned, "word_id": word_id})

        db.session.commit()
        return jsonify({"ok": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/get_titles_by_source/<source>')
def get_titles_by_source(source):
    query = text("""
        SELECT id, title
        FROM text_records_rows
        WHERE source = :source
        ORDER BY title ASC
    """)
    result = db.session.execute(query, {"source": source}).fetchall()
    return jsonify([{"id": r[0], "title": r[1]} for r in result])


# ✅ API: get unlearned words across multiple texts
from sqlalchemy import or_

@app.route('/api/unlearned_words', methods=['POST'])
def api_unlearned_words():
    data = request.get_json(force=True)
    text_ids = data.get('text_ids', [])
    if not text_ids:
        return jsonify({"error": "텍스트를 하나 이상 선택하세요."}), 400

    # Use ORM filter to find words where is_learned is False or NULL
    rows = WordsRow.query.filter(WordsRow.text_id.in_(text_ids)).filter(
        or_(WordsRow.is_learned == False, WordsRow.is_learned.is_(None))
    ).all()

    return jsonify([
        {"id": w.id, "word": w.word, "meaning": w.meaning, "text_title": w.text_title}
        for w in rows
    ])


# ✅ API: add a single word from text view (idempotent)
@app.route('/api/add_word', methods=['POST'])
def api_add_word():
    data = request.get_json(force=True)
    text_id = data.get('text_id')
    word = (data.get('word') or '').strip()
    meaning = (data.get('meaning') or '').strip()
    if not text_id or not word:
        return jsonify({"error": "text_id and word are required"}), 400

    # check if already exists
    exists = db.session.execute(text("SELECT id FROM words_rows WHERE text_id = :text_id AND word = :word"), {"text_id": text_id, "word": word}).fetchone()
    if exists:
        return jsonify({"ok": True, "created": False, "id": exists.id})

    # get text title
    r = db.session.execute(text("SELECT title FROM text_records_rows WHERE id = :id"), {"id": text_id}).fetchone()
    text_title = r.title if r else "(제목 없음)"

    # new id
    last = db.session.execute(text("SELECT MAX(CAST(id AS INT)) AS max_id FROM words_rows")).fetchone()
    new_id = str((last.max_id or 0) + 1)
    now = datetime.now().isoformat(timespec='seconds')

    insert_q = text("""
        INSERT INTO words_rows
            (id, word, meaning, is_learned, text_id, text_title, added_at, created_at, updated_at)
        VALUES
            (:id, :word, :meaning, 0, :text_id, :text_title, :now, :now, :now)
    """)

    db.session.execute(insert_q, {"id": new_id, "word": word, "meaning": meaning, "text_id": text_id, "text_title": text_title, "now": now})
    db.session.commit()

    return jsonify({"ok": True, "created": True, "id": new_id, "word": word})


# ✅ API: remove a single word (by text_id + word)
@app.route('/api/remove_word', methods=['POST'])
def api_remove_word():
    data = request.get_json(force=True)
    text_id = data.get('text_id')
    word = (data.get('word') or '').strip()
    if not text_id or not word:
        return jsonify({"error": "text_id and word are required"}), 400

    # count existing
    cnt_row = db.session.execute(text("SELECT COUNT(*) AS cnt FROM words_rows WHERE text_id = :text_id AND word = :word"), {"text_id": text_id, "word": word}).fetchone()
    cnt = cnt_row.cnt if hasattr(cnt_row, 'cnt') else (cnt_row[0] if cnt_row else 0)
    if cnt == 0:
        return jsonify({"ok": True, "deleted": False, "deleted_count": 0})

    db.session.execute(text("DELETE FROM words_rows WHERE text_id = :text_id AND word = :word"), {"text_id": text_id, "word": word})
    db.session.commit()
    return jsonify({"ok": True, "deleted": True, "deleted_count": cnt})

# ✅ 서버 실행
if __name__ == '__main__':
    app.run(debug=True)
