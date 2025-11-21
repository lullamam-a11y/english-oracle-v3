# modules/dashboard.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from modules import db

# [보조 함수] 이번 주 월요일 09:00 계산
def get_week_start():
    now = datetime.now()
    today_weekday = now.weekday() # 0:월 ~ 6:일
    if today_weekday == 0 and now.hour < 9:
        days_to_subtract = 7
    else:
        days_to_subtract = today_weekday
    last_monday = now - timedelta(days=days_to_subtract)
    return last_monday.replace(hour=9, minute=0, second=0, microsecond=0)

def show_dashboard():
    # 1. 사용자 체크
    if "user_id" not in st.session_state:
        st.warning("로그인이 필요합니다.")
        return

    user_id = st.session_state["user_id"]
    user_name = st.session_state["user_name"]
    
    # 2. 데이터 로딩
    hw_list = db.get_data("Homework_List")
    log_data = db.get_data("Homework_Log")
    exam_data = db.get_data("Exam_Results")
    users_data = db.get_data("Users")
    history_data = db.get_weekly_history(user_id) # 과거 박제된 데이터
    
    if not hw_list:
        st.info("등록된 숙제가 없습니다.")
        return

    df_hw = pd.DataFrame(hw_list)
    df_log = pd.DataFrame(log_data) if log_data else pd.DataFrame()
    df_exam = pd.DataFrame(exam_data) if exam_data else pd.DataFrame()
    df_history = pd.DataFrame(history_data) if history_data else pd.DataFrame()
    df_users = pd.DataFrame(users_data)

    my_missions = df_hw[df_hw["Student_ID"].astype(str) == str(user_id)]
    if my_missions.empty:
        st.warning("할당된 숙제가 없습니다.")
        return

    # 가입일(Start_Date) 확인 - 단순 표시용
    start_date_str = "-"
    try:
        user_row = df_users[df_users["Student_ID"].astype(str) == str(user_id)]
        if not user_row.empty:
            start_date_str = user_row.iloc[0]["Start_Date"]
    except: pass

    st.markdown(f"## 📊 {user_name}의 숙제 현황")
    st.caption(f"Start Date: {start_date_str} ~ Current")
    st.divider()

    # ---------------------------------------------------------
    # [Logic] 통계 집계 (History Sum + Current)
    # ---------------------------------------------------------
    stats = {}
    week_start = get_week_start()

    # [Step 1] 과거 기록(History) 합산 (순수하게 DB에 있는 것만 더함)
    if not df_history.empty:
        for _, h_row in df_history.iterrows():
            cat = h_row.get("Category")
            try:
                h_goal = int(h_row.get("Goal_Snapshot"))
                h_done = int(h_row.get("Done_Snapshot"))
            except:
                h_goal, h_done = 0, 0
                
            if cat not in stats:
                stats[cat] = {'weekly_goal':0, 'weekly_done':0, 'total_goal':0, 'total_done':0}
            
            stats[cat]['total_goal'] += h_goal
            stats[cat]['total_done'] += h_done

    # [Step 2] 이번 주(Current) 실시간 데이터 계산 및 합산
    for _, row in my_missions.iterrows():
        category = row["Category"]
        task_name = row["Task_Name"]
        custom_text = row["Custom_Text"]
        
        try:
            weekly_goal = int(row.get("Weekly_Goal")) if row.get("Weekly_Goal") else 1
        except: weekly_goal = 1
            
        if category not in stats:
            stats[category] = {'weekly_goal':0, 'weekly_done':0, 'total_goal':0, 'total_done':0}
            
        # 주간 목표 설정
        stats[category]['weekly_goal'] += weekly_goal
        # [핵심 수정] 누적 목표에 '이번 주 목표'를 더함 (경과 주수 곱하기 삭제!)
        stats[category]['total_goal'] += weekly_goal
        
        # Done 계산 (이번 주)
        current_done_count = 0
        
        is_exam = ("시험" in category) or ("Test" in category) or ("시험" in task_name)
        
        if is_exam and not df_exam.empty:
            my_exams = df_exam[(df_exam["Student_ID"].astype(str) == str(user_id)) & 
                               (df_exam["Range"].astype(str) == str(custom_text))]
            for _, e_row in my_exams.iterrows():
                try:
                    e_date = datetime.strptime(str(e_row["Date"]), "%Y-%m-%d")
                    # 이번 주 데이터만 카운트 (과거는 History에 있으므로)
                    if e_date.date() >= week_start.date():
                        current_done_count += 1
                except: continue
                
        elif not is_exam and not df_log.empty:
            full_name = f"{task_name} ({custom_text})"
            my_logs = df_log[(df_log["Student_ID"].astype(str) == str(user_id)) & 
                             (df_log["Task_Name"] == full_name)]
            for _, l_row in my_logs.iterrows():
                try:
                    l_date = datetime.strptime(str(l_row["Completed_At"]), "%Y-%m-%d %H:%M:%S")
                    if l_date >= week_start:
                        current_done_count += 1
                except: continue
        
        stats[category]['weekly_done'] += current_done_count
        stats[category]['total_done'] += current_done_count

    # ---------------------------------------------------------
    # [Visual] 시각화
    # ---------------------------------------------------------
    categories = list(stats.keys())
    
    # [Part 1] Weekly Radar (금주의 밸런스)
    st.subheader("🕸️ 주간 숙제 현황")
    if categories:
        r_goals = [1.0] * len(categories)
        r_dones = []
        for c in categories:
            g = stats[c]['weekly_goal']
            d = stats[c]['weekly_done']
            ratio = d/g if g>0 else 0
            r_dones.append(min(ratio, 1.1))

        cats_closed = categories + [categories[0]]
        r_goals_closed = r_goals + [r_goals[0]]
        r_dones_closed = r_dones + [r_dones[0]]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=r_goals_closed, theta=cats_closed, fill='toself',
            name='Goal', line=dict(color='#CFD8DC', dash='dot'), hoverinfo='skip'))
        fig.add_trace(go.Scatterpolar(r=r_dones_closed, theta=cats_closed, fill='toself',
            name='Progress', line=dict(color='#3498DB'), fillcolor='rgba(52, 152, 219, 0.6)'))
        
        fig.update_layout(polar=dict(radialaxis=dict(visible=False, range=[0, 1.1])), 
                          showlegend=False, height=300, margin=dict(l=30, r=30, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
        
        # 주간 요약 텍스트
        cols = st.columns(len(categories))
        for idx, cat in enumerate(categories):
            g = stats[cat]['weekly_goal']
            d = stats[cat]['weekly_done']
            p = int((d/g)*100) if g>0 else 0
            with cols[idx]:
                st.markdown(f"<div style='text-align:center; font-size:0.8rem;'>{cat}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:center; font-weight:bold;'>{p}%</div>", unsafe_allow_html=True)
    
    st.divider()
    
    # [Part 2] Total Accumulation (순수 누적)
    st.subheader("📚 누적 숙제 현황")
    st.caption("누적 학습량 = (지난주까지의 확정 기록) + (이번 주 실시간 기록)")
    st.write("")
    
    for cat in categories:
        t_goal = stats[cat]['total_goal']
        t_done = stats[cat]['total_done']
        t_rate = t_done / t_goal if t_goal > 0 else 0
        
        # 목표 달성 여부에 따른 색상
        status_color = "#3498DB" # 기본 파랑
        if t_rate >= 1.0: status_color = "#2ECC71" # 달성 시 초록
        
        st.markdown(f"""
        <div style="margin-bottom:5px;">
            <span style="font-weight:bold;">{cat}</span>
            <span style="float:right; font-size:0.9rem; color:#546E7A;">
                <b>{t_done}</b> / {t_goal} <span style="color:{status_color}">({int(t_rate*100)}%)</span>
            </span>
        </div>
        """, unsafe_allow_html=True)
        
        bar_fill = "linear-gradient(90deg, #3498DB, #8E44AD)"
        if t_rate >= 1.0: bar_fill = "linear-gradient(90deg, #11998e, #38ef7d)"
        
        st.markdown(f"""
        <div style="background:#ECEFF1; border-radius:10px; height:12px; width:100%;">
            <div style="background:{bar_fill}; width:{min(t_rate*100, 100)}%; height:100%; border-radius:10px;"></div>
        </div>
        <div style="margin-bottom:15px;"></div>
        """, unsafe_allow_html=True)