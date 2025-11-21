import streamlit as st
import traceback
import gspread
from google.oauth2.service_account import Credentials
import re
import base64
import binascii
import pandas as pd

st.set_page_config(page_title="시스템 정밀 진단", page_icon="🔍", layout="wide")
st.title("🔍 THE ORACLE: System Diagnostic V3 (Final)")

# ---------------------------------------------------------
# 1. Secrets 키 정밀 분석 (V2 기능)
# ---------------------------------------------------------
st.header("1. Secrets 키 정밀 검사")

if "gcp_service_account" not in st.secrets:
    st.error("❌ Secrets 설정이 없습니다.")
    st.stop()

try:
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" not in creds_dict:
        st.error("❌ private_key 항목이 비어 있습니다.")
        st.stop()

    raw_key = creds_dict["private_key"]
    st.info(f"🔑 입력된 키 길이: {len(raw_key)} 자")

    # [전처리] 공백/헤더/줄바꿈 싹 제거해서 알맹이만 추출
    clean_body = raw_key.replace("\\n", "")
    clean_body = clean_body.replace("\n", "")
    clean_body = clean_body.replace("-----BEGIN PRIVATE KEY-----", "")
    clean_body = clean_body.replace("-----END PRIVATE KEY-----", "")
    clean_body = re.sub(r"\s+", "", clean_body) # 숨은 공백 제거

    # [검사 1] Base64 패딩 검사
    remainder = len(clean_body) % 4
    if remainder != 0:
        st.error(f"🔥 [치명적 손상] 키의 일부가 잘렸습니다!")
        st.error(f"- 원인: 암호문 길이는 4의 배수여야 하는데 **{remainder}자**가 남습니다.")
        st.warning(f"👉 해결: 키 맨 끝에 '=' 기호가 {4-remainder}개 누락되었거나, 복사가 덜 되었습니다. 새 키를 발급받으세요.")
        st.stop()
    
    # [검사 2] 디코딩 테스트
    try:
        base64.b64decode(clean_body, validate=True)
        st.success("✅ 키 포맷 정상 (Base64 디코딩 통과)")
    except binascii.Error as e:
        st.error(f"❌ 키 내용 손상 (디코딩 실패): {e}")
        st.stop()

    # [재조립] 표준 포맷으로 복구
    final_key = f"-----BEGIN PRIVATE KEY-----\n{clean_body}\n-----END PRIVATE KEY-----"
    creds_dict["private_key"] = final_key

    # ---------------------------------------------------------
    # 2. 연결 및 인증 (공통 기능)
    # ---------------------------------------------------------
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    st.success("✅ 구글 클라우드 인증 성공")

    # ---------------------------------------------------------
    # 3. 데이터 확인 (V1 기능 복구)
    # ---------------------------------------------------------
    st.header("2. DB(스프레드시트) 데이터 확인")
    
    target_sheet = "Oracle_DB"
    doc = client.open(target_sheet)
    st.success(f"📂 파일 연결 성공: {doc.title}")

    # 워크시트 목록 가져오기
    worksheets = doc.worksheets()
    ws_names = [ws.title for ws in worksheets]
    st.write(f"📑 발견된 시트 탭: {ws_names}")

    if "Users" in ws_names:
        st.success("✅ 'Users' 탭 데이터 로드 중...")
        data = doc.worksheet("Users").get_all_records()
        
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df.head()) # 상위 5줄만 보여주기
            st.caption(f"총 {len(df)}명의 사용자 데이터가 있습니다.")
        else:
            st.warning("⚠️ 'Users' 탭이 비어 있습니다.")
    else:
        st.error("❌ 'Users' 탭을 찾을 수 없습니다.")

except Exception as e:
    st.error("🔥 진단 중 예상치 못한 에러 발생")
    st.code(traceback.format_exc())
