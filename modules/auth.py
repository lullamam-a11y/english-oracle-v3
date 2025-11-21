# modules/auth.py (안전장치 추가 버전)
import streamlit as st
import pandas as pd
from modules import db

def login():
    # 1. 세션 초기화
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["role"] = "student"

    query_params = st.query_params
    url_id = query_params.get("student_id", None)

    # 2. 자동 로그인 시도
    if not st.session_state["logged_in"] and url_id:
        try:
            users_data = db.get_data("Users")
            # [방어 로직] 데이터가 비어있으면 중단
            if users_data:
                df = pd.DataFrame(users_data)
                # 컬럼 이름 공백 제거
                df.columns = df.columns.str.strip()
                
                if "Student_ID" in df.columns:
                    user = df[df["Student_ID"].astype(str) == str(url_id)]
                    if not user.empty:
                        st.session_state["logged_in"] = True
                        st.session_state["user_name"] = user.iloc[0]["Name"]
                        st.session_state["user_id"] = user.iloc[0]["Student_ID"]
                        st.session_state["role"] = user.iloc[0].get("Role", "student")
        except Exception:
            pass 

    # 3. 로그인 상태면 통과
    if st.session_state["logged_in"]:
        return True

    # 4. 로그인 화면
    st.title("🔐 THE ORACLE: Access Gate")
    
    with st.form("login_form"):
        user_id = st.text_input("Student ID")
        password = st.text_input("Password", type="password")
        submit_btn = st.form_submit_button("Login")

        if submit_btn:
            users_data = db.get_data("Users")
            
            # [방어 로직] DB 연결 실패 등으로 데이터가 없으면 에러 메시지
            if not users_data:
                st.error("데이터베이스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.")
                return False

            df = pd.DataFrame(users_data)
            df.columns = df.columns.str.strip() # 컬럼명 공백 제거

            # 필수 컬럼 확인
            if "Student_ID" not in df.columns or "Password" not in df.columns:
                st.error("DB 구조 오류: Student_ID 컬럼을 찾을 수 없습니다.")
                return False

            # ID/PW 대조
            user = df[(df["Student_ID"].astype(str) == user_id) & (df["Password"].astype(str) == password)]

            if not user.empty:
                st.session_state["logged_in"] = True
                st.session_state["user_name"] = user.iloc[0]["Name"]
                st.session_state["user_id"] = user.iloc[0]["Student_ID"]
                st.session_state["role"] = user.iloc[0].get("Role", "student")
                
                st.query_params["student_id"] = user.iloc[0]["Student_ID"]
                
                st.success("로그인 성공! 접속 중...")
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호를 확인하세요.")
    
    return False

def logout():
    st.session_state["logged_in"] = False
    st.session_state["role"] = None
    st.query_params.clear()
    st.rerun()
