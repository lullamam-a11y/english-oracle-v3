# modules/auth.py (범인 색출용 디버깅 모드)
import streamlit as st
import pandas as pd
from modules import db

def login():
    # 세션 초기화
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["role"] = "student"

    # 이미 로그인 상태면 패스
    if st.session_state["logged_in"]:
        return True

    st.title("🔐 THE ORACLE: Access Gate")
    
    with st.form("login_form"):
        user_id = st.text_input("Student ID")
        password = st.text_input("Password", type="password")
        submit_btn = st.form_submit_button("Login")

        if submit_btn:
            users_data = db.get_data("Users")
            
            if not users_data:
                st.error("❌ DB에서 데이터를 가져오지 못했습니다. (데이터 없음)")
                return False

            df = pd.DataFrame(users_data)
            
            # -------------------------------------------------------
            # 🕵️‍♂️ [범인 색출] 컴퓨터가 읽은 컬럼명을 적나라하게 보여줌
            # -------------------------------------------------------
            st.warning("🔍 [디버깅 모드] 현재 인식된 컬럼 목록입니다:")
            st.code(df.columns.tolist()) # 리스트 형태로 그대로 출력
            
            # 공백 강제 제거 시도
            df.columns = df.columns.str.strip()
            
            # 필수 컬럼 체크
            if "Student_ID" not in df.columns:
                st.error(f"🚨 치명적 오류: 'Student_ID' 컬럼이 없습니다!")
                st.info("위의 [디버깅 모드] 목록을 확인하세요. 'Student_ID ' 처럼 공백이 있거나 오타가 있을 것입니다.")
                return False

            # 로그인 로직 진행
            user = df[(df["Student_ID"].astype(str) == user_id) & (df["Password"].astype(str) == password)]

            if not user.empty:
                st.session_state["logged_in"] = True
                st.session_state["user_name"] = user.iloc[0]["Name"]
                st.session_state["user_id"] = user.iloc[0]["Student_ID"]
                st.session_state["role"] = user.iloc[0].get("Role", "student")
                st.success("로그인 성공! 접속 중...")
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 일치하지 않습니다.")
    
    return False

def logout():
    st.session_state["logged_in"] = False
    st.session_state["role"] = None
    st.rerun()
