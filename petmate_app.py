# PetMate: 반려동물 통합 케어 앱 (Streamlit)
import os, json, uuid
from datetime import datetime, date, time, timedelta
from dateutil import tz
import pandas as pd
import streamlit as st
import hashlib

# ===== 페이지 설정 =====
st.set_page_config(page_title="PetMate",page_icon="🐾",layout="wide")

# ===== 자동 로그인 (쿠키 기반) =====
cookie_user = st.experimental_get_cookie("petmate_user")
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None and cookie_user:
    st.session_state.user = cookie_user  # 쿠키 기반 자동 로그인

# ===== 경로 설정 =====
DATA_DIR = "data"
USER_FILE = os.path.join(DATA_DIR, "users.json")
PHOTO_DIR = os.path.join(DATA_DIR, "pet_photos")
os.makedirs(PHOTO_DIR, exist_ok=True)
PET_FILE = os.path.join(DATA_DIR, "pets.json")
FEED_FILE = os.path.join(DATA_DIR, "feed_log.csv")
WATER_FILE = os.path.join(DATA_DIR, "water_log.csv")
MED_FILE = os.path.join(DATA_DIR, "med_schedule.json")
HOSP_FILE = os.path.join(DATA_DIR, "hospital_events.json")
UNSAFE_FILE = os.path.join(DATA_DIR, "unsafe_db.json")
os.makedirs(DATA_DIR, exist_ok=True)

# ===== 유틸 =====
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path,"r",encoding="utf-8") as f: return json.load(f)
        except:
            return default
    return default

def save_json(path,data):
    with open(path,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

def load_users():
    return load_json(USER_FILE, [])

def save_users(users):
    save_json(USER_FILE, users)

def load_csv(path,cols):
    if os.path.exists(path):
        try: return pd.read_csv(path)
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_csv(path,df):
    df.to_csv(path,index=False)

def local_today():
    return datetime.now(tz.gettz("Asia/Seoul")).date()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ===== 초기 세션 =====
if "pets" not in st.session_state: 
    st.session_state.pets = load_json(PET_FILE,[])
if "med_schedule" not in st.session_state: 
    st.session_state.med_schedule = load_json(MED_FILE,[])
if "hospital_events" not in st.session_state: 
    st.session_state.hospital_events = load_json(HOSP_FILE,[])
if "unsafe_db" not in st.session_state:
    default_unsafe=[
        {"category":"음식","name":"초콜릿","risk":"고위험","why":"카카오의 메틸잔틴(테오브로민) 독성"},
        {"category":"음식","name":"포도/건포도","risk":"고위험","why":"급성 신장손상 보고"}
    ]
    st.session_state.unsafe_db = load_json(UNSAFE_FILE,default_unsafe)

feed_cols=["log_id","pet_id","date","amount_g","memo"]
water_cols=["log_id","pet_id","date","amount_ml","memo"]

feed_df = load_csv(FEED_FILE,feed_cols)
water_df = load_csv(WATER_FILE,water_cols)

def recommended_food_grams(species:str,weight_kg:float)->tuple:
    if weight_kg<=0: return (0,0)
    if species.lower() in ["개","강아지","dog"]:
        kcal=weight_kg*30+70; grams=round(kcal/3.5)
    else:
        kcal=60*weight_kg; grams=round(kcal/3.5)
    return grams,max(0,round(grams*0.1))

def recommended_water_ml(weight_kg:float)->int:
    return int(round(weight_kg*60)) if weight_kg>0 else 0

def pet_selector(label="반려동물 선택", key=None):
    pets=st.session_state.pets
    if not pets:
        st.info("먼저 반려동물을 등록해 주세요 (왼쪽 '반려동물 프로필').")
        return None
    opts={f"{p['name']} ({p['species']})":p for p in pets}
    return opts[st.selectbox(label,list(opts.keys()), key=key)]

# ===== UI 시작 =====
st.title("🐾 PetMate")

# ===== 로그인 상태 확인 =====
if not st.session_state.user:

    # 로그인 페이지
    tab_login = st.tabs(["로그인/회원가입"])[0]
    
    with tab_login:
        st.header("🔐 로그인 & 회원가입")
        st.info("PetMate에 오신 것을 환영합니다!")

        users = load_users()
        tab1, tab2 = st.tabs(["로그인", "회원가입"])

        # ---------------- 로그인 ----------------
        with tab1:
            username = st.text_input("아이디")
            password = st.text_input("비밀번호", type="password")

            if st.button("로그인"):
                hashed = hash_password(password)
                if any(u["username"] == username and u["password"] == hashed for u in users):
                    st.session_state.user = username

                    # ★ 쿠키에 로그인 정보 저장 (30일 유지)
                    st.experimental_set_cookie(
                        "petmate_user", username, 
                        max_age=60*60*24*30
                    )

                    st.success(f"{username}님 로그인 성공!")
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

        # ---------------- 회원가입 ----------------
        with tab2:
            new_user = st.text_input("새 아이디")
            new_pass = st.text_input("새 비밀번호", type="password")

            if st.button("회원가입"):
                if not new_user or not new_pass:
                    st.error("아이디와 비밀번호를 모두 입력해주세요.")
                elif any(u["username"] == new_user for u in users):
                    st.error("이미 존재하는 아이디입니다.")
                else:
                    users.append({
                        "username": new_user,
                        "password": hash_password(new_pass)
                    })
                    save_users(users)
                    st.success("회원가입 완료!")

else:
    # ===== 로그인된 상태 =====
    col1, col2 = st.columns([6, 1])
    with col1:
        st.write(f"안녕하세요, **{st.session_state.user}**님! 👋")

    with col2:
        if st.button("로그아웃"):
            st.session_state.user = None

            # ★ 쿠키 삭제 (자동 로그인 해제)
            st.experimental_delete_cookie("petmate_user")

            st.rerun()

    # ===== 전체 기능 탭 =====
    tab_dash, tab_profile, tab_feed, tab_med, tab_hosp, tab_risk, tab_data = st.tabs([
        "대시보드","반려동물 프로필", "사료/급수 기록","복약 알림","병원 일정","위험 정보 검색","데이터 관리"
    ])

    # ===== 대시보드 =====
    with tab_dash:
        st.header("📊 오늘 한눈에 보기")
        pet = pet_selector(key="dashboard_pet_selector")
        if pet:
            col1,col2,col3 = st.columns(3)

            # 기본 정보
            with col1:
                st.subheader("기본 정보")
                st.write(f"**이름**: {pet['name']}")
                st.write(f"**종**: {pet['species']}")
                st.write(f"**체중**: {pet.get('weight_kg','-')} kg")
                if pet.get("birth"): st.write(f"**생일**: {pet['birth']}")
                if pet.get("notes"): st.caption(pet["notes"])
                if pet.get("photo_path") and os.path.exists(pet["photo_path"]):
                    st.image(pet["photo_path"],width=150)

            # 사료
            with col2:
                grams,snack_limit = recommended_food_grams(
                    pet["species"],
                    float(pet.get("weight_kg",0) or 0)
                )
                today = local_today().isoformat()
                eaten = feed_df[
                    (feed_df["pet_id"]==pet["id"]) &
                    (feed_df["date"]==today)
                ]["amount_g"].sum()
                
                st.subheader("사료/간식 권장량")
                st.write(f"권장: {grams} g/일 / 간식 상한: {snack_limit} g")
                st.progress(min(1.0,eaten/grams if grams else 0),
                    text=f"오늘 섭취: {int(eaten)} g")

            # 물
            with col3:
                wml = recommended_water_ml(float(pet.get("weight_kg",0) or 0))
                drank = water_df[
                    (water_df["pet_id"]==pet["id"]) &
                    (water_df["date"]==today)
                ]["amount_ml"].sum()
                
                st.subheader("물 권장량")
                st.write(f"권장: {wml} ml/일")
                st.progress(min(1.0,drank/wml if wml else 0),
                    text=f"오늘 급수: {int(drank)} ml")

    # ------------------------------------------
    # 이하 프로필/사료/복약/병원/위험/데이터 관리 탭은
    # 기존 코드 그대로 유지 (내용 생략)
    # 전체 코드 너무 길어지므로 핵심은 로그인 유지 부분
    # ------------------------------------------

# ===== 푸터 =====
st.divider()
st.caption("© 2025 PetMate • 학습/포트폴리오용 샘플. 실제 의료 조언은 수의사와 상담하세요.")
