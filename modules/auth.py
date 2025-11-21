import streamlit as st
# 여기에 필요한 DB 연결 라이브러리가 있다면 import 해야 합니다 (예: cx_Oracle, pandas 등)
# 기존에 run_query 함수가 어디 있는지 모르겠지만, auth.py 내부에 있다고 가정하고 작성합니다.

def check_password(username):
    """
    사용자가 입력한 ID(username)를 받아 DB에서 확인하는 함수
    """
    # 1. 쿼리 작성 (바인딩 변수 :id 사용)
    query = "SELECT * FROM students WHERE id = :id"
    
    # 2. 쿼리 실행 (run_query는 사용자가 정의한 DB 실행 함수라고 가정)
    # 만약 run_query가 이 파일에 없다면, 에러가 날 수 있습니다.
    # 그럴 경우 기존에 쓰시던 DB 실행 코드로 바꿔야 합니다.
    try:
        # run_query 함수가 있다고 가정
        result = run_query(query, id=username) 
    except NameError:
        st.error("시스템 오류: 'run_query' 함수를 찾을 수 없습니다. DB 연결 코드를 확인해주세요.")
        return False

    # --- [디버깅 코드 시작] ---
    st.warning("--- 🔍 오라클 디버깅 모드 ---")
    st.write(f"1. 입력한 ID: '{username}' (길이: {len(username)})")
    st.write(f"2. DB 조회 결과: {result}")

    if not result:
        st.error("👉 결과가 비어있습니다. (DB 매칭 실패)")
        st.info("팁: DB 데이터 뒤에 공백이 있거나, 대소문자가 다를 수 있습니다.")
    else:
        st.success("👉 데이터를 찾았습니다!")
    # --- [디버깅 코드 끝] ---

    # 결과 반환
    if result:
        return True # 또는 result 자체를 반환
    else:
        return False
