# (수정 코드) auth.py 내부

# 1. 쿼리 실행
query = f"SELECT * FROM students WHERE id = :id" # 바인딩 변수 사용 권장
result = run_query(query, id=username)

# --- [디버깅 코드 시작: 배포 후 화면에서 확인] ---
import streamlit as st
st.error("--- 🔍 오라클 디버깅 모드 ---")
st.write(f"1. 사용자가 입력한 ID: '{username}' (길이: {len(username)})") # 공백 포함 여부 확인
st.write(f"2. 실행된 쿼리 결과(Raw Data): {result}") 

# 결과가 리스트나 DataFrame인지 확인
if not result:
    st.write("👉 결과가 비어있습니다. (DB에서 매칭 실패)")
else:
    st.write("👉 데이터를 성공적으로 가져왔습니다.")
# --- [디버깅 코드 끝] ---

if result:
    return True
# ...
