import streamlit as st
import qrcode
from PIL import Image
import os
import pandas as pd
from io import BytesIO
from datetime import datetime

# 1. 페이지 제목 설정
st.set_page_config(page_title="로고 삽입 QR 생성기", page_icon="🔗")
st.title("🏫 학교/기관용 QR 코드 생성기")
st.write("URL을 입력하면 중앙에 로고가 삽입된 QR 코드가 자동 생성되며 기록이 남습니다.")

# 히스토리 파일명 설정
HISTORY_FILE = "history.csv"

# --- 초기화 기능을 위한 세션 상태(Session State) 설정 ---
if 'url_text' not in st.session_state:
    st.session_state['url_text'] = ""

def clear_text():
    st.session_state['url_text'] = ""

# --- 입력창과 버튼을 나란히 배치 ---
col1, col2 = st.columns([4, 1])

with col1:
    url = st.text_input("연결할 URL 주소를 입력하세요:", key="url_text", placeholder="https://example.com")

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.button("🔄 초기화", on_click=clear_text, use_container_width=True)

# 로고 파일 확인
LOGO_FILENAME = "logo.png"

if url:
    try:
        # --- QR 코드 생성 단계 ---
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
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
            logo.thumbnail((logo_max_size, logo_max_size), Image.Resampling.LANCZOS)
            
            logo_width, logo_height = logo.size
            pos = ((qr_width - logo_width) // 2, (qr_height - logo_height) // 2)
            
            qr_img.paste(logo, pos)
            st.success("로고가 성공적으로 삽입되었습니다!")
        else:
            st.warning("저장소에서 logo.png 파일을 찾을 수 없어 기본 QR코드만 생성합니다.")

        # --- 결과 화면 및 이미지 다운로드 ---
        buf = BytesIO()
        qr_img.save(buf, format="PNG")
        byte_im = buf.getvalue()

        st.image(byte_im, caption="생성된 QR 코드 (로고 포함)", width=350)
        
        st.download_button(
            label="QR 코드 이미지 다운로드",
            data=byte_im,
            file_name="qr_with_logo.png",
            mime="image/png"
        )

        # --- 히스토리 저장 로직 추가 ---
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_record = pd.DataFrame([{"생성 일시": now, "연결된 URL": url}])

        # 기존 파일이 있으면 불러와서 합치고, 없으면 새로 만듭니다.
        if os.path.exists(HISTORY_FILE):
            history_df = pd.read_csv(HISTORY_FILE)
            # 중복 저장을 방지하기 위해 가장 최근 URL이 현재 URL과 다를 때만 저장
            if history_df.iloc[0]["연결된 URL"] != url:
                history_df = pd.concat([new_record, history_df], ignore_index=True)
        else:
            history_df = new_record
            
        history_df.to_csv(HISTORY_FILE, index=False)

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

# --- 하단: 히스토리 대시보드 표시 ---
st.divider() # 시각적 구분선
st.subheader("📂 QR 코드 생성 히스토리")

if os.path.exists(HISTORY_FILE):
    # 히스토리 파일 읽어오기
    display_df = pd.read_csv(HISTORY_FILE)
    
    # 표 형태로 화면에 출력
    st.dataframe(display_df, use_container_width=True)
    
    # 엑셀(CSV) 파일로 다운로드하는 버튼
    with open(HISTORY_FILE, "rb") as f:
        st.download_button(
            label="📊 히스토리 엑셀(CSV)로 다운로드",
            data=f,
            file_name="qrcode_history.csv",
            mime="text/csv"
        )
else:
    st.info("아직 생성된 QR 코드 기록이 없습니다. URL을 입력해 첫 QR 코드를 만들어보세요!")
