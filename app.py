import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime

# --- 1. การเชื่อมต่อ Google Sheets ---
def get_google_sheet(sheet_name):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # ดึงรหัสจาก Secrets ของ Streamlit Cloud
    creds_dict = json.loads(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    # URL ของคุณที่ระบุมา
    sheet_url = "https://docs.google.com/spreadsheets/d/1gQZPiMC-wkzWEsoxY-81pu7LVRsFUf7RoS04X8nCReo/edit"
    
    try:
        return client.open_by_url(sheet_url).worksheet(sheet_name)
    except Exception as e:
        st.error(f"❌ ไม่พบแท็บชื่อ '{sheet_name}' กรุณาตรวจสอบชื่อแท็บใน Google Sheets ให้ตรงกัน")
        return None

# --- 2. ระบบจัดการ Session (จำ Login) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""

st.set_page_config(page_title="PIP Performance Portal", layout="centered")

# --- 3. หน้าจอ Login / Sign Up ---
if not st.session_state.logged_in:
    st.title("🔐 เข้าสู่ระบบติดตามงาน")
    tab_log, tab_sign = st.tabs(["Login", "Sign Up (สมาชิกใหม่)"])
    
    with tab_log:
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Log In", use_container_width=True):
                user_sheet = get_google_sheet("Users")
                if user_sheet:
                    users = pd.DataFrame(user_sheet.get_all_records())
                    if not users.empty:
                        match = users[(users['Username'] == u) & (users['Password'] == str(p))]
                        if not match.empty:
                            st.session_state.logged_in = True
                            st.session_state.user_name = match.iloc[0]['Name']
                            st.rerun()
                        else: st.error("Username หรือ Password ไม่ถูกต้อง")
    
    with tab_sign:
        with st.form("signup_form"):
            new_u = st.text_input("ตั้งชื่อ Username")
            new_p = st.text_input("ตั้งรหัสผ่าน", type="password")
            new_n = st.text_input("ชื่อ-นามสกุลจริง")
            if st.form_submit_button("สมัครสมาชิก"):
                user_sheet = get_google_sheet("Users")
                if user_sheet:
                    user_sheet.append_row([new_u, new_p, new_n, "Geologist"])
                    st.success("สมัครสมาชิกสำเร็จ! กรุณาไปที่หน้า Login")

# --- 4. หน้าจอหลัก (เมื่อ Login แล้ว) ---
else:
    st.sidebar.success(f"👤 สวัสดี: {st.session_state.user_name}")
    if st.sidebar.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()

    st.header("📋 ระบบติดตามผลงาน (PIP)")
    t1, t2 = st.tabs(["📅 วางแผนสัปดาห์ (Weekly)", "📝 รายงานรายวัน (Daily)"])

    # --- ส่วนที่ 1: Weekly Plan (ส่งข้อมูลแยกอิสระ) ---
    with t1:
        st.subheader("วางแผนงานประจำสัปดาห์")
        with st.form("weekly_form", clear_on_submit=True):
            p_date = st.date_input("สัปดาห์ของวันที่")
            w_num = p_date.isocalendar()[1]
            p_name = st.text_input("ชื่อโปรเจกต์ (Project Name)")
            p_due = st.date_input("กำหนดส่ง (Deadline)")
            
            st.write("แตกงานย่อย (Task Breakdown)")
            task_df = pd.DataFrame([{"งาน": "", "เป้าหมาย": "", "%": 0}])
            tasks = st.data_editor(task_df, num_rows="dynamic", use_container_width=True, hide_index=True)
            kpi = st.text_input("ตัวชี้วัด (KPI)")

            if st.form_submit_button("บันทึกแผนงาน", type="primary"):
                if not p_name: st.error("กรุณากรอกชื่อโปรเจกต์")
                else:
                    sheet = get_google_sheet("Weekly Plan")
                    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    # รวมตารางงานเป็นข้อความ
                    t_str = "\n".join([f"- {r['งาน']} ({r['เป้าหมาย']}) {r['%']}%" for _, r in tasks.iterrows() if r['งาน']])
                    sheet.append_row([ts, st.session_state.user_name, f"W{w_num}", p_name, str(p_due), t_str, kpi])
                    st.success("บันทึกแผนรายสัปดาห์สำเร็จ!")

    # --- ส่วนที่ 2: Daily Update (ส่งข้อมูลแยกอิสระ) ---
    with t2:
        st.subheader("รายงานการทำงานรายวัน")
        with st.form("daily_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            d_work = c1.date_input("วันที่")
            t_in = c2.time_input("เวลาเข้างาน")
            p_upd = st.text_input("ชื่อโปรเจกต์ (Project)")
            prog = st.select_slider("ความคืบหน้า (%)", options=["0%", "25%", "50%", "75%", "100%"])
            link = st.text_input("🔗 ลิงก์หลักฐานงาน")

            if st.form_submit_button("ส่งรายงานรายวัน", type="primary"):
                if not p_upd: st.error("กรุณากรอกชื่อโปรเจกต์")
                else:
                    sheet = get_google_sheet("Daily Update")
                    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    sheet.append_row([ts, st.session_state.user_name, str(d_work), str(t_in), p_upd, "Daily Task", prog, link])
                    st.success("บันทึกอัปเดตรายวันสำเร็จ!")
