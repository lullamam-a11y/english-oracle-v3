# app.py
import streamlit as st
from modules import auth, homework, dashboard, admin, style

# 1. 페이지 설정 (가장 먼저 실행)
st.set_page_config(page_title="THE ORACLE", page_icon="🔮", layout="centered")

# 2. 스타일 적용
style.apply_custom_style()

# 3. 로그인 체크 (The Gate)
if not auth.login():
    st.stop()

# =========================================================
# [핵심 기능] 사이드바 (접이식 메뉴) 구현
# =========================================================
with st.sidebar:
    # 사이드바 상단 프로필 영역
    st.title("🔮 THE ORACLE")
    
    # 로그인한 사용자 정보 표시
    user_name = st.session_state.get("user_name", "학생")
    user_id = st.session_state.get("user_id", "")
    role = st.session_state.get("role", "student")
    
    st.write(f"👋 반갑습니다, **{user_name}**님")
    st.caption(f"ID: {user_id} ({role})")
    
    st.divider()
    
    # [권한 분기] 메뉴 선택 (로그아웃은 리스트에서 제거됨)
    if role == "teacher":
        # 선생님용 메뉴
        menu = st.radio("메뉴 선택",
            ["전체 현황 (Admin)", "숙제 관리 (View)"], 
            index=0)
    else:
        # 학생용 메뉴 ("Dashboard" -> "숙제 현황" 변경 완료)
        menu = st.radio("메뉴 선택",
            ["주간 체크리스트", "숙제 현황", "Voca Test"], 
            index=0)

    # -----------------------------------------------------
    # [UI] 사이드바 하단 로그아웃 버튼 (안전지대)
    # -----------------------------------------------------
    st.write("") # 여백 추가
    st.write("") 
    st.divider() # 구분선으로 확실히 분리
    
    # 로그아웃 버튼을 누르면 즉시 실행
    if st.button("🚪 로그아웃", use_container_width=True):
        auth.logout()
        
    st.caption("System v1.0")

# =========================================================
# [메인 화면] 메뉴별 페이지 라우팅
# =========================================================

# 1. [선생님] 전체 현황판 (Admin)
if menu == "전체 현황 (Admin)":
    admin.show_admin_page()

# 2. [공통] 숙제 관리 (학생은 자기 것, 선생님은 확인용)
elif menu == "숙제 관리 (View)" or menu == "주간 체크리스트":
    homework.show_tracker()

# 3. [학생] 숙제 현황 (대시보드 -> "숙제 현황"으로 연결)
elif menu == "숙제 현황":
    dashboard.show_dashboard()

# 4. [학생] 단어 시험 (추후 개발 예정)
elif menu == "Voca Test":
    st.info("🧠 단어 시험 모듈 준비 중입니다.")