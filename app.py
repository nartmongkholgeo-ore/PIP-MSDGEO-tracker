import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import json

# --- 1. การตั้งค่าการเชื่อมต่อ Google Sheets (ใช้ระบบ Secrets) ---
def get_google_sheet(sheet_name):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    # 🔴 เอา URL ของ Google Sheet คุณมาใส่ตรงนี้ 🔴
    sheet_url = "https://docs.google.com/spreadsheets/d/1gQZPiMC-wkzWEsoxY-81pu7LVRsFUf7RoS04X8nCReo/edit?gid=0#gid=0" 
    
    sheet = client.open_by_url(sheet_url).worksheet(sheet_name)
    return sheet

PROJECTS = ["SWCC", "STS Raw Materials Exploration", "KCL Project", "Quartz SMK", "SKW Laterrite Exploration", "SLP Project", "EPR Reports", "Mine Slope stability", "SLSN Quicklime"]
TASK_CATEGORIES = ["Data preparation", "Drill planning", "Drilling Supervision", "Core Logging", "Geochemical Sampling (XRF)", "Mapping", "Data Modeling", "Report Writing"]
PROGRESS_OPTS = ["0%", "25%", "50%", "75%", "100% (Done)"]

st.set_page_config(page_title="PIP Performance Portal", layout="centered")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def login():
    st.title("🔐 Geologist Performance Portal")
    user = st.text_input("ชื่อพนักงาน")
    password = st.text_input("รหัสผ่าน", type="password") 
    if st.button("เข้าสู่ระบบ", use_container_width=True):
        if user and password == "1234": 
            st.session_state.logged_in = True
            st.session_state.user_name = user
            st.rerun()
        else:
            st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

if not st.session_state.logged_in:
    login()
else:
    st.sidebar.write(f"👤 ผู้ใช้งาน: **{st.session_state.user_name}**")
    if st.sidebar.button("Log out"):
        st.session_state.logged_in = False
        st.rerun()

    st.header("📊 PIP Performance Tracker")
    tab1, tab2 = st.tabs(["📅 วางแผนรายสัปดาห์", "📝 รายงานผลรายวัน"])

    with tab1:
        with st.form("weekly_plan_form", clear_on_submit=True):
            st.subheader("Weekly Commitment")
            plan_date = st.date_input("วันที่เริ่มต้นสัปดาห์")
            week_num = plan_date.isocalendar()[1]
            st.info(f"บันทึกสำหรับ: **สัปดาห์ที่ {week_num}**")

            col1, col2 = st.columns(2)
            with col1: p_select = st.selectbox("เลือกโปรเจกต์", ["-- เลือก --"] + PROJECTS)
            with col2: p_new = st.text_input("หรือพิมพ์โปรเจกต์ใหม่")
            
            deadline = st.date_input("กำหนดส่งงาน (Deadline)")

            st.markdown("---")
            st.write("**แตกย่อยงานประจำสัปดาห์ (Task Breakdown)**")
            init_df = pd.DataFrame([{"งานย่อย": "", "เป้าหมาย": "", "น้ำหนัก (%)": 0}])
            edited_tasks = st.data_editor(init_df, num_rows="dynamic", use_container_width=True, hide_index=True)
            kpi_desc = st.text_input("ตัวชี้วัดความสำเร็จ (Overall KPI)")

            if st.form_submit_button("บันทึกแผนประจำสัปดาห์", type="primary"):
                final_p = p_new if p_new else p_select
                if final_p == "-- เลือก --":
                    st.error("กรุณาระบุชื่อโปรเจกต์")
                else:
                    try:
                        task_text = "\n".join([f"- {r['งานย่อย']} ({r['เป้าหมาย']}) [{r['น้ำหนัก (%)']}%]" for _, r in edited_tasks.iterrows() if r['งานย่อย']])
                        sheet = get_google_sheet("Weekly Plan")
                        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        sheet.append_row([ts, st.session_state.user_name, f"W{week_num}", final_p, str(deadline), task_text, kpi_desc])
                        st.success("บันทึกแผนสำเร็จ!")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")

    with tab2:
        with st.form("daily_update_form", clear_on_submit=True):
            st.subheader("Daily Timesheet & Progress")
            col_d1, col_d2 = st.columns(2)
            with col_d1: work_date = st.date_input("วันที่ทำงาน")
            with col_d2: clock_in = st.time_input("เวลาเข้างาน")

            p_upd = st.selectbox("โปรเจกต์ที่ทำ", PROJECTS)
            t_cat = st.selectbox("ประเภทงาน", TASK_CATEGORIES)
            prog = st.select_slider("ความคืบหน้างาน", options=PROGRESS_OPTS)
            link = st.text_input("🔗 ลิงก์หลักฐานงาน (Google Drive / Photo)")

            if st.form_submit_button("ส่งรายงานรายวัน", type="primary"):
                try:
                    sheet = get_google_sheet("Daily Update")
                    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    sheet.append_row([ts, st.session_state.user_name, str(work_date), str(clock_in), p_upd, t_cat, prog, link])
                    st.success("บันทึกข้อมูลรายวันสำเร็จ!")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
