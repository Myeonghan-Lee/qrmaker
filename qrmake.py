import streamlit as st
import qrcode
from PIL import Image
import os
import pandas as pd
from io import BytesIO
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup
import base64

# 1. 페이지 제목 설정
st.set_page_config(page_title="로고 삽입 QR 생성기", page_icon="🔗", layout="wide")
st.title("🏫 학교/기관용 QR 코드 생성기")
st.write("URL을 입력하면 중앙에 로고가 선명하게 삽입된 QR 코드가 자동 생성되며 기록이 남습니다.")

HISTORY_FILE = "history.csv"

# --- 세션 상태 설정 및 함수 ---
if 'url_text' not in st.session_state:
    st.session_state['url_text'] = ""

def clear_text():
    st.session_state['url_text'] = ""

# URL 웹페이지 제목 가져오기 함수
def get_page_title(url):
    try:
        # 타임아웃을 2초로 설정하여 딜레이 방지
        response = requests.get(url, timeout=2)
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.title.string.strip() if soup.title else "제목 없음"
    except:
        return "확인 불가 (보안 적용 또는 유효하지 않은 주소)"

# --- 입력창과 버튼 배치 ---
col1, col2 = st.columns([5, 1])

with col1:
    url = st.text_input("연결할 URL 주소를 입력하세요:", key="url_text", placeholder="https://example.com")

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.button("🔄 입력 초기화", on_click=clear_text, use_container_width=True)

LOGO_FILENAME = "logo.png"

if url:
    try:
        # --- QR 코드 생성 단계 (로고 선명도 향상) ---
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=20, # 기존 10에서 20으로 증가시켜 기본 해상도를 대폭 높임 (로고가 선명해집니다)
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

        # --- 로고 합성 단계 ---
        if os.path.exists(LOGO_FILENAME):
            logo = Image.open(LOGO_FILENAME)
            
            qr_width, qr_height = qr_img.size
            logo_max_size = int(qr_width / 4)
            # LANCZOS 필터를 사용하여 축소 시에도 깨짐을 최소화
            logo.thumbnail((logo_max_size, logo_max_size), Image.Resampling.LANCZOS)
            
            logo_width, logo_height = logo.size
            pos = ((qr_width - logo_width) // 2, (qr_height - logo_height) // 2)
            
            qr_img.paste(logo, pos)
            st.success("로고가 성공적으로 삽입되었습니다!")
        else:
            st.warning("저장소에서 logo.png 파일을 찾을 수 없어 기본 QR코드만 생성합니다.")

        # --- 결과 화면 및 다운로드 ---
        buf = BytesIO()
        qr_img.save(buf, format="PNG")
        byte_im = buf.getvalue()

        # 이미지를 Base64 문자열로 변환 (표에 넣기 위함)
        b64_img = "data:image/png;base64," + base64.b64encode(byte_im).decode('utf-8')

        st.image(byte_im, caption="생성된 QR 코드 (로고 포함)", width=300)
        
        st.download_button(
            label="QR 코드 이미지 다운로드",
            data=byte_im,
            file_name="qr_with_logo.png",
            mime="image/png"
        )

        # --- 히스토리 저장 (KST 적용, 제목 크롤링, 이미지 포함) ---
        # 한국 표준시(UTC+9) 설정
        KST = timezone(timedelta(hours=9))
        now = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
        
        page_title = get_page_title(url)

        new_record = pd.DataFrame([{
            "생성 일시": now, 
            "페이지 제목": page_title,
            "생성된 URL": url, 
            "QR코드 이미지": b64_img
        }])

        if os.path.exists(HISTORY_FILE):
            history_df = pd.read_csv(HISTORY_FILE)
            # 중복 방지 (가장 최근 생성한 URL과 다를 경우에만 추가)
            if history_df.iloc[0]["생성된 URL"] != url:
                history_df = pd.concat([new_record, history_df], ignore_index=True)
        else:
            history_df = new_record
            
        history_df.to_csv(HISTORY_FILE, index=False)

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

# --- 하단: 히스토리 대시보드 ---
st.divider()

col3, col4 = st.columns([5, 1])
with col3:
    st.subheader("📂 QR 코드 생성 히스토리")
with col4:
    # 히스토리 초기화 버튼 추가
    if st.button("🗑️ 히스토리 초기화", use_container_width=True):
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
            st.rerun() # 앱을 새로고침하여 화면에서 즉시 지웁니다.

if os.path.exists(HISTORY_FILE):
    display_df = pd.read_csv(HISTORY_FILE)
    
    # 스트림릿 표에 이미지 렌더링 설정 적용
    st.dataframe(
        display_df,
        column_config={
            "QR코드 이미지": st.column_config.ImageColumn(
                "QR코드 미리보기", help="생성된 QR코드 이미지"
            ),
            "생성된 URL": st.column_config.LinkColumn("링크 주소")
        },
        use_container_width=True,
        hide_index=True # 깔끔하게 보이기 위해 인덱스 번호 숨김
    )
    
    with open(HISTORY_FILE, "rb") as f:
        st.download_button(
            label="📊 히스토리 엑셀(CSV)로 다운로드",
            data=f,
            file_name="qrcode_history.csv",
            mime="text/csv"
        )
else:
    st.info("아직 생성된 QR 코드 기록이 없습니다. URL을 입력해 첫 QR 코드를 만들어보세요!")
