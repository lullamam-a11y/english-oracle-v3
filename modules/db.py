# modules/db.py (최종: 자동 보정 + 모든 CRUD 기능 + 데이터 대청소 포함)

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import pytz 
import re 

# ---------------------------------------------------------
# 1. 키 자동 보정 함수 (Incorrect Padding 해결사)
# ---------------------------------------------------------
def fix_private_key(key):
    try:
        key = key.strip()
        if "\\n" in key:
            key = key.replace("\\n", "\n")
        if "-----BEGIN PRIVATE KEY-----" in key:
            clean_body = key.replace("-----BEGIN PRIVATE KEY-----", "") \
                            .replace("-----END PRIVATE KEY-----", "")
        else:
            clean_body = key 
        clean_body = re.sub(r"\s+", "", clean_body)
        fixed_key = f"-----BEGIN PRIVATE KEY-----\n{clean_body}\n-----END PRIVATE KEY-----"
        return fixed_key
    except Exception:
        return key

# ---------------------------------------------------------
# 2. 구글 시트 연결 및 인증
# ---------------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
def get_connection():
    try:
        if "gcp_service_account" not in st.secrets:
            return None
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        if "private_key" in creds_dict:
            raw_key = creds_dict["private_key"]
            creds_dict["private_key"] = fix_private_key(raw_key)
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        doc = client.open("Oracle_DB") 
        return doc
    except Exception as e:
        print(f"DB Connection Error: {e}")
        return None

doc = get_connection()

# ---------------------------------------------------------
# 3. 워크시트 정의
# ---------------------------------------------------------
if doc:
    try:
        user_sheet = doc.worksheet("Users")
        homework_list_sheet = doc.worksheet("Homework_List")
        homework_log_sheet = doc.worksheet("Homework_Log")
        exam_results_sheet = doc.worksheet("Exam_Results")
        weekly_history_sheet = doc.worksheet("Weekly_History")
        # [누락 방지] 아카이브 시트도 정의 (없으면 생성 시도 로직은 생략, 수동 생성 권장)
        try:
            log_archive_sheet = doc.worksheet("Log_Archive")
        except:
            log_archive_sheet = None
    except:
        user_sheet = None
else:
    user_sheet = None
    homework_list_sheet = None
    homework_log_sheet = None
    exam_results_sheet = None
    weekly_history_sheet = None
    log_archive_sheet = None

# ---------------------------------------------------------
# 4. 데이터 조회/조작 함수들
# ---------------------------------------------------------

def get_data(sheet_name):
    if doc is None: return []
    try:
        return doc.worksheet(sheet_name).get_all_records()
    except: return []

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

# ---------------------------------------------------------
# [복구된 기능] 데이터 대청소 함수 (archive_old_logs)
# ---------------------------------------------------------
def archive_old_logs(days=30):
    """
    30일 지난 로그를 Log_Archive 시트로 이동
    """
    if doc is None: return "DB 연결 실패"
    
    try:
        # 시트 재확인
        try:
            log_sheet = doc.worksheet("Homework_Log")
            archive_sheet = doc.worksheet("Log_Archive")
        except:
            return "❌ 필수 시트(Homework_Log 또는 Log_Archive)가 없습니다."

        all_logs = log_sheet.get_all_values()
        if len(all_logs) <= 1: return "데이터 없음"
        
        header = all_logs[0]
        data_rows = all_logs[1:]
        
        kst = pytz.timezone('Asia/Seoul')
        cutoff_date = datetime.now(kst) - pd.Timedelta(days=days)
        
        rows_to_archive = []
        rows_to_keep = []
        
        for row in data_rows:
            try:
                # 날짜 컬럼(C열, index 2) 확인
                if len(row) > 2:
                    log_date_str = row[2] 
                    log_date = datetime.strptime(log_date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=kst)
                    
                    if log_date < cutoff_date:
                        rows_to_archive.append(row)
                    else:
                        rows_to_keep.append(row)
                else:
                    rows_to_keep.append(row) # 데이터 불완전 시 보존
            except:
                rows_to_keep.append(row) # 날짜 파싱 실패 시 보존
        
        if rows_to_archive:
            archive_sheet.append_rows(rows_to_archive)
            log_sheet.clear()
            log_sheet.append_row(header)
            if rows_to_keep:
                log_sheet.append_rows(rows_to_keep)
            
            st.cache_data.clear() # 캐시 초기화
            return f"✅ {len(rows_to_archive)}개의 기록을 정리했습니다."
        else:
            return "🧹 정리할 데이터가 없습니다."
            
    except Exception as e:
        return f"❌ 아카이빙 실패: {str(e)}"
