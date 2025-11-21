import streamlit as st
import traceback
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="시스템 정밀 진단", page_icon="🔍", layout="wide")

st.title("🔍 THE ORACLE: System Diagnostic")
st.write("시스템 연결 상태를 단계별로 점검하고 상세 에러를 출력합니다.")

# ---------------------------------------------------------
# 1. Secrets 점검
# ---------------------------------------------------------
st.header("1. Secrets 설정 점검")
if "gcp_service_account" not in st.secrets:
    st.error("❌ Secrets에 '[gcp_service_account]' 섹션이 없습니다.")
    st.stop()

try:
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        key_sample = creds_dict["private_key"][:20] + "..."
        st.success(f"✅ Secrets 로드 성공 (Key 시작부: {key_sample})")
        
        # 키 포맷 검사
        if "\\n" in creds_dict["private_key"]:
             st.info("ℹ️ 키에 이스케이프 된 줄바꿈(\\\\n)이 감지되었습니다. (코드에서 자동 변환 예정)")
        if "-----BEGIN PRIVATE KEY-----" not in creds_dict["private_key"]:
             st.warning("⚠️ 키 헤더(BEGIN PRIVATE KEY)가 보이지 않습니다. 키 값이 잘렸을 수 있습니다.")
    else:
        st.error("❌ Secrets는 있지만 'private_key' 항목이 비어 있습니다.")
        st.stop()
except Exception as e:
    st.error(f"❌ Secrets 읽기 실패: {e}")
    st.stop()

# ---------------------------------------------------------
# 2. 인증 및 연결 시도 (가장 중요한 부분)
# ---------------------------------------------------------
st.header("2. 구글 클라우드 인증 시도")

try:
    # 1. 키 수리 로직 (db.py와 동일하게 적용)
    import re
    raw_key = creds_dict["private_key"]
    
    # 자동 수리 시뮬레이션
    key_fixed = raw_key.strip()
    if "\\n" in key_fixed:
        key_fixed = key_fixed.replace("\\n", "\n")
    
    # 정규식으로 공백 제거 후 재조립
    if "-----BEGIN PRIVATE KEY-----" in key_fixed:
        clean_body = key_fixed.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "")
        clean_body = re.sub(r"\s+", "", clean_body)
        final_key = f"-----BEGIN PRIVATE KEY-----\n{clean_body}\n-----END PRIVATE KEY-----"
    else:
        final_key = key_fixed

    creds_dict["private_key"] = final_key
    
    # 2. Credentials 객체 생성
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    st.success("✅ 인증 객체(Credentials) 생성 성공")

    # 3. Gspread 연결
    client = gspread.authorize(creds)
    st.success("✅ Gspread 클라이언트 승인 성공")

except Exception as e:
    st.error("🔥 인증 과정에서 치명적 에러 발생!")
    st.code(traceback.format_exc()) # 여기가 진짜 에러를 보여주는 곳
    st.stop()

# ---------------------------------------------------------
# 3. 스프레드시트 접근 테스트
# ---------------------------------------------------------
st.header("3. DB(스프레드시트) 접근 테스트")

target_sheet = "Oracle_DB" # 파일명 확인

try:
    doc = client.open(target_sheet)
    st.success(f"✅ 파일 '{target_sheet}' 찾기 성공!")
    
    # 워크시트 목록 출력
    worksheets = doc.worksheets()
    ws_names = [ws.title for ws in worksheets]
    st.write(f"📂 발견된 탭(Worksheets): {ws_names}")
    
    if "Users" in ws_names:
        st.success("✅ 'Users' 탭 확인됨. 데이터 로드 시도...")
        rows = doc.worksheet("Users").get_all_records()
        st.write(f"📊 데이터 {len(rows)}행 로드 성공")
        st.dataframe(rows) # 데이터 보여주기
    else:
        st.error("❌ 'Users' 탭이 없습니다! 탭 이름을 정확히 'Users'로 수정하세요.")

except gspread.exceptions.SpreadsheetNotFound:
    st.error(f"❌ 에러: '{target_sheet}'라는 파일을 찾을 수 없습니다.")
    st.warning("👉 해결책: 구글 시트 우측 상단 [공유] 버튼 -> 봇 이메일을 [편집자]로 추가했는지 확인하세요.")
    st.code(creds_dict.get("client_email", "이메일 확인 불가"))
    
except Exception as e:
    st.error("🔥 DB 연결 중 에러 발생!")
    st.code(traceback.format_exc())
