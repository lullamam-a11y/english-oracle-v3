# modules/db.py
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import pytz 

# ---------------------------------------------------------
# 1. 구글 시트 연결 및 인증 (Connection) - [수정 완료]
# ---------------------------------------------------------

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
def get_connection():
    try:
        # [핵심 수정 1] st.secrets 객체를 순수 파이썬 딕셔너리로 강제 변환
        # (oauth2client는 streamlit의 secrets 객체를 바로 인식하지 못할 수 있음)
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # [핵심 수정 2] Private Key의 줄바꿈 문자(\n)를 실제 엔터키로 변환
        # (TOML 파일에서 불러올 때 발생하는 이스케이프 문자 문제를 해결)
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        # 수정된 딕셔너리로 인증 진행
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        
        # 연결
        client = gspread.authorize(creds)
        doc = client.open("Oracle_DB") # 파일명이 정확히 'Oracle_DB'여야 함
        return doc
        
    except Exception as e:
        # 연결 실패 시 에러 로그 출력 (앱이 멈추지 않도록 None 반환)
        print(f"🔥 DB 연결 에러: {e}") 
        return None

# 연결 객체 생성 (앱 실행 시 1회 수행)
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
        st.error(f"⚠️ 시트를 찾을 수 없습니다. 탭 이름을 확인하세요: {e}")
        st.stop()
else:
    # DB 연결 실패 시 전역 변수 초기화 방지용 (안전장치)
    user_sheet = None
    homework_list_sheet = None
    homework_log_sheet = None
    exam_results_sheet = None
    weekly_history_sheet = None

# ---------------------------------------------------------
# 3. 데이터 조회/조작 함수들
# ---------------------------------------------------------

def get_data(sheet_name):
    """시트 데이터를 가져오는 함수 (연결 실패 시 빈 리스트 반환)"""
    if doc is None:
        return []
    try:
        worksheet = doc.worksheet(sheet_name)
        return worksheet.get_all_records()
    except Exception:
        return []

def get_all_users():
    if user_sheet is None: return []
    try:
        users = user_sheet.get_all_records()
        user_list = [
            f"{u['Student_ID']} ({u['Name']})" 
            for u in users 
            if str(u.get('Role', '')).strip().lower() == 'student'
        ]
        return user_list
    except Exception:
        return []

def get_homework_list(student_id):
    if homework_list_sheet is None: return []
    try:
        all_hw = homework_list_sheet.get_all_records()
        my_hw = [h for h in all_hw if str(h['Student_ID']) == str(student_id)]
        return my_hw
    except Exception:
        return []

def get_weekly_history(student_id):
    if weekly_history_sheet is None: return []
    try:
        rows = weekly_history_sheet.get_all_records()
        if not rows: return []
        return [r for r in rows if str(r.get("Student_ID")) == str(student_id)]
    except Exception: return []

def add_homework_assignment(student_id, category, task_name, custom_text, weekly_goal):
    if homework_list_sheet is None: return False
    try:
        row_data = [student_id, category, task_name, custom_text, weekly_goal]
        homework_list_sheet.append_row(row_data)
        # 캐시 무효화 (즉시 반영을 위해)
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"숙제 배정 실패: {e}")
        return False

def add_homework_log(student_id, task_name, day_of_week):
    if homework_log_sheet is None: return
    try:
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        row = [student_id, task_name, now, day_of_week]
        homework_log_sheet.append_row(row)
        st.cache_data.clear() 
    except Exception as e:
        st.error(f"저장 실패: {e}")

def delete_homework_log(student_id, task_name, day_of_week):
    if homework_log_sheet is None: return False
    try:
        logs = homework_log_sheet.get_all_values()
        # 뒤에서부터 검색하여 최신 로그 삭제
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

def reset_student_homework(student_id):
    if homework_list_sheet is None: return False
    try:
        all_rows = homework_list_sheet.get_all_values()
        if not all_rows: return False
        
        header = all_rows[0]
        data_rows = all_rows[1:]
        
        # 해당 학생을 제외한 행만 남김
        new_rows = [row for row in data_rows if str(row[0]) != str(student_id)]
        
        homework_list_sheet.clear()
        homework_list_sheet.append_row(header)
        if new_rows:
            homework_list_sheet.append_rows(new_rows) 
        st.cache_data.clear()
        return True
    except Exception as e:
        return False
