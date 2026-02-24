"""
DB 마이그레이션 스크립트: words_rows 테이블에 language, pronunciation 컬럼 추가
기존 데이터는 모두 'english'로 설정
"""
import pyodbc

# SQL Server 연결 설정
conn_str = (
    "Driver={ODBC Driver 18 for SQL Server};"
    "Server=ms1901.gabiadb.com;"
    "Database=yujincast;"
    "UID=pinkyj81;"
    "PWD=zoskek38!!;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    print("데이터베이스 연결 성공")
    
    # 1. language 컬럼 추가
    try:
        cursor.execute("""
            ALTER TABLE words_rows 
            ADD language NVARCHAR(50) DEFAULT 'english'
        """)
        print("✓ language 컬럼 추가 완료")
    except Exception as e:
        if "already exists" in str(e) or "duplicate" in str(e).lower():
            print("✓ language 컬럼이 이미 존재합니다")
        else:
            raise e
    
    # 2. pronunciation 컬럼 추가
    try:
        cursor.execute("""
            ALTER TABLE words_rows 
            ADD pronunciation NVARCHAR(200)
        """)
        print("✓ pronunciation 컬럼 추가 완료")
    except Exception as e:
        if "already exists" in str(e) or "duplicate" in str(e).lower():
            print("✓ pronunciation 컬럼이 이미 존재합니다")
        else:
            raise e
    
    # 3. 기존 데이터 업데이트 (NULL인 경우만)
    cursor.execute("""
        UPDATE words_rows 
        SET language = 'english' 
        WHERE language IS NULL
    """)
    updated_count = cursor.rowcount
    print(f"✓ 기존 데이터 {updated_count}개를 'english'로 업데이트 완료")
    
    conn.commit()
    print("\n✅ 마이그레이션이 성공적으로 완료되었습니다!")
    
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    if 'conn' in locals():
        conn.rollback()
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()
