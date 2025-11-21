# modules/auth.py (자동 로그인 + 권한 관리 통합 버전)
import streamlit as st
import pandas as pd
from modules import db

def login():
    # ------------------------------------------------------------------
    # [Step 1] URL이나 세션을 확인해서 자동 로그인 시도
    # ------------------------------------------------------------------
    
    # 1. 세션 변수 초기화 (로그인 상태 & 권한)
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["role"] = "student" # 기본값은 학생

    # 2. URL에 'student_id' 꼬리표가 있는지 확인 (새로고침 대응)
    query_params = st.query_params
    url_id = query_params.get("student_id", None)

    # 3. 세션에는 없는데 URL에는 ID가 있다면? -> DB 확인 후 자동 로그인 처리
    if not st.session_state["logged_in"] and url_id:
        try:
            users_data = db.get_data("Users")
            df = pd.DataFrame(users_data)
            
            # URL에 있는 ID가 실제 DB에 존재하는지 검증
            user = df[df["Student_ID"].astype(str) == str(url_id)]
            
            if not user.empty:
                # 검증 통과! 세션에 정보 입력
                st.session_state["logged_in"] = True
                st.session_state["user_name"] = user.iloc[0]["Name"]
                st.session_state["user_id"] = user.iloc[0]["Student_ID"]
                
                # [New] 권한(Role) 정보 읽어오기
                # 혹시 Role 컬럼을 안 만들었을 경우를 대비해 안전장치 추가
                if "Role" in user.columns:
                    st.session_state["role"] = user.iloc[0]["Role"]
                else:
                    st.session_state["role"] = "student"
                    
        except Exception:
            pass # DB 연결 에러 시 그냥 로그인 화면으로

    # ------------------------------------------------------------------
    # [Step 2] 로그인 여부 최종 판단
    # ------------------------------------------------------------------
    
    # 이미 로그인 된 상태라면 (세션 O) -> 문 열어줌
    if st.session_state["logged_in"]:
        return True

    # ------------------------------------------------------------------
    # [Step 3] 로그인 화면 출력 (아직 로그인 안 된 경우)
    # ------------------------------------------------------------------
    st.title("🔐 THE ORACLE: Access Gate")
    
    with st.form("login_form"):
        user_id = st.text_input("Student ID")
        password = st.text_input("Password", type="password")
        submit_btn = st.form_submit_button("Login")

        if submit_btn:
            users_data = db.get_data("Users")
            df = pd.DataFrame(users_data)
            
            # ID/PW 대조
            user = df[(df["Student_ID"].astype(str) == user_id) & (df["Password"].astype(str) == password)]

            if not user.empty:
                # 로그인 성공!
                st.session_state["logged_in"] = True
                st.session_state["user_name"] = user.iloc[0]["Name"]
                st.session_state["user_id"] = user.iloc[0]["Student_ID"]
                
                # [New] 권한(Role) 정보 저장
                if "Role" in user.columns:
                    st.session_state["role"] = user.iloc[0]["Role"]
                else:
                    st.session_state["role"] = "student"
                
                # [핵심] URL에 꼬리표 달기 (이제 새로고침해도 기억함!)
                st.query_params["student_id"] = user.iloc[0]["Student_ID"]
                
                st.success("로그인 성공! 접속 중...")
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호를 확인하세요.")
    
    return False

def logout():
    """로그아웃 버튼용 함수"""
    st.session_state["logged_in"] = False
    st.session_state["role"] = None # 권한도 초기화
    st.query_params.clear() # URL 꼬리표 제거
    st.rerun()