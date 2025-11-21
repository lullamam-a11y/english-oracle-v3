# modules/auth.py
import streamlit as st
import pandas as pd
from modules import db  # modules 폴더 내 db.py를 임포트

def login():
    # 1. 세션 초기화
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["role"] = "student"
        st.session_state["user_name"] = ""
        st.session_state["user_id"] = ""

    query_params = st.query_params
    url_id = query_params.get("student_id", None)

    # 2. 자동 로그인 시도 (URL 파라미터가 있을 때)
    if not st.session_state["logged_in"] and url_id:
        try:
            users_data = db.get_data("Users")
            if users_data:
                df = pd.DataFrame(users_data)
                df.columns = df.columns.str.strip() # 컬럼 공백 제거
                
                if "Student_ID" in df.columns:
                    # 문자열로 변환하여 비교
                    user = df[df["Student_ID"].astype(str) == str(url_id)]
                    if not user.empty:
                        st.session_state["logged_in"] = True
                        st.session_state["user_name"] = user.iloc[0]["Name"]
                        st.session_state["user_id"] = user.iloc[0]["Student_ID"]
                        st.session_state["role"] = user.iloc[0].get("Role", "student")
        except Exception:
            pass 

    # 3. 로그인 성공 상태라면 True 반환
    if st.session_state["logged_in"]:
        return True

    # 4. 로그인 화면 출력
    st.title("🔐 THE ORACLE: Access Gate")
    
    with st.form("login_form"):
        user_id = st.text_input("Student ID")
        password = st.text_input("Password", type="password")
        submit_btn = st.form_submit_button("Login")

        if submit_btn:
            users_data = db.get_data("Users")
            
            # DB 연결 실패 시 처리
            if not users_data:
                st.error("데이터베이스 연결 실패. 관리자에게 문의하세요.")
                return False

            df = pd.DataFrame(users_data)
            df.columns = df.columns.str.strip()

            # 필수 컬럼 확인
            if "Student_ID" not in df.columns or "Password" not in df.columns:
                st.error("DB 구조 오류: 필수 컬럼(Student_ID, Password)이 누락되었습니다.")
                return False

            # ID/PW 대조 (문자열 변환 후 비교)
            user = df[(df["Student_ID"].astype(str) == str(user_id)) & 
                      (df["Password"].astype(str) == str(password))]

            if not user.empty:
                st.session_state["logged_in"] = True
                st.session_state["user_name"] = user.iloc[0]["Name"]
                st.session_state["user_id"] = user.iloc[0]["Student_ID"]
                st.session_state["role"] = user.iloc[0].get("Role", "student")
                
                # URL에 ID 쿼리 추가 (재접속 시 자동로그인용)
                st.query_params["student_id"] = user.iloc[0]["Student_ID"]
                
                st.success(f"환영합니다, {user.iloc[0]['Name']}님! 접속 중...")
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 일치하지 않습니다.")
    
    return False

def logout():
    st.session_state["logged_in"] = False
    st.session_state["role"] = None
    st.session_state["user_name"] = ""
    st.session_state["user_id"] = ""
    st.query_params.clear() # URL 파라미터도 초기화
    st.rerun()
