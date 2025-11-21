# modules/db.py (최종 수정본: Native Dictionary 방식)

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import pytz 

# ---------------------------------------------------------
# 1. 구글 시트 연결 및 인증 (Connection)
# ---------------------------------------------------------

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
def get_connection():
    try:
        # [핵심 변경] Secrets에서 'gcp_service_account' 섹션을 딕셔너리로 바로 가져옵니다.
        # 파일을 만들거나 JSON 파싱을 할 필요가 없어 'Incorrect padding' 오류가 사라집니다.
        creds_dict = st.secrets["gcp_service_account"]
        
        # 딕셔너리로 바로 인증
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        
        # 연결
        client = gspread.authorize(creds)
        doc = client.open("Oracle_DB")
        return doc
        
    except Exception as e:
        st.error(f"🔥 최종 DB 연결 에러: {e}") 
        return None

# 연결 객체 생성
doc = get_connection()

# ---------------------------------------------------------
# 2. 워크시트 정의
# ---------------------------------------------------------
if doc:
    try:
        user_sheet = doc.worksheet("Users")
        homework_list_sheet = doc.worksheet("Homework_List")
        homework_log_sheet = doc.worksheet("Homework_Log")
        exam_results_sheet = doc.worksheet("Exam_Results")
        weekly_history_sheet = doc.worksheet("Weekly_History")
    except gspread.WorksheetNotFound as e:
        st.error(f"⚠️ 시트를 찾을 수 없습니다: {e}")
        st.stop() 

# ---------------------------------------------------------
# 3. 데이터 조회/조작 함수들 (기존 로직 유지)
# ---------------------------------------------------------

@st.cache_data(ttl=60)
def get_data(sheet_name):
    try:
        worksheet = doc.worksheet(sheet_name)
        return worksheet.get_all_records()
    except Exception as e:
        # DB 연결이 끊겼거나 에러 발생 시 빈 리스트 반환
        return []

def get_all_users():
    try:
        users = user_sheet.get_all_records()
        user_list = [
            f"{u['Student_ID']} ({u['Name']})" 
            for u in users 
            if str(u.get('Role', '')).strip().lower() == 'student'
        ]
        return user_list
    except Exception as e:
        return []

def get_homework_list(student_id):
    try:
        all_hw = homework_list_sheet.get_all_records()
        my_hw = [h for h in all_hw if str(h['Student_ID']) == str(student_id)]
        return my_hw
    except Exception as e:
        return []

def get_weekly_history(student_id):
    try:
        rows = weekly_history_sheet.get_all_records()
        if not rows: return []
        return [r for r in rows if str(r.get("Student_ID")) == str(student_id)]
    except Exception: return []

def add_homework_assignment(student_id, category, task_name, custom_text, weekly_goal):
    try:
        row_data = [student_id, category, task_name, custom_text, weekly_goal]
        homework_list_sheet.append_row(row_data)
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"숙제 배정 실패: {e}")
        return False

def add_homework_log(student_id, task_name, day_of_week):
    try:
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        row = [student_id, task_name, now, day_of_week]
        homework_log_sheet.append_row(row)
        st.cache_data.clear() 
    except Exception as e:
        st.error(f"저장 실패: {e}")

def delete_homework_log(student_id, task_name, day_of_week):
    try:
        logs = homework_log_sheet.get_all_values()
        for i in range(len(logs) - 1, 0, -1):
            row = logs[i]
            if (str(row[0]) == str(student_id) and 
                str(row[1]) == str(task_name) and 
                str(row[3]) == str(day_of_week)):
                homework_log_sheet.delete_rows(i + 1) 
                st.cache_data.clear()
                return True
        return False
    except Exception as e:
        st.error(f"삭제 실패: {e}")
        return False

def archive_old_logs():
    return 0

def reset_student_homework(student_id):
    try:
        all_rows = homework_list_sheet.get_all_values()
        header = all_rows[0]
        data_rows = all_rows[1:]
        new_rows = [row for row in data_rows if str(row[0]) != str(student_id)]
        homework_list_sheet.clear()
        homework_list_sheet.append_row(header)
        if new_rows:
            homework_list_sheet.append_rows(new_rows) 
        return True
    except Exception as e:
        return False
