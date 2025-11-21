# modules/admin.py (최종: 전체 학생 한눈에 보기 기능 탑재)

import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import pytz
from modules import db

# [Helper] 이번 주 기준 날짜 계산 (월요일 09:00)
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

def show_admin_page():
    st.title("👑 Administrator Hub")
    
    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["📚 숙제 일괄 배정", "🧹 데이터 관리", "📊 전체 이행 현황"])

    # ------------------------------------------------------------------
    # Tab 1: 숙제 일괄 배정 (Batch Assignment) - 기존 유지
    # ------------------------------------------------------------------
    with tab1:
        st.subheader("🚀 학생별 숙제 일괄 배정")
        
        student_list = db.get_all_users()
        if not student_list:
            st.error("등록된 학생이 없습니다. Users 시트에 학생을 등록해주세요.")
            return

        col_sel, col_btn = st.columns([3, 1])
        with col_sel:
            selected_student_raw_t1 = st.selectbox("학생 선택", student_list, key="sel_student_t1")
            selected_student_id_t1 = selected_student_raw_t1.split(' (')[0]
        
        st.divider()

        default_data = [
            {"선택": False, "영역": "듣기", "숙제명": "백지 딕테이션", "비고/범위": "20분 내외", "주간목표": 2},
            {"선택": False, "영역": "문법", "숙제명": "문법 교재", "비고/범위": "복습", "주간목표": 2},
            {"선택": False, "영역": "단어", "숙제명": "단어 암기", "비고/범위": "001~100", "주간목표": 5},
            {"선택": False, "영역": "단어", "숙제명": "단어 시험", "비고/범위": "001~100", "주간목표": 2},
            {"선택": False, "영역": "모의고사", "숙제명": "모의고사 (65분)", "비고/범위": "고3 1회", "주간목표": 1},
            {"선택": False, "영역": "모의고사", "숙제명": "변형문제", "비고/범위": "수업분", "주간목표": 1},
            {"선택": False, "영역": "모의고사", "숙제명": "구문독해", "비고/범위": "수업분", "주간목표": 1},
            {"선택": False, "영역": "모의고사", "숙제명": "구조화", "비고/범위": "수업분", "주간목표": 1},
        ]

        current_assignments = db.get_homework_list(selected_student_id_t1)
        
        current_map = {}
        if current_assignments:
            for item in current_assignments:
                key = (item['Category'], item['Task_Name'])
                current_map[key] = item
        
        final_data = []
        
        for row in default_data:
            key = (row['영역'], row['숙제명'])
            if key in current_map:
                saved = current_map[key]
                row['선택'] = True
                row['비고/범위'] = saved['Custom_Text']
                try: row['주간목표'] = int(saved['Weekly_Goal'])
                except: row['주간목표'] = 1
                del current_map[key]
            final_data.append(row)
        
        for key, saved in current_map.items():
            new_row = {
                "선택": True,
                "영역": saved['Category'],
                "숙제명": saved['Task_Name'],
                "비고/범위": saved['Custom_Text'],
                "주간목표": int(saved['Weekly_Goal']) if saved['Weekly_Goal'] else 1
            }
            final_data.append(new_row)

        df_template = pd.DataFrame(final_data)

        st.info(f"👇 **{selected_student_raw_t1}** 학생의 현재 설정된 숙제입니다. 내용을 수정하고 저장하세요.")
        st.caption("💡 지난주에 배정한 내용(범위, 목표)을 자동으로 불러왔습니다.")

        edited_df = st.data_editor(
            df_template,
            column_config={
                "선택": st.column_config.CheckboxColumn("선택", default=False),
                "주간목표": st.column_config.NumberColumn("목표(회)", min_value=1, max_value=7, step=1),
            },
            disabled=["영역", "숙제명"], 
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic"
        )

        if st.button("수정된 내용으로 저장 (Overwrite) 🚀", type="primary"):
            selected_rows = edited_df[edited_df["선택"] == True]
            
            with st.spinner(f"💾 {selected_student_raw_t1} 학생의 숙제 데이터를 갱신 중..."):
                if not db.reset_student_homework(selected_student_id_t1):
                    st.error("기존 숙제 삭제 중 오류가 발생했습니다. DB 연결을 확인해주세요.")
                    st.stop()
            
            success_count = 0
            fail_count = 0
            total = len(selected_rows)
            
            if total > 0:
                progress_text = st.empty()
                bar = st.progress(0)
                
                for idx, row in selected_rows.iterrows():
                    cat = row["영역"]
                    task = row["숙제명"]
                    custom = row["비고/범위"]
                    goal = row["주간목표"]
                    progress_text.text(f"📤 저장 중... [{task}]")
                    
                    if db.add_homework_assignment(selected_student_id_t1, cat, task, custom, int(goal)):
                        success_count += 1
                    else:
                        fail_count += 1
                    bar.progress((success_count + fail_count) / total)
                
                bar.empty()
                progress_text.empty()
            
            if fail_count == 0:
                st.success(f"✅ {selected_student_raw_t1} 학생의 숙제가 최신 상태로 **저장**되었습니다!")
                time.sleep(1) 
                st.rerun()
            else:
                st.warning(f"⚠️ {success_count}건 성공, {fail_count}건 실패.")

    # ------------------------------------------------------------------
    # Tab 2: 데이터 관리
    # ------------------------------------------------------------------
    with tab2:
        st.subheader("시스템 데이터 관리")
        st.warning("⚠️ 주의: 데이터 삭제는 복구할 수 없습니다.")
        if st.button("🧹 오래된 로그 정리 (30일 이상)"):
            removed_count = db.archive_old_logs()
            st.success(f"{removed_count}개의 오래된 기록을 Archive로 이동했습니다.")

    # ------------------------------------------------------------------
    # Tab 3: 전체 학생 이행 현황 (All-in-One View)
    # ------------------------------------------------------------------
    with tab3:
        st.subheader("📊 전체 학생 주간 이행 현황 (Dashboard)")
        st.caption(f"기준 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (실시간)")

        if st.button("전체 현황 새로고침 🔄", type="primary", use_container_width=True):
            with st.spinner("모든 학생의 데이터를 분석 중입니다..."):
                
                # 1. [Optimization] DB 통신 최소화: 모든 데이터를 한 번에 가져옴
                all_users = db.get_all_users() # ["id (name)", ...]
                raw_hw = db.get_data("Homework_List")
                raw_log = db.get_data("Homework_Log")
                
                # Pandas DataFrame으로 변환 (필터링 속도 향상)
                df_hw_all = pd.DataFrame(raw_hw) if raw_hw else pd.DataFrame()
                df_log_all = pd.DataFrame(raw_log) if raw_log else pd.DataFrame()
                
                week_start = get_current_week_start()
                week_start_naive = week_start.replace(tzinfo=None)
                days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

                # 2. 학생별 반복 처리
                for student_str in all_users:
                    student_id = student_str.split(' (')[0]
                    student_name = student_str.split(' (')[1].replace(')', '')
                    
                    # A. 내 숙제 필터링
                    if df_hw_all.empty:
                        my_hw_rows = pd.DataFrame()
                    else:
                        my_hw_rows = df_hw_all[df_hw_all["Student_ID"].astype(str) == str(student_id)]
                    
                    if my_hw_rows.empty:
                        # 숙제가 없는 학생은 스킵하거나 별도 표시
                        with st.expander(f"⚪ {student_name} ({student_id}) - 배정된 숙제 없음"):
                            st.info("아직 숙제가 배정되지 않았습니다.")
                        continue

                    # B. 내 로그 필터링 (이번 주 기록만)
                    my_done_set = set()
                    if not df_log_all.empty:
                        my_logs = df_log_all[df_log_all["Student_ID"].astype(str) == str(student_id)]
                        for _, row in my_logs.iterrows():
                            try:
                                completed_at = datetime.strptime(str(row.get("Completed_At")), "%Y-%m-%d %H:%M:%S")
                                if completed_at >= week_start_naive:
                                    my_done_set.add((row.get("Task_Name"), row.get("Day_of_Week")))
                            except: continue
                    
                    # C. 통계 계산
                    total_goal = 0
                    total_done = 0
                    status_data = []
                    
                    for _, hw in my_hw_rows.iterrows():
                        task = hw['Task_Name']
                        custom = hw['Custom_Text']
                        full_name = f"{task} ({custom})"
                        
                        try: goal = int(hw['Weekly_Goal'])
                        except: goal = 1
                        
                        # 개별 숙제 수행 카운트
                        done_count = 0
                        day_marks = {}
                        for d in days:
                            if (full_name, d) in my_done_set:
                                day_marks[d] = "✅"
                                done_count += 1
                            else:
                                day_marks[d] = ""
                        
                        total_goal += goal
                        total_done += min(done_count, goal) # 100% 초과 방지
                        
                        progress_pct = min(int((done_count / goal) * 100), 100)
                        
                        row_data = {
                            "영역": hw['Category'],
                            "숙제명": full_name,
                            "진척도": f"{done_count}/{goal}",
                            "달성률": progress_pct # 숫자만 넣어서 bar chart 활용
                        }
                        row_data.update(day_marks)
                        status_data.append(row_data)

                    # D. UI 렌더링 (Expandable Card)
                    # 전체 달성률 계산
                    final_percent = 0
                    if total_goal > 0:
                        final_percent = int((total_done / total_goal) * 100)
                    
                    # 상태에 따른 이모지/색상
                    if final_percent >= 100: icon = "🏆"
                    elif final_percent >= 80: icon = "🔥"
                    elif final_percent >= 50: icon = "🏃"
                    else: icon = "⚠️"
                    
                    label = f"{icon} {student_name} ({student_id}) : 종합 달성률 {final_percent}%"
                    
                    with st.expander(label, expanded=False):
                        # 상단 프로그레스 바
                        st.progress(min(final_percent / 100, 1.0))
                        
                        # 상세 표
                        df_status = pd.DataFrame(status_data)
                        if not df_status.empty:
                            cols_order = ["영역", "숙제명", "진척도", "달성률"] + days
                            df_status = df_status[cols_order]
                            
                            st.dataframe(
                                df_status,
                                hide_index=True,
                                use_container_width=True,
                                column_config={
                                    "달성률": st.column_config.ProgressColumn(
                                        "Goal",
                                        format="%d%%",
                                        min_value=0,
                                        max_value=100,
                                    ),
                                    "영역": st.column_config.TextColumn("Category", width="small"),
                                    "숙제명": st.column_config.TextColumn("Task", width="large"),
                                }
                            )
                        else:
                            st.warning("표시할 데이터가 없습니다.")