# modules/auth.py
import streamlit as st
import pandas as pd
from modules import db
import time

def login():
    # 1. 세션 변수 초기화
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["role"] = "student"
        st.session_state["user_name"] = ""
        st.session_state["user_id"] = ""

    # 2. URL 파라미터 확인
    query_params = st.query_params
    url_id = query_params.get("student_id", None)

    # 3. 자동 로그인 시도
    if not st.session_state["logged_in"] and url_id:
        with st.spinner("계정 정보를 확인 중입니다..."):
            try:
                users_data = db.get_data("Users")
                if users_data:
                    df = pd.DataFrame(users_data)
                    df.columns = df.columns.str.strip()
                    
                    if "Student_ID" in df.columns:
                        user = df[df["Student_ID"].astype(str) == str(url_id)]
                        
                        if not user.empty:
                            st.session_state["logged_in"] = True
                            st.session_state["user_name"] = user.iloc[0]["Name"]
                            st.session_state["user_id"] = user.iloc[0]["Student_ID"]
                            st.session_state["role"] = user.iloc[0].get("Role", "student")
                            return True
            except Exception as e:
                print(f"자동 로그인 실패: {e}")

    # 4. 이미 로그인 상태면 통과
    if st.session_state["logged_in"]:
        return True

    # 5. 로그인 화면
    st.markdown(
        """
        <h1 style='text-align: center;'>🔐 THE ORACLE</h1>
        <p style='text-align: center;'>Access Gate</p>
        """, 
        unsafe_allow_html=True
    )
    
    with st.form("login_form"):
        user_id = st.text_input("Student ID", placeholder="학번을 입력하세요")
        password = st.text_input("Password", type="password", placeholder="비밀번호")
        
        submit_btn = st.form_submit_button("Login", use_container_width=True)

        if submit_btn:
            if not user_id or not password:
                st.warning("아이디와 비밀번호를 모두 입력해주세요.")
                return False

            with st.spinner("DB 접속 중..."):
                users_data = db.get_data("Users")
            
            if not users_data:
                st.error("데이터베이스 연결에 실패했습니다. 잠시 후 다시 시도하세요.")
                return False

            df = pd.DataFrame(users_data)
            df.columns = df.columns.str.strip()

            try:
                user = df[(df["Student_ID"].astype(str) == str(user_id)) & 
                          (df["Password"].astype(str) == str(password))]

                if not user.empty:
                    st.session_state["logged_in"] = True
                    st.session_state["user_name"] = user.iloc[0]["Name"]
                    st.session_state["user_id"] = user.iloc[0]["Student_ID"]
                    st.session_state["role"] = user.iloc[0].get("Role", "student")
                    
                    st.query_params["student_id"] = user.iloc[0]["Student_ID"]
                    
                    st.success(f"환영합니다, {st.session_state['user_name']}님!")
                    time.sleep(0.5)
                    st.rerun() 
                else:
                    st.error("아이디 또는 비밀번호가 일치하지 않습니다.")
            except Exception as e:
                st.error(f"로그인 처리 중 오류 발생: {e}")
    
    return False

def logout():
    st.session_state["logged_in"] = False
    st.session_state["role"] = None
    st.session_state["user_name"] = ""
    st.session_state["user_id"] = ""
    
    st.query_params.clear()
    
    st.success("로그아웃 되었습니다.")
    time.sleep(0.5)
    st.rerun()
