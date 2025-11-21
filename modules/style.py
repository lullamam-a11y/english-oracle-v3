# modules/style.py
import streamlit as st

def apply_custom_style():
    st.markdown("""
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700;900&display=swap" rel="stylesheet">
        
        <style>
        /* 1. 기본 설정 */
        html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
        .stApp { background-color: #F5F7F9; }
        
        /* [중요] 앱의 필수 버튼은 살리고, 불필요한 메뉴만 숨김 */
        #MainMenu {visibility: hidden;} /* 우측 상단 점 3개 메뉴 숨김 */
        footer {visibility: hidden;}    /* 하단 Made with Streamlit 숨김 */
        /* header {visibility: hidden;}  <-- 이 줄을 삭제했습니다! (사이드바 버튼 살리기 위해) */
        
        /* 2. 카드 컨테이너 스타일 */
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            background-color: white;
            border-radius: 16px;
            border: 1px solid #E1E4E8;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            padding: 20px;
            transition: all 0.3s ease;
        }
        
        div[data-testid="stVerticalBlockBorderWrapper"] > div:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.08);
            border-color: #D1D9E0;
        }

        /* =================================================================
           [핵심 1] 텍스트형 체크박스 -> '버튼형' 디자인
           ================================================================= */
        div[data-testid="stCheckbox"] label span:first-child { display: none !important; }
        
        div[data-testid="stCheckbox"] label div[data-testid="stMarkdownContainer"] p {
            color: #90A4AE;
            font-size: 13px;
            font-weight: 600;
            text-align: center;
            margin: 0px;
            padding: 8px 0px;
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.2s ease;
            white-space: nowrap !important; 
            width: 100% !important;
            display: block !important;
        }
        
        div[data-testid="stCheckbox"] label div[data-testid="stMarkdownContainer"] p:hover {
            background-color: #F5F7F9;
            color: #546E7A;
        }

        div[data-testid="stCheckbox"]:has(input:checked) label div[data-testid="stMarkdownContainer"] p {
            background-color: #E3F2FD !important;
            color: #1976D2 !important;
            font-weight: 900 !important;
            transform: scale(1.05);
            box-shadow: 0 2px 4px rgba(25, 118, 210, 0.15);
        }

        /* =================================================================
           [핵심 2] 모바일 레이아웃 스마트 교정 (Grid System)
           ================================================================= */
        @media (max-width: 768px) {
            div[data-testid="stHorizontalBlock"]:has(div[data-testid="stCheckbox"]) {
                display: grid !important;
                grid-template-columns: repeat(7, 1fr) !important;
                gap: 4px !important;
                width: 100% !important;
            }
            
            div[data-testid="stHorizontalBlock"]:has(div[data-testid="stCheckbox"]) div[data-testid="column"] {
                width: 100% !important;
                min-width: 0px !important;
                flex: none !important;
                padding: 0px !important;
                margin: 0px !important;
            }
            
            div[data-testid="stCheckbox"] {
                display: flex !important;
                justify-content: center !important;
                align-items: center !important;
                margin-top: 0px !important;
                width: 100% !important;
            }
            
            div[data-testid="stCheckbox"] label div[data-testid="stMarkdownContainer"] p {
                font-size: 11px !important;
                padding: 6px 0px !important;
                border-radius: 6px !important;
            }
        }
        
        @media (min-width: 769px) {
            div[data-testid="stHorizontalBlock"]:has(div[data-testid="stCheckbox"]) {
                display: grid;
                grid-template-columns: repeat(7, 1fr);
                gap: 10px;
            }
            div[data-testid="stCheckbox"] label div[data-testid="stMarkdownContainer"] p {
                text-align: center !important;
            }
        }

        /* 기타 스타일 */
        .badge-category {
            background-color: #EFF6FF;
            color: #2563EB;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.5px;
            border: 1px solid #DBEAFE;
        }
        .task-title { font-size: 1.1rem; font-weight: 800; color: #1E293B; margin-top: 8px; margin-bottom: 2px; }
        .task-desc { font-size: 0.85rem; color: #64748B; font-weight: 400; }
        
        .score-card-container { 
            background: #fff; 
            border-left: 5px solid #2563EB; 
            padding: 15px; 
            border-radius: 8px; 
            box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        }
        .score-label { font-weight: 700; letter-spacing: -0.3px; }

        /* 상단 여백 조정 */
        .block-container { padding-top: 3rem; padding-bottom: 5rem; }
        
        button[data-baseweb="tab"] {
            font-family: 'Noto Sans KR', sans-serif !important;
            font-weight: 600 !important;
        }
        </style>
    """, unsafe_allow_html=True)