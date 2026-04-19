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
        st.error(f"ไม่พบหน้าแท็บชื่อ '{sheet_name}' ใน Google Sheets กรุณาตรวจสอบการตั้งชื่อแท็บ")
        return None

# --- 2. ฟังก์ชันจัดการข้อมูลผู้ใช้งาน ---
def fetch_users():
    sheet = get_google_sheet("Users")
    if sheet:
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    return pd.DataFrame()

def add_new_user(username, password, name):
    sheet = get_google_sheet("Users")
    if sheet:
        sheet.append_row([username, password, name, "Geologist"])
        return True
    return False

# --- 3. ตั้งค่าระบบ Session (จำการ Login) ---
if 'auth_status' not in st.session_state:
    st.session_state.auth_status = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}

st.set_page_config(page_title="Geologist PIP Performance", layout="centered")

# --- ข้อมูลตัวเลือก (Dropdown Options) ---
PROJECTS = ["White Cement Limestone", "Raw Material Exploration", "KCL Project", "VCM Mine", "Len Na", "Len Bang"]
TASKS = ["Core Logging", "Geochemical Sampling (XRF)", "Mapping", "Drilling Supervision", "Data Modeling", "Report Writing"]
PROGRESS_LEVELS = ["0%", "25%", "50%", "75%", "100% (Done)"]

# --- 4. หน้าจอ Login และสมัครสมาชิก ---
if not st.session_state.auth_status:
    st.title("🔐 Geologist Performance Portal")
    choice = st.radio("เลือกรายการ", ["เข้าสู่ระบบ", "สมัครสมาชิกใหม่"], horizontal=True)
    
    if choice == "เข้าสู่ระบบ":
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Log In", use_container_width=True):
                users_df = fetch_users()
                if not users_df.empty:
                    # ตรวจสอบชื่อและรหัส
                    match = users_df[(users_df['Username'] == u) & (users_df['Password'] == str(p))]
                    if not match.empty:
                        st.session_state.auth_status = True
                        st.session_state.user_info = match.iloc[0].to_dict()
                        st.success("เข้าสู่ระบบสำเร็จ!")
                        st.rerun()
                    else:
                        st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
                else:
                    st.error("ยังไม่มีข้อมูลผู้ใช้งานในระบบ")

    else:
        with st.form("signup_form"):
            new_u = st.text_input("ตั้งชื่อ Username (ภาษาอังกฤษ)")
            new_p = st.text_input("ตั้งรหัสผ่าน", type="password")
            real_name = st.text_input("ชื่อ-นามสกุลจริง")
            if st.form_submit_button("ลงทะเบียน"):
                users_df = fetch_users()
                if not users_df.empty and new_u in users_df['Username'].values:
                    st.error("ชื่อ Username นี้ถูกใช้ไปแล้ว")
                elif new_u and new_p and real_name:
                    if add_new_user(new_u, new_p, real_name):
                        st.success("สมัครสมาชิกสำเร็จ! กรุณาสลับไปหน้าเข้าสู่ระบบ")
                else:
                    st.warning("กรุณากรอกข้อมูลให้ครบทุกช่อง")

# --- 5. หน้าจอหลัก (เมื่อ Login แล้ว) ---
else:
    current_user = st.session_state.user_info
    st.sidebar.success(f"👤 สวัสดี: {current_user['Name']}")
    if st.sidebar.button("Log Out"):
        st.session_state.auth_status = False
        st.session_state.user_info = {}
        st.rerun()

    st.header("📋 ระบบติดตามงานรายสัปดาห์และรายวัน")
    tab1, tab2 = st.tabs(["📅 Weekly Plan (วันจันทร์)", "📝 Daily Update (รายวัน)"])

    # --- ส่วนที่ 1: การวางแผนรายสัปดาห์ ---
    with tab1:
        st.info("ใช้สำหรับลงแผนงานตอนต้นสัปดาห์")
        with st.form("weekly_form", clear_on_submit=True):
            plan_date = st.date_input("วันที่เริ่มต้นสัปดาห์")
            week_num = plan_date.isocalendar()[1]
            st.write(f"📌 บันทึกแผนงานประจำ **สัปดาห์ที่ {week_num}**")

            col1, col2 = st.columns(2)
            with col1: p_drop = st.selectbox("เลือกโปรเจกต์", ["-- เลือก --"] + PROJECTS)
            with col2: p_text = st.text_input("หรือ พิมพ์ชื่อโปรเจกต์ใหม่")
            
            due = st.date_input("กำหนดส่งงาน (Project Deadline)")

            st.markdown("---")
            st.write("**ตารางงานย่อยประจำสัปดาห์**")
            task_df = pd.DataFrame([{"งานย่อย": "", "เป้าหมาย": "", "น้ำหนัก (%)": 0}])
            edited_tasks = st.data_editor(task_df, num_rows="dynamic", use_container_width=True, hide_index=True)
            
            kpi_input = st.text_input("ตัวชี้วัดความสำเร็จภาพรวม (KPI)")

            if st.form_submit_button("บันทึกแผนงาน", type="primary"):
                final_project = p_text if p_text.strip() != "" else p_drop
                if final_project == "-- เลือก --":
                    st.error("กรุณาระบุชื่อโปรเจกต์")
                else:
                    # รวมตารางงานย่อยเป็นข้อความ
                    t_list = []
                    for _, r in edited_tasks.iterrows():
                        if r['งานย่อย']:
                            t_list.append(f"- {r['งานย่อย']} ({r['เป้าหมาย']}) [{r['น้ำหนัก (%)']}%]")
                    
                    t_str = "\n".join(t_list)
                    sheet = get_google_sheet("Weekly Plan")
                    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    sheet.append_row([ts, current_user['Name'], f"W{week_num}", final_project, str(due), t_str, kpi_input])
                    st.success("บันทึกแผนประจำสัปดาห์เรียบร้อย!")

    # --- ส่วนที่ 2: การอัปเดตงานรายวัน ---
    with tab2:
        st.info("ใช้สำหรับลงเวลาเข้างานและอัปเดตงานรายวัน")
        with st.form("daily_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: d_work = st.date_input("วันที่ทำงาน")
            with c2: t_in = st.time_input("เวลาเข้างาน")

            p_upd = st.selectbox("โปรเจกต์ที่ทำวันนี้", PROJECTS)
            t_cat = st.selectbox("ประเภทงาน", TASKS)
            prog = st.select_slider("ความคืบหน้างาน (%)", options=PROGRESS_LEVELS)
            evidence = st.text_input("🔗 ลิงก์หลักฐานงาน (Google Drive/Photo Link)")

            if st.form_submit_button("ส่งรายงานรายวัน", type="primary"):
                sheet = get_google_sheet("Daily Update")
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                sheet.append_row([ts, current_user['Name'], str(d_work), str(t_in), p_upd, t_cat, prog, evidence])
                st.success("บันทึกอัปเดตรายวันสำเร็จ!")
