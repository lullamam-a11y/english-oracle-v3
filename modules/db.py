# modules/db.py (최종 통합 완성본)

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import pytz # 한국 시간 처리를 위해 필요
import json # 추가
import os  #

# ---------------------------------------------------------
# 1. 구글 시트 연결 및 인증 (Connection)
# ---------------------------------------------------------
# 이 부분은 앱이 켜질 때 딱 한 번만 실행되어 연결을 맺습니다.

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
def get_connection():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'] 
    
    # [핵심] 1. JSON 내용을 임시 파일로 저장하여 인증
    creds_json = st.secrets["GOOGLE_CREDENTIALS"]
    temp_file_path = "creds.json"
    
    try:
        # CRITICAL FIX: .strip()으로 앞뒤의 모든 공백/빈 줄을 제거하여 JSON 무결성 확보
        cleaned_json = creds_json.strip() 
        
        # 1. 파일 쓰기 (임시)
        with open(temp_file_path, "w") as f:
            f.write(cleaned_json) 
            
        # 2. 임시 파일을 사용하여 인증
        creds = ServiceAccountCredentials.from_json_keyfile_name(temp_file_path, scope)
        
        # 3. Google Sheets 연결
        client = gspread.authorize(creds)
        doc = client.open("Oracle_DB")
        
        return doc
        
    
    except Exception as e:
        # 에러 메시지를 화면에 빨갛게 출력하여 원인을 바로 확인!
        st.error(f"🔥 상세 연결 에러: {e}")
        return None
  
    finally:
        # 4. 앱이 실행된 후 임시 파일 삭제 (cleanup)
        if os.path.exists(temp_file_path):
             os.remove(temp_file_path)

# [중요] 연결 객체(doc)를 미리 만들어 둡니다.
doc = get_connection()

# ---------------------------------------------------------
# 2. 워크시트 정의 (Global Variables)
# ---------------------------------------------------------
# 여기서 정의한 변수명(user_sheet 등)을 아래 함수들이 가져다 씁니다.
# 이렇게 하면 함수마다 매번 시트를 여는 코드를 짤 필요가 없습니다.

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
        
        # [신규] 주간 기록 및 단어 관련 시트 (없으면 에러가 날 수 있으니 시트 생성 필수)
        # 만약 아직 시트를 안 만들었다면 이 부분에서 에러가 날 수 있습니다.
        weekly_history_sheet = doc.worksheet("Weekly_History") 
        # voca_db_sheet = doc.worksheet("Voca_DB")       # 필요 시 주석 해제
        # voca_status_sheet = doc.worksheet("Voca_Status") # 필요 시 주석 해제
        
    except gspread.WorksheetNotFound as e:
        st.error(f"⚠️ 시트를 찾을 수 없습니다: {e}")
        st.stop() # 시트가 없으면 더 이상 진행하지 않음

# ---------------------------------------------------------
# 3. 데이터 조회 함수 (Read)
# ---------------------------------------------------------

# [기존] 데이터 읽기 (캐싱 적용)
@st.cache_data(ttl=60)
def get_data(sheet_name):
    """시트의 모든 데이터를 딕셔너리 리스트로 가져옵니다."""
    try:
        worksheet = doc.worksheet(sheet_name)
        return worksheet.get_all_records()
    except Exception as e:
        st.error(f"데이터 읽기 실패 ({sheet_name}): {e}")
        return []

# [신규] 모든 학생 목록 가져오기 (Admin용)
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
        st.error(f"학생 목록 로딩 에러: {e}")
        return []

# [기존] 특정 학생의 숙제 목록 가져오기 (필터링)
def get_homework_list(student_id):
    try:
        all_hw = homework_list_sheet.get_all_records()
        # 해당 학생의 숙제만 필터링
        my_hw = [h for h in all_hw if str(h['Student_ID']) == str(student_id)]
        return my_hw
    except Exception as e:
        print(f"숙제 목록 로딩 실패: {e}")
        return []

# [신규] 주간 기록 조회 (Dashboard용)
def get_weekly_history(student_id):
    try:
        rows = weekly_history_sheet.get_all_records()
        if not rows:
            return []
        return [r for r in rows if str(r.get("Student_ID")) == str(student_id)]
    except Exception:
        return []

# ---------------------------------------------------------
# 4. 데이터 조작 함수 (Write / Update)
# ---------------------------------------------------------

# [신규] 숙제 배정하기 (Admin용)
def add_homework_assignment(student_id, category, task_name, custom_text, weekly_goal):
    try:
        # 헤더 순서: Student_ID | Category | Task_Name | Custom_Text | Weekly_Goal
        row_data = [student_id, category, task_name, custom_text, weekly_goal]
        homework_list_sheet.append_row(row_data)
        # 데이터가 바뀌었으므로 캐시를 비워줍니다.
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"숙제 배정 실패: {e}")
        return False

# [기존] 숙제 완료 체크 (Log 저장)
def add_homework_log(student_id, task_name, day_of_week):
    try:
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        row = [student_id, task_name, now, day_of_week]
        homework_log_sheet.append_row(row)
        st.cache_data.clear() # 캐시 초기화
    except Exception as e:
        st.error(f"저장 실패: {e}")

# [기존] 숙제 체크 해제 (Log 삭제)
def delete_homework_log(student_id, task_name, day_of_week):
    try:
        # 모든 로그를 가져와서 값만 추출 (헤더 포함)
        logs = homework_log_sheet.get_all_values()
        
        # 역순으로 탐색 (최신 기록부터 삭제해야 안전함)
        for i in range(len(logs) - 1, 0, -1):
            row = logs[i]
            # row[0]=ID, row[1]=Task, row[3]=Day (순서 주의)
            # 엑셀 컬럼 순서: Student_ID | Task_Name | Completed_At | Day_of_Week
            if (str(row[0]) == str(student_id) and 
                str(row[1]) == str(task_name) and 
                str(row[3]) == str(day_of_week)):
                
                homework_log_sheet.delete_rows(i + 1) # 시트 행 번호는 1부터 시작
                st.cache_data.clear()
                return True
        return False
    except Exception as e:
        st.error(f"삭제 실패: {e}")
        return False

# [관리] 오래된 로그 정리 (Admin용 - 필요 시 사용)
def archive_old_logs():
    # 현재는 기능만 정의해두고 나중에 구현
    return 0
# modules/db.py 맨 아래에 추가해주세요.

def reset_student_homework(student_id):
    """
    특정 학생의 기존 숙제 목록을 모두 삭제합니다. (새 숙제 배정 전 초기화용)
    """
    try:
        # 1. 모든 데이터를 읽어옵니다.
        all_rows = homework_list_sheet.get_all_values()
        
        # 2. 헤더(첫 줄)는 남기고, 해당 학생(student_id)이 '아닌' 데이터만 남깁니다.
        # 즉, 내 것만 빼고 나머지는 유지하는 방식입니다.
        header = all_rows[0]
        data_rows = all_rows[1:]
        
        # 필터링: ID가 다른 사람의 데이터만 keep
        new_rows = [row for row in data_rows if str(row[0]) != str(student_id)]
        
        # 3. 시트를 싹 지우고 다시 씁니다.
        homework_list_sheet.clear()
        homework_list_sheet.append_row(header) # 헤더 다시 쓰기
        if new_rows:
            homework_list_sheet.append_rows(new_rows) # 남은 데이터 다시 쓰기
            
        return True
    except Exception as e:
        print(f"숙제 초기화 실패: {e}")
        return False