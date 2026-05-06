import streamlit as st
import qrcode
from PIL import Image
import os
from io import BytesIO

# 1. 페이지 제목 설정
st.set_page_config(page_title="로고 삽입 QR 생성기", page_icon="🔗")
st.title("🏫 학교/기관용 QR 코드 생성기")
st.write("URL을 입력하면 중앙에 로고가 삽입된 QR 코드가 자동 생성됩니다.")

# 2. 사용자로부터 URL 입력 받기
url = st.text_input("연결할 URL 주소를 입력하세요:", placeholder="https://example.com")

# 3. 로고 파일 확인 (파일 이름이 logo.png여야 합니다)
LOGO_FILENAME = "logo.png"

if url:
    try:
        # --- QR 코드 생성 단계 ---
        # 로고가 가려져도 인식되게 하려면 ERROR_CORRECT_H (High) 설정이 필수입니다.
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # QR 코드를 이미지(RGB 형태)로 생성
        qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

        # --- 로고 합성 단계 ---
        # 깃허브 저장소에 logo.png가 있는지 확인
        if os.path.exists(LOGO_FILENAME):
            logo = Image.open(LOGO_FILENAME)
            
            # QR 코드 크기에 맞춰 로고 사이즈 조절 (전체의 약 20% 크기)
            qr_width, qr_height = qr_img.size
            logo_max_size = int(qr_width / 4)
            logo.thumbnail((logo_max_size, logo_max_size), Image.Resampling.LANCZOS)
            
            # 로고를 중앙에 배치할 좌표 계산
            logo_width, logo_height = logo.size
            pos = ((qr_width - logo_width) // 2, (qr_height - logo_height) // 2)
            
            # QR 코드 위에 로고 붙이기
            qr_img.paste(logo, pos)
            st.success("로고가 성공적으로 삽입되었습니다!")
        else:
            st.warning("저장소에서 logo.png 파일을 찾을 수 없어 기본 QR코드만 생성합니다.")

        # --- 결과 화면 및 다운로드 단계 ---
        # 이미지를 화면에 표시하기 위해 메모리에 저장
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

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
