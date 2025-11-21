import streamlit as st
import json

def inspect_secrets():
    st.title("🕵️ THE ORACLE: Secrets Inspector")
    st.write("구글 클라우드 인증 키 상태를 정밀 진단합니다.")

    # 1. Secrets 존재 여부 확인
    if "gcp_service_account" not in st.secrets:
        st.error("❌ [CRITICAL] 'gcp_service_account' 섹션이 Secrets에 없습니다.")
        return
    
    st.success("✅ 'gcp_service_account' 섹션 발견됨")
    
    raw_data = st.secrets["gcp_service_account"]
    private_key = raw_data.get("private_key", "")

    # 2. Private Key 기본 검사
    st.subheader("1. 키 형식 분석 (Key Format Analysis)")
    
    if not private_key:
        st.error("❌ Private Key가 비어 있습니다.")
        return

    key_len = len(private_key)
    st.info(f"🔑 키 길이: {key_len} 자 (보통 1500~1700자 사이여야 함)")

    # 3. 헤더/푸터 검사
    has_header = "-----BEGIN PRIVATE KEY-----" in private_key
    has_footer = "-----END PRIVATE KEY-----" in private_key

    if has_header and has_footer:
        st.success("✅ 헤더와 푸터가 정상적으로 포함되어 있습니다.")
    else:
        st.error(f"❌ 헤더/푸터 누락: Header={has_header}, Footer={has_footer}")
        st.warning("키 값을 복사할 때 '-----BEGIN...' 부터 '...KEY-----' 까지 모두 포함해야 합니다.")

    # 4. 줄바꿈 문자(\n) 진단 (가장 중요한 부분)
    st.subheader("2. 줄바꿈 문자 진단 (Newline Check)")
    
    count_slash_n = private_key.count("\n")
    count_double_slash_n = private_key.count("\\n")
    
    st.write(f"- 실제 엔터(\\n) 개수: **{count_slash_n}개**")
    st.write(f"- 이스케이프 문자(\\\\n) 개수: **{count_double_slash_n}개**")

    if count_slash_n > 0:
        st.success("✅ 실제 줄바꿈(Real Newline)이 감지되었습니다. (TOML 파일의 \"\"\" 사용 시 정상)")
    elif count_double_slash_n > 0:
        st.info("ℹ️ 이스케이프 된 줄바꿈(\\\\n)이 감지되었습니다. 코드에서 변환이 필요합니다.")
        # 변환 시뮬레이션
        fixed_key = private_key.replace("\\n", "\n")
        st.caption(f"🔄 변환 후 예상되는 실제 엔터 개수: {fixed_key.count('\n')}개")
    else:
        st.error("❌ 줄바꿈 문자가 전혀 없습니다. 키가 한 줄로 뭉개져 있을 가능성이 높습니다.")

    # 5. 패딩/공백 오염 진단
    st.subheader("3. 오염도 진단 (Corruption Check)")
    if " " in private_key.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").replace("\n", "").replace("\\n", ""):
        st.error("❌ 키 본문에 허용되지 않은 '공백(Space)'이 포함되어 있습니다. 복사 과정에서 끊어쓰기가 들어갔을 수 있습니다.")
    else:
        st.success("✅ 키 본문에 불필요한 공백이 없습니다.")

    # 6. 최종 모의 테스트
    st.subheader("4. 최종 모의 인증 (Simulation)")
    try:
        from google.oauth2.service_account import Credentials
        
        # 실제 DB 연결에 쓰는 로직 그대로 적용
        creds_dict = dict(raw_data)
        if "\\n" in creds_dict["private_key"]:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
        creds = Credentials.from_service_account_info(creds_dict)
        st.balloons()
        st.success("🎉 [PASS] 인증 객체 생성 성공! 이제 DB에 연결할 수 있습니다.")
        
    except Exception as e:
        st.error(f"🔥 [FAIL] 인증 객체 생성 실패: {e}")
        st.error("👉 위의 진단 결과를 바탕으로 Secrets 값을 수정하세요.")

if __name__ == "__main__":
    inspect_secrets()
