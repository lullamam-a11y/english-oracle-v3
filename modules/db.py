# modules/db.py (최종 통합본: 자동 보정 + 모든 기능 포함)

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import pytz 
import re # [추가] 정규표현식 사용을 위해 필요

# ---------------------------------------------------------
# 1. 키 자동 보정 함수 (Incorrect Padding 해결사)
# ---------------------------------------------------------
def fix_private_key(key):
    """
    사용자가 입력한 키가 꼬여있을 경우, 강제로 분해해서 표준 형태로 재조립합니다.
    """
    try:
        # 1. 앞뒤 공백 제거
        key = key.strip()
        
        # 2. 이미 \n 처리가 되어 있다면 변환
        if "\\n" in key:
            key = key.replace("\\n", "\n")
            
        # 3. 헤더/푸터 내용 발라내기
        if "-----BEGIN PRIVATE KEY-----" in key:
            clean_body = key.replace("-----BEGIN PRIVATE KEY-----", "") \
                            .replace("-----END PRIVATE KEY-----", "")
        else:
            clean_body = key 
            
        # 4. 본문에 섞인 공백/줄바꿈 싹 제거 (순수 키값만 추출)
        clean_body = re.sub(r"\s+", "", clean_body)
        
        # 5. 표준 포맷으로 재조립
        fixed_key = f"-----BEGIN PRIVATE KEY-----\n{clean_body}\n-----END PRIVATE KEY-----"
        return fixed_key
    except Exception:
        return key

# ---------------------------------------------------------
# 2. 구글 시트 연결 및 인증 (Connection)
# ---------------------------------------------------------

# 권한 범위 (Scope)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
def get_connection():
    try:
        # [1] Secrets 가져오기
        if "gcp_service_account" not in st.secrets:
            st.error("🚨 Secrets 설정 오류: '[gcp_service_account]' 헤더를 찾을 수 없습니다.")
            return None

        # st.secrets는 수정 불가능 객체이므로 dict로 변환
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # [2] Private Key 강제 수리 (핵심 로직 적용)
        if "private_key" in creds_dict:
            raw_key = creds_dict["private_key"]
            creds_dict["private_key"] = fix_private_key(raw_key)
        
        # [3] google-auth 라이브러리로 인증 (신형)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES
        )
        
        # [4] gspread 연결
        client = gspread.authorize(creds)
        
        # [5] 시트 열기
        doc = client.open("Oracle_DB") 
        return doc
        
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("🚨 DB 연결 실패: 'Oracle_DB'라는 이름의 구글 시트를 찾을 수 없습니다. (봇 이메일 초대 필수)")
        return None
    except Exception as e:
        st.error(f"🔥 DB 연결 에러 (상세): {str(e)}")
        return None

# 연결 객체 생성
doc = get_connection()

# ---------------------------------------------------------
# 3. 워크시트 정의 (안전 장치 포함)
# ---------------------------------------------------------
if doc:
    try:
        user_sheet = doc.worksheet("Users")
        homework_list_sheet = doc.worksheet("Homework_List")
        homework_log_sheet = doc.worksheet("Homework_Log")
        exam_results_sheet = doc.worksheet("Exam_Results")
        weekly_history_sheet = doc.worksheet("Weekly_History")
    except gspread.WorksheetNotFound as e:
        st.warning(f"⚠️ 일부 시트를 찾을 수 없습니다: {e}")
        user_sheet = None
else:
    user_sheet = None
    homework_list_sheet = None
    homework_log_sheet = None
    exam_results_sheet = None
    weekly_history_sheet = None

# ---------------------------------------------------------
# 4. 데이터 조회/조작 함수들 (모든 기능 포함됨)
# ---------------------------------------------------------

def get_data(sheet_name):
    if doc is None: return []
    try:
        worksheet = doc.worksheet(sheet_name)
        return worksheet.get_all_records()
    except Exception:
        return []

def get_all_users():
    if user_sheet is None: return []
    try:
        users = user_sheet.get_all_records()
        return [f"{u['Student_ID']} ({u['Name']})" for u in users if str(u.get('Role','')).strip().lower() == 'student']
    except: return []

def get_homework_list(student_id):
    if homework_list_sheet is None: return []
    try:
        all_hw = homework_list_sheet.get_all_records()
        return [h for h in all_hw if str(h['Student_ID']) == str(student_id)]
    except: return []

def get_weekly_history(student_id):
    if weekly_history_sheet is None: return []
    try:
        rows = weekly_history_sheet.get_all_records()
        return [r for r in rows if str(r.get("Student_ID")) == str(student_id)]
    except: return []

def add_homework_assignment(student_id, category, task_name, custom_text, weekly_goal):
    if homework_list_sheet is None: return False
    try:
        homework_list_sheet.append_row([student_id, category, task_name, custom_text, weekly_goal])
        st.cache_data.clear()
        return True
    except: return False

def add_homework_log(student_id, task_name, day_of_week):
    if homework_log_sheet is None: return
    try:
        now = datetime.now(pytz.timezone('Asia/Seoul')).strftime("%Y-%m-%d %H:%M:%S")
        homework_log_sheet.append_row([student_id, task_name, now, day_of_week])
        st.cache_data.clear() 
    except: pass

def delete_homework_log(student_id, task_name, day_of_week):
    if homework_log_sheet is None: return False
    try:
        logs = homework_log_sheet.get_all_values()
        for i in range(len(logs) - 1, 0, -1):
            row = logs[i]
            if str(row[0]) == str(student_id) and str(row[1]) == str(task_name) and str(row[3]) == str(day_of_week):
                homework_log_sheet.delete_rows(i + 1) 
                st.cache_data.clear()
                return True
        return False
    except: return False

def reset_student_homework(student_id):
    if homework_list_sheet is None: return False
    try:
        all_rows = homework_list_sheet.get_all_values()
        header = all_rows[0]
        new_rows = [row for row in all_rows[1:] if str(row[0]) != str(student_id)]
        homework_list_sheet.clear()
        homework_list_sheet.append_row(header)
        if new_rows: homework_list_sheet.append_rows(new_rows)
        st.cache_data.clear()
        return True
    except: return False
