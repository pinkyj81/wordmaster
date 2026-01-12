from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from datetime import datetime
from gtts import gTTS
from functools import wraps
import io
import uuid
import json
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 세션 암호화 키

# ✅ SQL Server 연결 (SSL 인증서 허용)
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mssql+pyodbc://pinkyj81:zoskek38!!@ms1901.gabiadb.com/yujincast"
    "?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ✅ 사용자 목록 (간단한 구현)
USERS = [
    {"id": "user1", "name": "박영진", "user_id": "박영진", "is_admin": True},
    {"id": "user2", "name": "권혁재", "user_id": "권혁재", "is_admin": False},
    {"id": "user3", "name": "권유현", "user_id": "권유현", "is_admin": False},
    {"id": "user4", "name": "GUEST", "user_id": "GUEST", "is_admin": False},
    {"id": "user5", "name": "사용자5", "user_id": "사용자5", "is_admin": False},
    {"id": "user6", "name": "사용자6", "user_id": "사용자6", "is_admin": False},
]

# ✅ 로그인 체크 데코레이터
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ✅ 현재 로그인한 사용자의 출처 목록 가져오기
def get_user_sources():
    """현재 로그인한 사용자가 등록한 출처 목록 반환"""
    if 'user_name' not in session:
        return []
    user_name = session['user_name']
    sources = WordUser.query.filter_by(user_name=user_name).all()
    return [s.source for s in sources]

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
    is_learned = db.Column(db.Boolean, nullable=True)
    text_id = db.Column(db.String, nullable=True)
    text_title = db.Column(db.String, nullable=True)
    added_at = db.Column(db.String)
    created_at = db.Column(db.String)
    updated_at = db.Column(db.String)
    example = db.Column(db.String)
    exam_korean = db.Column(db.String)

# ✅ 시험 문제 모델
class ExamQuestion(db.Model):
    __tablename__ = 'exam_questions'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category = db.Column(db.String(50), nullable=True)
    number = db.Column(db.Integer, nullable=True)
    question = db.Column(db.String(500), nullable=False)
    choice_a = db.Column(db.String(200), nullable=True)
    choice_b = db.Column(db.String(200), nullable=True)
    choice_c = db.Column(db.String(200), nullable=True)
    choice_d = db.Column(db.String(200), nullable=True)
    answer = db.Column(db.String(1), nullable=False)
    created_at = db.Column(db.DateTime, nullable=True)

# ✅ 학습 문제 모델 (빈칸 채우기)
class ExamAnswer(db.Model):
    __tablename__ = 'exam_answer'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category = db.Column(db.String(10), nullable=True)
    number = db.Column(db.Integer, nullable=True)
    question = db.Column(db.String, nullable=True)
    correct_word = db.Column(db.String(200), nullable=True)
    meaning = db.Column(db.String(500), nullable=True)

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
    user_id = db.Column(db.String(50))

# ✅ 사용자-소스 매핑 모델
class WordUser(db.Model):
    __tablename__ = 'word_users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_name = db.Column(db.String(50), nullable=False)
    source = db.Column(db.String(50), nullable=False)

# ✅ 로그인 페이지
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        selected_name = request.form.get('user_id')
        
        # word_users에서 해당 사용자가 있는지 확인
        user_exists = db.session.execute(
            text("SELECT COUNT(*) as cnt FROM word_users WHERE user_name = :name"),
            {"name": selected_name}
        ).fetchone()
        
        if user_exists and user_exists.cnt > 0:
            # USERS 리스트에서 관리자 정보 확인 (없으면 일반 사용자)
            static_user = next((u for u in USERS if u['name'] == selected_name), None)
            is_admin = static_user.get('is_admin', False) if static_user else False
            
            session['user_id'] = f"user_{selected_name}"
            session['user_name'] = selected_name
            session['db_user_id'] = selected_name  # DB에 저장될 user_id (문자열)
            session['is_admin'] = is_admin
            return redirect(url_for('index'))
        else:
            # word_users에 등록된 사용자 목록 조회
            registered_users_query = text("SELECT DISTINCT user_name FROM word_users ORDER BY user_name")
            registered_names = [r.user_name for r in db.session.execute(registered_users_query).fetchall()]
            return render_template('login.html', users=registered_names, error='사용자를 선택하세요.')
    
    # word_users에 등록된 사용자 목록 조회
    registered_users_query = text("SELECT DISTINCT user_name FROM word_users ORDER BY user_name")
    registered_names = [r.user_name for r in db.session.execute(registered_users_query).fetchall()]
    
    return render_template('login.html', users=registered_names)

# ✅ 로그아웃
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    # 사용자가 등록한 출처 목록
    user_sources = get_user_sources()
    
    if not user_sources:
        # 등록된 출처가 없으면 빈 목록 반환
        return render_template('index.html', texts=[], sources=[])
    
    # 현재 로그인한 사용자 ID
    current_user_id = session.get('db_user_id', session.get('user_name', 'Unknown'))
    
    # IN 절을 위한 파라미터 생성
    source_params = {f'src{i}': src for i, src in enumerate(user_sources)}
    source_placeholders = ', '.join([f':src{i}' for i in range(len(user_sources))])
    source_params['current_user_id'] = current_user_id
    
    query = text(f"""
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
    WHERE user_id = :current_user_id
    GROUP BY LEFT(test_name, CHARINDEX(' ', test_name + ' ') - 1)
) tc ON t.id = tc.text_id

WHERE t.source IN ({source_placeholders})

ORDER BY t.id ASC;
    """)
    texts = db.session.execute(query, source_params).fetchall()

    return render_template('index.html',
                           texts=texts,
                           sources=user_sources)


@app.route('/text_records')
@login_required
def text_records():
    # 사용자가 등록한 출처 목록
    user_sources = get_user_sources()
    
    if not user_sources:
        return render_template('text_records.html', records=[], sources=[])
    
    # IN 절을 위한 파라미터 생성
    source_params = {f'src{i}': src for i, src in enumerate(user_sources)}
    source_placeholders = ', '.join([f':src{i}' for i in range(len(user_sources))])
    
    # 사용자 출처에 해당하는 텍스트만 조회
    query = text(f"SELECT * FROM text_records_rows WHERE source IN ({source_placeholders}) ORDER BY id")
    records = db.session.execute(query, source_params).fetchall()

    return render_template('text_records.html', 
                           records=records, 
                           sources=user_sources)







# ✅ 단어 테스트 페이지
@app.route('/test/<text_id>')
def word_test(text_id):
    words = WordsRow.query.filter_by(text_id=text_id).all()
    word_list = [{"word": w.word, "meaning": w.meaning, "text_title": w.text_title} for w in words]
    return render_template('test_modal.html', words=word_list)


# ✅ 테스트 결과 저장
@app.route('/save_test_result', methods=['POST'])
@login_required
def save_test_result():
    data = request.get_json()
    record_id = str(uuid.uuid4())
    test_name = data.get('test_name', '')
    score = int(round(data.get('score', 0)))
    total = data.get('total_questions', 0)
    correct = data.get('correct_answers', 0)
    duration = data.get('duration', 0)
    wrong_words = json.dumps(data.get('wrong_words', []), ensure_ascii=False)
    user_id = session.get('db_user_id', session.get('user_name', 'Unknown'))

    try:
        insert_query = text("""
            INSERT INTO test_records_rows 
                (id, test_name, total_questions, correct_answers, score, duration, test_words, completed_at, created_at, user_id)
            VALUES 
                (:id, :test_name, :total_questions, :correct_answers, :score, :duration, :test_words, SYSDATETIMEOFFSET(), SYSDATETIMEOFFSET(), :user_id)
        """)
        db.session.execute(insert_query, {
            "id": record_id,
            "test_name": test_name,
            "total_questions": total,
            "correct_answers": correct,
            "score": score,
            "duration": duration,
            "test_words": wrong_words,
            "user_id": user_id
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
@login_required
def refresh_text_counts(text_id):
    wc_row = db.session.execute(text("SELECT COUNT(*) AS cnt FROM words_rows WHERE text_id = :text_id"), {"text_id": text_id}).fetchone()
    word_count = wc_row.cnt if hasattr(wc_row, 'cnt') else (wc_row[0] if wc_row else 0)

    # 현재 로그인한 사용자의 테스트 기록만 카운트
    current_user_id = session.get('db_user_id', session.get('user_name', 'Unknown'))
    tc_row = db.session.execute(
        text("SELECT COUNT(*) AS cnt FROM test_records_rows WHERE LEFT(test_name, CHARINDEX(' ', test_name + ' ') - 1) = :text_id AND user_id = :user_id"),
        {"text_id": text_id, "user_id": current_user_id}
    ).fetchone()
    test_count = tc_row.cnt if hasattr(tc_row, 'cnt') else (tc_row[0] if tc_row else 0)

    return jsonify({"word_count": int(word_count), "test_count": int(test_count)})


# ✅ 학습 로그 페이지
# ✅ 단어 관리 전체 화면 페이지
@app.route('/word_management')
@login_required
def word_management():
    user_sources = get_user_sources()
    return render_template('word_management.html', sources=user_sources)

@app.route('/learning_log')
@login_required
def learning_log():
    q = request.args.get('q', '').strip()
    view_all = request.args.get('view_all', '0') == '1'
    user_id = session.get('db_user_id')
    is_admin = session.get('is_admin', False)
    
    # 디버깅: user_id가 None인 경우 체크
    if user_id is None:
        print(f"WARNING: db_user_id is None in session. Session data: {dict(session)}")
        user_id = session.get('user_name', 'Unknown')  # 기본값
    
    # user_id를 user_name으로 매핑 (user_id가 이미 이름이므로 그대로 사용)
    user_map = {u['user_id']: u['name'] for u in USERS}
    
    # 관리자가 전체 보기를 선택한 경우
    show_all = is_admin and view_all
    
    print(f"DEBUG: user_id={user_id}, is_admin={is_admin}, view_all={view_all}, show_all={show_all}")

    if q:
        if show_all:
            logs_query = text("""
                SELECT id, test_name, total_questions, correct_answers, score, duration, completed_at, test_words, user_id
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
                SELECT id, test_name, total_questions, correct_answers, score, duration, completed_at, test_words, user_id
                FROM test_records_rows
                WHERE test_name LIKE :q AND user_id = :user_id
                ORDER BY completed_at DESC
            """)
            logs = db.session.execute(logs_query, {"q": f"%{q}%", "user_id": user_id}).fetchall()

            summary_query = text("""
                SELECT test_name, COUNT(*) AS test_count
                FROM test_records_rows
                WHERE test_name LIKE :q AND user_id = :user_id
                GROUP BY test_name
                ORDER BY test_count DESC
            """)
            summary_rows = db.session.execute(summary_query, {"q": f"%{q}%", "user_id": user_id}).fetchall()
    else:
        if show_all:
            logs_query = text("""
                SELECT id, test_name, total_questions, correct_answers, score, duration, completed_at, test_words, user_id
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
        else:
            logs_query = text("""
                SELECT id, test_name, total_questions, correct_answers, score, duration, completed_at, test_words, user_id
                FROM test_records_rows
                WHERE user_id = :user_id
                ORDER BY completed_at DESC
            """)
            logs = db.session.execute(logs_query, {"user_id": user_id}).fetchall()

            summary_query = text("""
                SELECT test_name, COUNT(*) AS test_count
                FROM test_records_rows
                WHERE user_id = :user_id
                GROUP BY test_name
                ORDER BY test_count DESC
            """)
            summary_rows = db.session.execute(summary_query, {"user_id": user_id}).fetchall()

    summary = [{"test_name": r.test_name, "test_count": r.test_count} for r in summary_rows]

    # distinct test names for datalist/autocomplete
    if show_all:
        tn_rows = db.session.execute(text("SELECT DISTINCT test_name FROM test_records_rows ORDER BY test_name")).fetchall()
    else:
        tn_rows = db.session.execute(text("SELECT DISTINCT test_name FROM test_records_rows WHERE user_id = :user_id ORDER BY test_name"), {"user_id": user_id}).fetchall()
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
            "test_words": wrong_list,
            "user_name": user_map.get(row.user_id, f'User {row.user_id}')
        })

    return render_template('learning_log.html', logs=formatted_logs, summary=summary, q=q, test_names=test_names, is_admin=is_admin, view_all=view_all)


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
    return jsonify([{
        "id": w.id, 
        "word": w.word, 
        "meaning": w.meaning,
        "example": w.example or ""
    } for w in words])


# ✅ 단어 수정 API (일괄 수정 지원)
@app.route('/update_words', methods=['POST'])
def update_words():
    try:
        data = request.get_json()
        words = data.get('words', [])
        
        if not words:
            return jsonify({"error": "수정할 단어가 없습니다."}), 400
        
        for w in words:
            update_query = text("""
                UPDATE words_rows
                SET word = :word, 
                    meaning = :meaning,
                    example = :example,
                    exam_korean = :exam_korean,
                    is_learned = :is_learned,
                    updated_at = SYSDATETIMEOFFSET()
                WHERE id = :id
            """)
            db.session.execute(update_query, {
                "id": w["id"], 
                "word": w["word"], 
                "meaning": w["meaning"],
                "example": w.get("example", ""),
                "exam_korean": w.get("exam_korean", ""),
                "is_learned": w.get("is_learned", 0)
            })
        
        db.session.commit()
        return jsonify({"message": f"{len(words)}개 단어 수정 완료"})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


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
                     added_at, created_at, updated_at, example, exam_korean)
                VALUES
                    (:id, :word, :meaning, :is_learned, :text_id, :text_title,
                     :now, :now, :now, :example, :exam_korean)
            """)
            db.session.execute(insert_query, {
                "id": str(current_max_id),
                "word": w["word"],
                "meaning": w["meaning"],
                "is_learned": w.get("is_learned", 0),
                "text_id": text_id,
                "text_title": text_title,
                "now": now,
                "example": w.get("example", ""),
                "exam_korean": w.get("exam_korean", "")
            })

        db.session.commit()
        return jsonify({"message": "단어 업로드 완료"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ✅ 텍스트 제목 리스트 반환 (사용자 출처만)
@app.route('/get_text_titles')
@login_required
def get_text_titles():
    user_sources = get_user_sources()
    
    if not user_sources:
        return jsonify([])
    
    source_params = {f'src{i}': src for i, src in enumerate(user_sources)}
    source_placeholders = ', '.join([f':src{i}' for i in range(len(user_sources))])
    
    query = text(f"SELECT id, title FROM text_records_rows WHERE source IN ({source_placeholders}) ORDER BY title ASC")
    result = db.session.execute(query, source_params).fetchall()
    return jsonify([{"id": r.id, "title": r.title} for r in result])


# ✅ 특정 텍스트의 단어 목록 반환
@app.route('/get_words_by_text/<text_id>')
def get_words_by_text(text_id):
    query = text("""
        SELECT id, word, meaning, ISNULL(is_learned, 0) AS is_learned, example, exam_korean
        FROM words_rows
        WHERE text_id = :text_id
        ORDER BY word ASC
    """)
    result = db.session.execute(query, {"text_id": text_id}).fetchall()
    return jsonify([{
        "id": r.id, 
        "word": r.word, 
        "meaning": r.meaning,
        "is_learned": int(r.is_learned or 0),
        "example": r.example or "",
        "exam_korean": r.exam_korean or ""
    } for r in result])



# ✅ 단어 수정
@app.route('/update_word', methods=['POST'])
def update_word():
    data = request.get_json()
    word_id = data.get('id')
    word = data.get('word')
    meaning = data.get('meaning')
    example = data.get('example', '')

    query = text("""
        UPDATE words_rows
        SET word = :word,
            meaning = :meaning,
            example = :example,
            updated_at = SYSDATETIMEOFFSET()
        WHERE id = :id
    """)
    db.session.execute(query, {"id": word_id, "word": word, "meaning": meaning, "example": example})
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
@login_required
def get_sources():
    """현재 로그인한 사용자가 등록한 출처 목록만 반환"""
    user_sources = get_user_sources()
    return jsonify([{"source": src} for src in sorted(user_sources)])


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
    example = (data.get('example') or '').strip()
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
            (id, word, meaning, is_learned, text_id, text_title, added_at, created_at, updated_at, example)
        VALUES
            (:id, :word, :meaning, 0, :text_id, :text_title, :now, :now, :now, :example)
    """)

    db.session.execute(insert_q, {"id": new_id, "word": word, "meaning": meaning, "text_id": text_id, "text_title": text_title, "now": now, "example": example})
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

# ✅ 문제 풀기 페이지
@app.route('/exam_questions')
@login_required
def exam_questions():
    """문제 풀기 메인 페이지"""
    # 카테고리 목록 가져오기
    categories = db.session.execute(text("""
        SELECT DISTINCT category 
        FROM exam_questions 
        WHERE category IS NOT NULL
        ORDER BY category
    """)).fetchall()
    
    category_list = [c.category for c in categories]
    return render_template('exam_questions.html', categories=category_list)

# ✅ 학습 문제 페이지 (빈칸 채우기)
@app.route('/study_questions')
@login_required
def study_questions():
    """학습 문제 메인 페이지 (빈칸 채우기)"""
    # 카테고리 목록 가져오기
    categories = db.session.execute(text("""
        SELECT DISTINCT category 
        FROM exam_answer 
        WHERE category IS NOT NULL
        ORDER BY category
    """)).fetchall()
    
    category_list = [c.category for c in categories]
    return render_template('study_questions.html', categories=category_list)

@app.route('/api/exam_questions', methods=['GET'])
@login_required
def api_get_exam_questions():
    """카테고리별 문제 가져오기"""
    category = request.args.get('category', '')
    
    if category:
        query = text("""
            SELECT id, category, number, question, choice_a, choice_b, choice_c, choice_d, answer
            FROM exam_questions
            WHERE category = :category
            ORDER BY number
        """)
        result = db.session.execute(query, {"category": category}).fetchall()
    else:
        query = text("""
            SELECT id, category, number, question, choice_a, choice_b, choice_c, choice_d, answer
            FROM exam_questions
            ORDER BY category, number
        """)
        result = db.session.execute(query).fetchall()
    
    questions = [{
        "id": r.id,
        "category": r.category,
        "number": r.number,
        "question": r.question,
        "choice_a": r.choice_a,
        "choice_b": r.choice_b,
        "choice_c": r.choice_c,
        "choice_d": r.choice_d,
        "answer": r.answer
    } for r in result]
    
    return jsonify(questions)

@app.route('/api/exam_result', methods=['POST'])
@login_required
def api_save_exam_result():
    """시험 결과 저장"""
    try:
        data = request.get_json()
        category = data.get('category', '')
        total = data.get('total_questions', 0)
        correct = data.get('correct_answers', 0)
        score = round((correct / total * 100) if total > 0 else 0, 2)
        
        # 결과 로그 (선택사항 - 나중에 exam_results 테이블 만들면 저장)
        return jsonify({
            "ok": True,
            "score": score,
            "message": f"{correct}/{total} 정답 ({score}점)"
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500

@app.route('/api/exam_questions', methods=['POST'])
@login_required
def api_add_exam_question():
    """문제 추가"""
    try:
        data = request.get_json()
        category = data.get('category', '').strip()
        number = data.get('number')
        question = data.get('question', '').strip()
        choice_a = data.get('choice_a', '').strip()
        choice_b = data.get('choice_b', '').strip()
        choice_c = data.get('choice_c', '').strip()
        choice_d = data.get('choice_d', '').strip()
        answer = data.get('answer', '').strip().upper()
        
        if not question or not answer:
            return jsonify({"error": "문제와 정답은 필수입니다."}), 400
        
        insert_query = text("""
            INSERT INTO exam_questions 
                (category, number, question, choice_a, choice_b, choice_c, choice_d, answer, created_at)
            VALUES 
                (:category, :number, :question, :choice_a, :choice_b, :choice_c, :choice_d, :answer, SYSDATETIMEOFFSET())
        """)
        db.session.execute(insert_query, {
            "category": category or None,
            "number": number,
            "question": question,
            "choice_a": choice_a or None,
            "choice_b": choice_b or None,
            "choice_c": choice_c or None,
            "choice_d": choice_d or None,
            "answer": answer
        })
        db.session.commit()
        
        return jsonify({"ok": True, "message": "문제가 추가되었습니다."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/exam_questions/bulk', methods=['POST'])
@login_required
def api_bulk_add_exam_questions():
    """문제 일괄 추가"""
    try:
        data = request.get_json()
        questions = data.get('questions', [])
        
        if not questions:
            return jsonify({"error": "문제 데이터가 없습니다."}), 400
        
        insert_query = text("""
            INSERT INTO exam_questions 
                (category, number, question, choice_a, choice_b, choice_c, choice_d, answer, created_at)
            VALUES 
                (:category, :number, :question, :choice_a, :choice_b, :choice_c, :choice_d, :answer, SYSDATETIMEOFFSET())
        """)
        
        success_count = 0
        for q in questions:
            try:
                category = q.get('category', '').strip()
                number_str = str(q.get('number', '')).strip()
                number = int(number_str) if number_str and number_str.isdigit() else None
                question = q.get('question', '').strip()
                choice_a = q.get('choice_a', '').strip()
                choice_b = q.get('choice_b', '').strip()
                choice_c = q.get('choice_c', '').strip()
                choice_d = q.get('choice_d', '').strip()
                answer = q.get('answer', '').strip().upper()
                
                if not question or not answer:
                    continue
                
                db.session.execute(insert_query, {
                    "category": category or None,
                    "number": number,
                    "question": question,
                    "choice_a": choice_a or None,
                    "choice_b": choice_b or None,
                    "choice_c": choice_c or None,
                    "choice_d": choice_d or None,
                    "answer": answer
                })
                success_count += 1
            except Exception as e:
                print(f"문제 추가 실패: {e}")
                continue
        
        db.session.commit()
        
        return jsonify({"ok": True, "count": success_count, "message": f"{success_count}개의 문제가 추가되었습니다."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/exam_questions/<int:question_id>', methods=['GET'])
@login_required
def api_get_exam_question(question_id):
    """특정 문제 조회"""
    try:
        query = text("""
            SELECT id, category, number, question, choice_a, choice_b, choice_c, choice_d, answer
            FROM exam_questions
            WHERE id = :id
        """)
        result = db.session.execute(query, {"id": question_id}).fetchone()
        
        if not result:
            return jsonify({"error": "문제를 찾을 수 없습니다."}), 404
        
        return jsonify({
            "id": result.id,
            "category": result.category,
            "number": result.number,
            "question": result.question,
            "choice_a": result.choice_a,
            "choice_b": result.choice_b,
            "choice_c": result.choice_c,
            "choice_d": result.choice_d,
            "answer": result.answer
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/exam_questions/<int:question_id>', methods=['PUT'])
@login_required
def api_update_exam_question(question_id):
    """문제 수정"""
    try:
        data = request.get_json()
        category = data.get('category', '').strip()
        number = data.get('number')
        question = data.get('question', '').strip()
        choice_a = data.get('choice_a', '').strip()
        choice_b = data.get('choice_b', '').strip()
        choice_c = data.get('choice_c', '').strip()
        choice_d = data.get('choice_d', '').strip()
        answer = data.get('answer', '').strip().upper()
        
        if not question or not answer:
            return jsonify({"error": "문제와 정답은 필수입니다."}), 400
        
        update_query = text("""
            UPDATE exam_questions
            SET category = :category,
                number = :number,
                question = :question,
                choice_a = :choice_a,
                choice_b = :choice_b,
                choice_c = :choice_c,
                choice_d = :choice_d,
                answer = :answer
            WHERE id = :id
        """)
        db.session.execute(update_query, {
            "id": question_id,
            "category": category or None,
            "number": number,
            "question": question,
            "choice_a": choice_a or None,
            "choice_b": choice_b or None,
            "choice_c": choice_c or None,
            "choice_d": choice_d or None,
            "answer": answer
        })
        db.session.commit()
        
        return jsonify({"ok": True, "message": "문제가 수정되었습니다."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/exam_questions/<int:question_id>', methods=['DELETE'])
@login_required
def api_delete_exam_question(question_id):
    """문제 삭제"""
    try:
        delete_query = text("DELETE FROM exam_questions WHERE id = :id")
        db.session.execute(delete_query, {"id": question_id})
        db.session.commit()
        
        return jsonify({"ok": True, "message": "문제가 삭제되었습니다."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500

# ============================================
# 학습 문제 (빈칸 채우기) API
# ============================================

@app.route('/api/study_questions', methods=['GET'])
@login_required
def api_get_study_questions():
    """카테고리별 학습 문제 가져오기"""
    category = request.args.get('category', '')
    
    if category:
        query = text("""
            SELECT id, category, number, question, correct_word, meaning
            FROM exam_answer
            WHERE category = :category
            ORDER BY number
        """)
        result = db.session.execute(query, {"category": category}).fetchall()
    else:
        query = text("""
            SELECT id, category, number, question, correct_word, meaning
            FROM exam_answer
            ORDER BY category, number
        """)
        result = db.session.execute(query).fetchall()
    
    questions = [{
        "id": r.id,
        "category": r.category,
        "number": r.number,
        "question": r.question,
        "correct_word": r.correct_word,
        "meaning": r.meaning
    } for r in result]
    
    return jsonify(questions)

@app.route('/api/study_questions', methods=['POST'])
@login_required
def api_add_study_question():
    """학습 문제 추가"""
    try:
        data = request.get_json()
        category = data.get('category', '').strip()
        number = data.get('number')
        question = data.get('question', '').strip()
        correct_word = data.get('correct_word', '').strip()
        meaning = data.get('meaning', '').strip()
        
        if not question or not correct_word:
            return jsonify({"error": "문제와 정답은 필수입니다."}), 400
        
        insert_query = text("""
            INSERT INTO exam_answer 
                (category, number, question, correct_word, meaning)
            VALUES 
                (:category, :number, :question, :correct_word, :meaning)
        """)
        db.session.execute(insert_query, {
            "category": category or None,
            "number": number,
            "question": question,
            "correct_word": correct_word,
            "meaning": meaning or None
        })
        db.session.commit()
        
        return jsonify({"ok": True, "message": "문제가 추가되었습니다."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/study_questions/bulk', methods=['POST'])
@login_required
def api_bulk_add_study_questions():
    """학습 문제 일괄 추가"""
    try:
        data = request.get_json()
        questions = data.get('questions', [])
        
        if not questions:
            return jsonify({"error": "문제 데이터가 없습니다."}), 400
        
        insert_query = text("""
            INSERT INTO exam_answer 
                (category, number, question, correct_word, meaning)
            VALUES 
                (:category, :number, :question, :correct_word, :meaning)
        """)
        
        success_count = 0
        for q in questions:
            try:
                category = q.get('category', '').strip()
                number_str = str(q.get('number', '')).strip()
                number = int(number_str) if number_str and number_str.isdigit() else None
                question = q.get('question', '').strip()
                correct_word = q.get('correct_word', '').strip()
                meaning = q.get('meaning', '').strip()
                
                if not question or not correct_word:
                    continue
                
                db.session.execute(insert_query, {
                    "category": category or None,
                    "number": number,
                    "question": question,
                    "correct_word": correct_word,
                    "meaning": meaning or None
                })
                success_count += 1
            except Exception as e:
                print(f"문제 추가 실패: {e}")
                continue
        
        db.session.commit()
        
        return jsonify({"ok": True, "count": success_count, "message": f"{success_count}개의 문제가 추가되었습니다."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/study_questions/<int:question_id>', methods=['GET'])
@login_required
def api_get_study_question(question_id):
    """특정 학습 문제 조회"""
    try:
        query = text("""
            SELECT id, category, number, question, correct_word, meaning
            FROM exam_answer
            WHERE id = :id
        """)
        result = db.session.execute(query, {"id": question_id}).fetchone()
        
        if not result:
            return jsonify({"error": "문제를 찾을 수 없습니다."}), 404
        
        return jsonify({
            "id": result.id,
            "category": result.category,
            "number": result.number,
            "question": result.question,
            "correct_word": result.correct_word,
            "meaning": result.meaning
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/study_questions/<int:question_id>', methods=['PUT'])
@login_required
def api_update_study_question(question_id):
    """학습 문제 수정"""
    try:
        data = request.get_json()
        category = data.get('category', '').strip()
        number = data.get('number')
        question = data.get('question', '').strip()
        correct_word = data.get('correct_word', '').strip()
        meaning = data.get('meaning', '').strip()
        
        if not question or not correct_word:
            return jsonify({"error": "문제와 정답은 필수입니다."}), 400
        
        update_query = text("""
            UPDATE exam_answer
            SET category = :category,
                number = :number,
                question = :question,
                correct_word = :correct_word,
                meaning = :meaning
            WHERE id = :id
        """)
        db.session.execute(update_query, {
            "id": question_id,
            "category": category or None,
            "number": number,
            "question": question,
            "correct_word": correct_word,
            "meaning": meaning or None
        })
        db.session.commit()
        
        return jsonify({"ok": True, "message": "문제가 수정되었습니다."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/study_questions/<int:question_id>', methods=['DELETE'])
@login_required
def api_delete_study_question(question_id):
    """학습 문제 삭제"""
    try:
        delete_query = text("DELETE FROM exam_answer WHERE id = :id")
        db.session.execute(delete_query, {"id": question_id})
        db.session.commit()
        
        return jsonify({"ok": True, "message": "문제가 삭제되었습니다."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500

# ✅ 사용자 관리 API
@app.route('/api/users', methods=['GET'])
@login_required
def api_get_users():
    """모든 사용자-소스 매핑 목록 조회"""
    users = WordUser.query.order_by(WordUser.user_name, WordUser.source).all()
    return jsonify([{
        "id": u.id,
        "user_name": u.user_name,
        "source": u.source
    } for u in users])

@app.route('/api/users', methods=['POST'])
@login_required
def api_add_user():
    """사용자-소스 매핑 추가"""
    try:
        data = request.get_json()
        user_name = data.get('user_name', '').strip()
        source = data.get('source', '').strip()
        
        if not user_name or not source:
            return jsonify({"error": "사용자명과 소스를 모두 입력하세요."}), 400
        
        # 중복 체크
        exists = WordUser.query.filter_by(user_name=user_name, source=source).first()
        if exists:
            return jsonify({"error": "이미 등록된 사용자-소스 조합입니다."}), 400
        
        new_user = WordUser(user_name=user_name, source=source)
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            "ok": True,
            "id": new_user.id,
            "user_name": new_user.user_name,
            "source": new_user.source
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
def api_update_user(user_id):
    """사용자-소스 매핑 수정"""
    try:
        data = request.get_json()
        user_name = data.get('user_name', '').strip()
        source = data.get('source', '').strip()
        
        if not user_name or not source:
            return jsonify({"error": "사용자명과 소스를 모두 입력하세요."}), 400
        
        user = WordUser.query.get(user_id)
        if not user:
            return jsonify({"error": "사용자를 찾을 수 없습니다."}), 404
        
        # 중복 체크 (본인 제외)
        exists = WordUser.query.filter(
            WordUser.user_name == user_name,
            WordUser.source == source,
            WordUser.id != user_id
        ).first()
        if exists:
            return jsonify({"error": "이미 등록된 사용자-소스 조합입니다."}), 400
        
        user.user_name = user_name
        user.source = source
        db.session.commit()
        
        return jsonify({"ok": True, "message": "수정되었습니다."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def api_delete_user(user_id):
    """사용자-소스 매핑 삭제"""
    try:
        user = WordUser.query.get(user_id)
        if not user:
            return jsonify({"error": "사용자를 찾을 수 없습니다."}), 404
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({"ok": True, "message": "삭제되었습니다."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ✅ 디버그: 테스트 기록의 user_id 확인
@app.route('/debug/test_records')
@login_required
def debug_test_records():
    """디버그용: 최근 10개 테스트 기록의 user_id 확인"""
    records = db.session.execute(text("""
        SELECT TOP 10 id, test_name, user_id, completed_at
        FROM test_records_rows
        ORDER BY completed_at DESC
    """)).fetchall()
    
    result = [{
        "id": r.id,
        "test_name": r.test_name,
        "user_id": r.user_id,
        "completed_at": str(r.completed_at)
    } for r in records]
    
    return jsonify({
        "current_session_user_id": session.get('db_user_id'),
        "current_session_user_name": session.get('user_name'),
        "is_admin": session.get('is_admin'),
        "recent_records": result
    })

# ✅ 서버 실행
if __name__ == '__main__':
    app.run(debug=True)
