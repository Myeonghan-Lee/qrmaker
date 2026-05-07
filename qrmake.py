import streamlit as st
import qrcode
from PIL import Image
import os
import pandas as pd
from io import BytesIO
from datetime import datetime
import pytz
import requests
from bs4 import BeautifulSoup
import base64

# 1. 페이지 제목 설정
st.set_page_config(page_title="로고 삽입 QR 생성기", page_icon="🔗", layout="wide")
st.title("🏫 학교/기관용 QR 코드 생성기")
st.write("URL을 입력하면 중앙에 로고가 삽입된 QR 코드가 자동 생성되며 상세 기록이 남습니다.")

# 히스토리 파일명 설정
HISTORY_FILE = "history.csv"

# --- 세션 상태 설정 및 초기화 함수 ---
if 'url_text' not in st.session_state:
    st.session_state['url_text'] = ""

def clear_text():
    st.session_state['url_text'] = ""

# --- 웹 페이지 제목 가져오는 함수 ---
def get_page_title(url):
    try:
        # 학교 홈페이지 등 접속 시 봇 차단을 막기 위해 User-Agent 추가
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=3)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string if soup.title else "제목 없음"
            return title.strip()
        return "접속 불가 (제목 확인 실패)"
    except Exception:
        return "확인 불가 (잘못된 URL 등)"

# --- 이미지를 Base64 (텍스트 형태)로 변환하는 함수 (표에 넣기 위함) ---
def get_image_base64(img):
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

# --- 입력창과 버튼 배치 ---
col1, col2 = st.columns([5, 1])

with col1:
    url = st.text_input("연결할 URL 주소를 입력하세요:", key="url_text", placeholder="https://www.sen.go.kr/")

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.button("🔄 초기화", on_click=clear_text, use_container_width=True)

LOGO_FILENAME = "logo.png"

if url:
    with st.spinner("QR 코드 생성 및 페이지 정보를 가져오는 중입니다..."):
        try:
            # --- QR 코드 생성 (해상도 증가로 로고 선명도 확보) ---
            # box_size를 10에서 15로 늘려 전체 이미지 해상도를 높입니다.
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=15, 
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)

            # 이미지를 RGBA(투명도 지원) 형식으로 생성
            qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGBA')

            # --- 로고 합성 ---
            if os.path.exists(LOGO_FILENAME):
                logo = Image.open(LOGO_FILENAME).convert("RGBA")
                
                qr_width, qr_height = qr_img.size
                logo_max_size = int(qr_width / 4)
                
                # 고품질 리사이징 적용
                logo.thumbnail((logo_max_size, logo_max_size), Image.Resampling.LANCZOS)
                
                logo_width, logo_height = logo.size
                pos = ((qr_width - logo_width) // 2, (qr_height - logo_height) // 2)
                
                # 투명 배경(Alpha 채널)을 마스크로 사용하여 깔끔하게 합성
                qr_img.paste(logo, pos, logo)
                st.success("로고가 성공적으로 삽입되었습니다!")
            else:
                st.warning("저장소에서 logo.png 파일을 찾을 수 없어 기본 QR코드만 생성합니다.")

            # 결과를 RGB로 다시 변환하여 저장 준비 (PNG 저장을 위함)
            final_img = qr_img.convert("RGB")
            buf = BytesIO()
            final_img.save(buf, format="PNG")
            byte_im = buf.getvalue()

            # 화면 출력 및 다운로드
            st.image(byte_im, caption="생성된 QR 코드 (고해상도)", width=350)
            
            st.download_button(
                label="QR 코드 이미지 다운로드",
                data=byte_im,
                file_name="qr_with_logo.png",
                mime="image/png"
            )

            # --- 데이터 수집 및 히스토리 저장 ---
            # 1. 한국 시간 설정 (Streamlit Cloud 서버 시간에 영향받지 않음)
            kst = pytz.timezone('Asia/Seoul')
            now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
            
            # 2. 페이지 제목 추출
            page_title = get_page_title(url)
            
            # 3. QR 이미지를 Base64 문자열로 변환 (표 삽입용)
            qr_base64 = get_image_base64(final_img)

            new_record = pd.DataFrame([{
                "생성 일시": now_kst, 
                "페이지 제목": page_title, 
                "URL": url, 
                "QR 이미지": qr_base64
            }])

            # 파일 저장 로직 (최근 URL과 같지 않을 때만 추가)
            if os.path.exists(HISTORY_FILE):
                history_df = pd.read_csv(HISTORY_FILE)
                if history_df.iloc[0]["URL"] != url:
                    history_df = pd.concat([new_record, history_df], ignore_index=True)
            else:
                history_df = new_record
                
            history_df.to_csv(HISTORY_FILE, index=False)

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

# --- 하단: 히스토리 대시보드 ---
st.divider()
st.subheader("📂 QR 코드 생성 히스토리")

if os.path.exists(HISTORY_FILE):
    display_df = pd.read_csv(HISTORY_FILE)
    
    # Streamlit의 column_config를 사용하여 표 안에 이미지와 링크를 예쁘게 렌더링합니다.
    st.dataframe(
        display_df,
        column_config={
            "생성 일시": st.column_config.TextColumn("생성 일시(KST)", width="medium"),
            "페이지 제목": st.column_config.TextColumn("페이지 제목", width="large"),
            "URL": st.column_config.LinkColumn("연결 링크 (클릭 시 이동)", width="large"),
            "QR 이미지": st.column_config.ImageColumn("QR 이미지", help="생성된 QR 코드 미리보기")
        },
        use_container_width=True,
        hide_index=True # 불필요한 숫자 인덱스 숨김
    )
    
    with open(HISTORY_FILE, "rb") as f:
        st.download_button(
            label="📊 히스토리 엑셀(CSV)로 다운로드",
            data=f,
            file_name="qrcode_history.csv",
            mime="text/csv"
        )
else:
    st.info("아직 생성된 QR 코드 기록이 없습니다. 위에서 첫 QR 코드를 만들어보세요!")
