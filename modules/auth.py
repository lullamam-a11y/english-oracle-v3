# modules/auth.py
import streamlit as st
import pandas as pd
from modules import db
import time

def login():
    # 1. 세션 변수 초기화 (없을 경우에만)
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["role"] = "student"
        st.session_state["user_name"] = ""
        st.session_state["user_id"] = ""

    # 2. [핵심] URL에서 꼬리표(student_id) 확인
    # 새로고침 해도 이 값은 주소창에 남아있습니다.
    query_params = st.query_params
    url_id = query_params.get("student_id", None)

    # 3. 자동 로그인 시도 (로그인 안 된 상태인데, URL에 ID가 있다면)
    if not st.session_state["logged_in"] and url_id:
        with st.spinner("계정 정보를 확인 중입니다..."):
            try:
                users_data = db.get_data("Users")
                if users_data:
                    df = pd.DataFrame(users_data)
                    # 컬럼명 공백 제거 및 문자열 변환
                    df.columns = df.columns.str.strip()
                    
                    if "Student_ID" in df.columns:
                        # URL에 있는 ID와 일치하는 유저 찾기
                        user = df[df["Student_ID"].astype(str) == str(url_id)]
                        
                        if not user.empty:
                            # 유저 찾음 -> 즉시 로그인 처리
                            st.session_state["logged_in"] = True
                            st.session_state["user_name"] = user.iloc[0]["Name"]
                            st.session_state["user_id"] = user.iloc[0]["Student_ID"]
                            st.session_state["role"] = user.iloc[0].get("Role", "student")
                            # 성공했으므로 함수 종료 (로그인 화면 안 띄움)
                            return True
            except Exception as e:
                # DB 연결 실패 시엔 그냥 넘어감 (로그인 화면 나오게)
                print(f"자동 로그인 실패: {e}")

    # 4. 이미 로그인 된 상태라면 통과
    if st.session_state["logged_in"]:
        return True

    # ---------------------------------------------------------
    # 5. 로그인 화면 (로그인 안 된 경우에만 실행)
    # ---------------------------------------------------------
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

            # ID/PW 검증
            try:
                user = df[(df["Student_ID"].astype(str) == str(user_id)) & 
                          (df["Password"].astype(str) == str(password))]

                if not user.empty:
                    # 로그인 성공 처리
                    st.session_state["logged_in"] = True
                    st.session_state["user_name"] = user.iloc[0]["Name"]
                    st.session_state["user_id"] = user.iloc[0]["Student_ID"]
                    st.session_state["role"] = user.iloc[0].get("Role", "student")
                    
                    # [핵심] 로그인 성공 시 URL에 꼬리표 붙이기
                    st.query_params["student_id"] = user.iloc[0]["Student_ID"]
                    
                    st.success(f"환영합니다, {st.session_state['user_name']}님!")
                    time.sleep(0.5)
                    st.rerun() # 새로고침해서 로그인 된 화면 보여주기
                else:
                    st.error("아이디 또는 비밀번호가 일치하지 않습니다.")
            except Exception as e:
                st.error(f"로그인 처리 중 오류 발생: {e}")
    
    return False

def logout():
    # 로그아웃 시 세션과 URL 꼬리표 모두 제거
    st.session_state["logged_in"] = False
    st.session_state["role"] = None
    st.session_state["user_name"] = ""
    st.session_state["user_id"] = ""
    
    # URL 파라미터 초기화
    st.query_params.clear()
    
    st.success("로그아웃 되었습니다.")
    time.sleep(0.5)
    st.rerun()
