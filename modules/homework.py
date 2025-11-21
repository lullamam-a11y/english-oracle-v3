# modules/homework.py (Speed Optimized & Feature Complete)

import streamlit as st
import pandas as pd
import pytz 
from datetime import datetime, timedelta
from modules import db

# ---------------------------------------------------------
# [Helper] 데이터 로딩 최적화 (Session State Caching)
# ---------------------------------------------------------
def load_data_to_session(user_id, reset_time_naive):
    """
    매번 DB를 읽지 않고, 세션에 데이터가 없거나 강제 갱신이 필요할 때만 DB를 읽습니다.
    """
    # 1. 숙제 목록 (Homework_List) - 잘 안 바뀌므로 세션에 저장
    if "my_hw_list" not in st.session_state:
        raw_hw = db.get_data("Homework_List") # DB에서 읽기
        if raw_hw:
            df = pd.DataFrame(raw_hw)
            # 내 숙제만 필터링하여 저장
            st.session_state["my_hw_list"] = df[df["Student_ID"].astype(str) == str(user_id)]
        else:
            st.session_state["my_hw_list"] = pd.DataFrame()

    # 2. 수행 기록 (Homework_Log) - 체크할 때마다 로컬 업데이트 + DB 백그라운드 전송 효과
    if "my_done_map" not in st.session_state:
        # 처음 한 번만 DB에서 읽어와서 '세트(Set)'로 만듦
        raw_log = db.get_data("Homework_Log")
        done_set = set()
        task_cnt = {}
        
        if raw_log:
            df_log = pd.DataFrame(raw_log)
            # 내 기록만 필터링
            my_logs = df_log[df_log["Student_ID"].astype(str) == str(user_id)]
            
            for _, row in my_logs.iterrows():
                try:
                    # 문자열을 날짜로 변환하여 이번 주 기록인지 확인
                    completed_at_str = str(row.get("Completed_At"))
                    completed_at = datetime.strptime(completed_at_str, "%Y-%m-%d %H:%M:%S")
                    
                    if completed_at >= reset_time_naive:
                        t_name = row.get("Task_Name")
                        day = row.get("Day_of_Week")
                        done_set.add((t_name, day))
                        task_cnt[t_name] = task_cnt.get(t_name, 0) + 1
                except: continue
        
        st.session_state["my_done_map"] = done_set
        st.session_state["my_task_counts"] = task_cnt

    # 3. 시험 결과 (Exam_Results) - 시험 칠 때만 갱신
    if "my_exam_results" not in st.session_state:
        raw_exam = db.get_data("Exam_Results")
        st.session_state["my_exam_results"] = pd.DataFrame(raw_exam) if raw_exam else pd.DataFrame()

# ---------------------------------------------------------
# [Core] 날짜 및 유령 주간 계산
# ---------------------------------------------------------
def get_current_week_start():
    KST = pytz.timezone('Asia/Seoul')
    now = datetime.now(KST) 
    today_weekday = now.weekday()
    
    if today_weekday == 0 and now.hour < 9:
        days_to_subtract = 7
    else:
        days_to_subtract = today_weekday
        
    last_monday = now - timedelta(days=days_to_subtract)
    return last_monday.replace(hour=9, minute=0, second=0, microsecond=0)

def check_and_archive_missing_weeks(user_id):
    """
    마지막으로 저장된 History 날짜를 찾아, 
    그 이후부터 이번 주 전까지 비어있는 모든 주(Week)를 순차적으로 마감함.
    """
    # 1. 기준점 설정
    this_monday = get_current_week_start()
    this_monday_naive = this_monday.replace(tzinfo=None)
    
    # 2. 사용자 정보에서 시작일 찾기
    start_monday = this_monday_naive 
    try:
        users_data = db.get_data("Users")
        df_users = pd.DataFrame(users_data)
        u_row = df_users[df_users["Student_ID"].astype(str) == str(user_id)]
        if not u_row.empty:
            s_date_val = u_row.iloc[0]["Start_Date"]
            if s_date_val and str(s_date_val).strip() != "":
                start_dt = datetime.strptime(str(s_date_val), "%Y-%m-%d")
                calc_start = start_dt - timedelta(days=start_dt.weekday())
                start_monday = calc_start.replace(hour=9, minute=0, second=0, microsecond=0)
    except:
        start_monday = this_monday_naive

    # 3. History 확인
    history_data = db.get_weekly_history(user_id)
    last_archived_date = None
    if history_data:
        dates = []
        for r in history_data:
            try: dates.append(datetime.strptime(r["Week_Start_Date"], "%Y-%m-%d"))
            except: continue
        if dates:
            last_archived_date = max(dates).replace(hour=9, minute=0, second=0, microsecond=0)

    # 4. 추적 시작점 결정
    if last_archived_date:
        next_check_date = last_archived_date + timedelta(days=7)
    else:
        next_check_date = start_monday

    # 5. 루프 실행 (업데이트가 필요한 경우에만 True 반환)
    if next_check_date.date() < this_monday_naive.date():
        hw_list = db.get_data("Homework_List")
        log_data = db.get_data("Homework_Log")
        exam_data = db.get_data("Exam_Results")
        
        df_hw = pd.DataFrame(hw_list)
        df_log = pd.DataFrame(log_data) if log_data else pd.DataFrame()
        df_exam = pd.DataFrame(exam_data) if exam_data else pd.DataFrame()
        
        my_missions = df_hw[df_hw["Student_ID"].astype(str) == str(user_id)]
        rows_to_insert = []

        while next_check_date.date() < this_monday_naive.date():
            week_start = next_check_date
            week_end = week_start + timedelta(days=7)
            week_start_str = week_start.strftime("%Y-%m-%d")
            
            archive_stats = {} 
            if not my_missions.empty:
                for _, row in my_missions.iterrows():
                    cat = row["Category"]
                    task = row["Task_Name"]
                    custom = row["Custom_Text"]
                    try: goal = int(row.get("Weekly_Goal")) if row.get("Weekly_Goal") else 1
                    except: goal = 1
                        
                    if cat not in archive_stats: archive_stats[cat] = {'goal': 0, 'done': 0}
                    archive_stats[cat]['goal'] += goal
                    
                    is_exam = ("시험" in cat) or ("Test" in cat) or ("시험" in task)
                    if is_exam and not df_exam.empty:
                        my_exams = df_exam[(df_exam["Student_ID"].astype(str) == str(user_id)) & (df_exam["Range"].astype(str) == str(custom))]
                        for _, r in my_exams.iterrows():
                            try:
                                d_date = datetime.strptime(str(r["Date"]), "%Y-%m-%d")
                                if week_start.date() <= d_date.date() < week_end.date():
                                    archive_stats[cat]['done'] += 1
                            except: continue
                    elif not is_exam and not df_log.empty:
                        full_name = f"{task} ({custom})"
                        my_logs = df_log[(df_log["Student_ID"].astype(str) == str(user_id)) & (df_log["Task_Name"] == full_name)]
                        for _, r in my_logs.iterrows():
                            try:
                                l_date = datetime.strptime(str(r["Completed_At"]), "%Y-%m-%d %H:%M:%S")
                                if week_start <= l_date < week_end:
                                    archive_stats[cat]['done'] += 1
                            except: continue
            
            for cat, stat in archive_stats.items():
                rows_to_insert.append([str(user_id), week_start_str, cat, stat['goal'], stat['done']])
            next_check_date += timedelta(days=7)
        
        if rows_to_insert:
            db.add_weekly_history(rows_to_insert)
            return True
    return False


# ---------------------------------------------------------
# [Action] 체크박스 클릭 핸들러 (Optimistic Update)
# ---------------------------------------------------------
def toggle_status(user_id, task_name, day, current_status):
    """
    체크박스를 클릭했을 때 실행되는 콜백 함수입니다.
    DB에 저장을 요청함과 동시에 세션(화면) 데이터를 즉시 수정하여 반응 속도를 높입니다.
    """
    # 1. DB 업데이트 (가장 느림 - 백그라운드처럼 처리)
    if not current_status:
        db.add_homework_log(user_id, task_name, day)
        # 2. 세션 상태 즉시 업데이트 (화면 갱신용)
        st.session_state["my_done_map"].add((task_name, day))
        st.toast(f"👍 [{day}] 완료!")
    else:
        db.delete_homework_log(user_id, task_name, day)
        # 2. 세션 상태 즉시 업데이트
        if (task_name, day) in st.session_state["my_done_map"]:
            st.session_state["my_done_map"].remove((task_name, day))
        st.toast(f"↩️ [{day}] 취소")
    
    # 3. 카운트 재계산 (그래프/텍스트 갱신용)
    new_count = 0
    for (t, d) in st.session_state["my_done_map"]:
        if t == task_name: new_count += 1
    st.session_state["my_task_counts"][task_name] = new_count


# ---------------------------------------------------------
# [Main] 화면 출력
# ---------------------------------------------------------
def show_tracker():
    user_id = st.session_state.get("student_id") or st.session_state.get("user_id")
    if not user_id:
        st.error("로그인이 필요합니다.")
        return

    reset_time = get_current_week_start()
    reset_time_naive = reset_time.replace(tzinfo=None)

    # 1. [Heavy Task] 유령 주간 체크 (세션당 1회만 수행)
    if "history_checked" not in st.session_state:
        with st.spinner("데이터 동기화 중..."):
            updated = check_and_archive_missing_weeks(user_id)
            st.session_state["history_checked"] = True
            if updated:
                st.toast("✅ 지난 학습 기록이 동기화되었습니다.")

    # 2. [Optimized Task] 데이터 로드 (세션 캐시 활용)
    load_data_to_session(user_id, reset_time_naive)

    # 3. UI 그리기
    reset_str = reset_time.strftime("%m월 %d일")
    st.markdown(f"""
        <h3 style='color:#2C3E50; margin-bottom:0px;'>주간 체크리스트</h3>
        <p style='color:#7F8C8D; font-size:0.9rem; margin-top:5px;'>
            🔄 매주 월요일 09:00 자동 초기화 (기준: {reset_str} 09:00 이후)
        </p>
    """, unsafe_allow_html=True)
    st.write("") 

    # 세션에서 데이터 가져오기 (DB 직접 조회 X)
    my_missions = st.session_state["my_hw_list"]
    done_map = st.session_state["my_done_map"]
    task_counts = st.session_state["my_task_counts"]
    df_exam = st.session_state["my_exam_results"]

    if my_missions.empty:
        st.info("할당된 숙제가 없습니다.")
        return

    # 시험/루틴 분리
    is_exam = (my_missions["Category"].str.contains("시험|Test", case=False, na=False)) | \
              (my_missions["Task_Name"].str.contains("시험|Test", case=False, na=False))
    
    exam_missions = my_missions[is_exam]
    routine_missions = my_missions[~is_exam]

    # [Section 1] 시험 결과 (읽기 전용)
    if not exam_missions.empty:
        st.markdown("##### 🏆 단어 시험 결과")
        cols = st.columns(2)
        for idx, (_, row) in enumerate(exam_missions.iterrows()):
            col_idx = idx % 2
            custom = row["Custom_Text"]
            task = row["Task_Name"]
            try: goal = int(row.get("Weekly_Goal", 1))
            except: goal = 1
            
            # 시험 점수 매칭
            valid_matches = []
            if not df_exam.empty:
                match = df_exam[(df_exam["Student_ID"].astype(str) == str(user_id)) & 
                                (df_exam["Range"].astype(str) == str(custom))]
                for _, r in match.iterrows():
                    try:
                        if datetime.strptime(str(r["Date"]), "%Y-%m-%d").date() >= reset_time_naive.date():
                            valid_matches.append(r)
                    except: pass
            
            valid_matches.sort(key=lambda x: x['Date'])
            
            # (UI 렌더링: 코드 길이상 핵심 부분만 유지)
            exam_cnt = len(valid_matches)
            header_html = f"""<div style="display:flex; justify-content:space-between;"><div class="score-label" style="font-size:0.8rem; color:#546E7A;">{task}</div><span style='font-size:0.8rem; color:#546E7A; margin-left:5px;'>({exam_cnt} / {goal}회)</span></div>"""
            
            score_html = """<div style="font-size:1.5rem; color:#B0BEC5; font-weight:800;">- %</div>"""
            if goal == 1:
                if valid_matches:
                    last_score = valid_matches[-1]['Score']
                    color = "#43A047" if int(last_score) >= 90 else "#E53935"
                    score_html = f"""<div style="font-size:1.5rem; color:{color}; font-weight:800;">{last_score}%</div>"""
                content_html = header_html + score_html
            else:
                # 리스트 형태 표시
                list_html = "<div style='margin-top:8px; display:flex; flex-direction:column; gap:4px;'>"
                for i in range(goal):
                    nth = i + 1
                    if i < exam_cnt:
                        rec = valid_matches[i]
                        sc, dt = rec['Score'], rec['Date']
                        c = "#43A047" if int(sc) >= 90 else "#E53935"
                        list_html += f"""<div style="display:flex; justify-content:space-between; align-items:center; background:#F8F9FA; padding:4px 8px; border-radius:4px;"><span style="font-size:0.75rem; color:#546E7A;">#{nth}</span><span style="font-size:0.9rem; color:{c}; font-weight:800;">{sc}%</span></div>"""
                    else:
                        list_html += f"""<div style="display:flex; justify-content:space-between; align-items:center; border:1px dashed #ECEFF1; padding:4px 8px; border-radius:4px;"><span style="font-size:0.75rem; color:#CFD8DC;">#{nth}</span><span style="font-size:0.8rem; color:#CFD8DC;">-</span></div>"""
                list_html += "</div>"
                content_html = header_html + list_html

            with cols[col_idx]:
                st.markdown(f"""<div class="score-card-container" style="min-height:80px;">{content_html}</div>""", unsafe_allow_html=True)

    # [Section 2] 루틴 체크리스트 (속도 최적화 핵심)
    if not routine_missions.empty:
        st.write("")
        st.markdown("##### ✅ Checklist")
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        for index, row in routine_missions.iterrows():
            task_name = row["Task_Name"]
            custom_text = row["Custom_Text"]
            category = row["Category"]
            full_task_name = f"{task_name} ({custom_text})"
            
            try: goal = int(row.get("Weekly_Goal", 7))
            except: goal = 7
            
            # 세션에서 카운트 조회 (DB 재조회 X)
            current = task_counts.get(full_task_name, 0)
            progress_text = f"({current} / {goal}회)"
            progress_color = "#43A047" if current >= goal else "#78909C"

            with st.container(border=True):
                st.markdown(f"""
                    <div style="display:flex; justify-content:space-between;">
                        <div>
                            <span class="badge-category">{category}</span>
                            <span class="task-title" style="margin-left:5px;">{task_name}</span>
                            <div class="task-desc">{custom_text} <span style="color:{progress_color}; font-weight:bold;">{progress_text}</span></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                d_cols = st.columns(7)
                for i, day in enumerate(days):
                    # 세션 맵에서 상태 확인 (초고속)
                    is_done = (full_task_name, day) in done_map
                    
                    # [중요] on_change 콜백 사용
                    # 버튼을 누르면 DB 업데이트 후 -> 세션 업데이트 -> 화면 리프레시
                    with d_cols[i]:
                        st.checkbox(
                            day, 
                            value=is_done, 
                            key=f"chk_{index}_{day}",
                            on_change=toggle_status,
                            args=(user_id, full_task_name, day, is_done)
                        )