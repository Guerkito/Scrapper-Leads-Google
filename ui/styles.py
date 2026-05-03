import streamlit as st

def apply_styles():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

        :root {
            --onyx-red: #FF0000;
            --onyx-red-glow: rgba(255, 0, 0, 0.4);
            --onyx-black: #0C0C0E;
            --onyx-card: #16161E;
            --onyx-silver: #E8E8F0;
            --onyx-gray: #1E1E28;
            --glass-bg: rgba(22, 22, 30, 0.85);
            --glass-border: rgba(255, 255, 255, 0.08);
        }

        /* ── Base ── */
        .stApp {
            background-color: var(--onyx-black);
            font-family: 'Inter', sans-serif;
            color: var(--onyx-silver);
        }
        .stApp > header { background: transparent !important; }

        /* Títulos con Space Grotesk */
        h1, h2, h3, .onyx-header {
            font-family: 'Space Grotesk', sans-serif !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
        }

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {
            background: #08080A !important;
            border-right: 1px solid var(--onyx-gray) !important;
        }
        @media (min-width: 768px) {
            [data-testid="stSidebar"] { min-width: 340px !important; }
        }

        /* ── Logo sidebar ── */
        .onyx-logo {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.35rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #FFFFFF;
            text-align: center;
            padding: 1.2rem 0 0.3rem;
            line-height: 1.2;
        }
        .onyx-logo span {
            background: linear-gradient(135deg, #FF0000 0%, #FF4444 50%, #FF0000 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            display: block;
            font-size: 1.75rem;
            letter-spacing: 0.2em;
        }
        .onyx-version {
            font-size: 0.65rem;
            color: #4A4A5A;
            text-align: center;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            margin-top: 2px;
        }

        /* ── Glass Cards Premium & Streamlit native containers ── */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--glass-bg) !important;
            backdrop-filter: blur(16px) !important;
            -webkit-backdrop-filter: blur(16px) !important;
            border: 1px solid var(--glass-border) !important;
            border-radius: 22px !important;
            padding: 28px !important;
            transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1) !important;
            box-shadow: 0 12px 40px rgba(0,0,0,0.5), 
                        0 0 0 1px rgba(255,255,255,0.03) inset !important;
            margin-bottom: 24px !important;
            overflow: hidden !important;
            word-wrap: break-word !important;
            position: relative !important;
            animation: fadeIn 0.7s cubic-bezier(0.23, 1, 0.32, 1) forwards;
        }
        
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: rgba(255, 0, 0, 0.35) !important;
            transform: translateY(-5px) !important;
            box-shadow: 0 20px 50px rgba(255, 0, 0, 0.1),
                        0 0 0 1px rgba(255,255,255,0.08) inset !important;
        }

        /* ── Expanders ── */
        [data-testid="stExpander"] {
            background: #16161E !important;
            border: 1px solid #1E1E28 !important;
            border-radius: 10px !important;
            margin-bottom: 8px;
        }
        [data-testid="stExpander"] summary {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: #8888A0 !important;
        }

        /* ── Buttons ── */
        .stButton > button {
            width: 100% !important;
            border-radius: 12px !important;
            font-family: 'Space Grotesk', sans-serif !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            transition: all 0.3s ease !important;
            padding: 0.6rem 1.2rem !important;
            white-space: normal !important;
            height: auto !important;
            min-height: 45px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #16161E !important;
            color: #FF0000 !important;
            border: 1px solid #2A2A3A !important;
        }
        .stButton > button:hover {
            background: #FF0000 !important;
            color: #FFFFFF !important;
            border-color: #FF0000 !important;
            box-shadow: 0 0 18px rgba(255, 0, 0, 0.3) !important;
            transform: translateY(-2px);
        }
        /* Primary button (INICIAR) */
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #CC0000, #FF2222) !important;
            color: #FFFFFF !important;
            border: none !important;
            box-shadow: 0 2px 12px rgba(255, 0, 0, 0.35) !important;
        }
        .stButton > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #FF0000, #FF4444) !important;
            box-shadow: 0 4px 20px rgba(255, 0, 0, 0.5) !important;
            color: #FFFFFF !important;
        }

        /* ── Metrics ── */
        div[data-testid="stMetric"] {
            background: var(--onyx-card) !important;
            border: 1px solid var(--onyx-gray) !important;
            border-radius: 18px !important;
            padding: 24px !important;
            position: relative;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            transition: all 0.3s ease;
        }
        div[data-testid="stMetric"]:hover {
            transform: scale(1.02);
            border-color: var(--onyx-red);
        }
        div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
            font-family: 'Space Grotesk', sans-serif !important;
            font-size: 0.8rem !important;
            letter-spacing: 0.1em !important;
            text-transform: uppercase !important;
            color: #888898 !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            font-family: 'Space Grotesk', sans-serif !important;
            font-size: 2.2rem !important;
            font-weight: 700 !important;
            color: #FFFFFF !important;
        }
        div[data-testid="stMetric"]::after {
            content: '';
            position: absolute;
            bottom: 0; left: 0; width: 100%; height: 4px;
            background: linear-gradient(90deg, transparent, var(--onyx-red), transparent);
            opacity: 0.6;
        }

        /* ── Page header ── */
        .onyx-header {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 2rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #FFFFFF;
            line-height: 1;
            margin-bottom: 4px;
        }
        .onyx-header-red {
            background: linear-gradient(135deg, #FF0000 0%, #FF4444 50%, #FF0000 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .onyx-subtitle {
            font-size: 0.7rem;
            color: #4A4A5A;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            margin-bottom: 1.5rem;
        }

        /* ── Divider ── */
        hr {
            border: none;
            border-top: 1px solid #1E1E28 !important;
            margin: 1rem 0 !important;
        }

        /* ── Select / Input ── */
        .stSelectbox > div > div,
        .stMultiSelect > div > div,
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input {
            background-color: #12121A !important;
            border: 1px solid var(--onyx-gray) !important;
            border-radius: 10px !important;
            color: #E8E8F0 !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.85rem !important;
        }
        .stSelectbox label, .stMultiSelect label,
        .stTextInput label, .stNumberInput label,
        .stSlider label, .stCheckbox label, .stToggle label {
            font-family: 'Space Grotesk', sans-serif !important;
            font-size: 0.7rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.1em !important;
            text-transform: uppercase !important;
            color: #6A6A7A !important;
        }

        /* ── Toggle / Checkbox ── */
        .stToggle [data-baseweb="checkbox"] span {
            background: #FF0000 !important;
        }

        /* ── Slider ── */
        .stSlider [data-baseweb="slider"] div[role="slider"] {
            background: #FF0000 !important;
        }

        /* ── Radio (vista) ── */
        .stRadio > div {
            background: #16161E;
            border-radius: 10px;
            padding: 6px 8px;
            border: 1px solid #1E1E28;
            gap: 4px;
        }
        .stRadio label {
            font-family: 'Space Grotesk', sans-serif !important;
            font-size: 0.75rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
            color: #6A6A7A !important;
        }

        /* ── Data Editor ── */
        .stDataFrame, [data-testid="stDataEditor"] {
            border-radius: 10px !important;
            overflow: hidden !important;
            border: 1px solid #1E1E28 !important;
        }

        /* ── Download button ── */
        .stDownloadButton > button {
            background: #16161E !important;
            color: #FF0000 !important;
            border: 1px solid #2A2A3A !important;
            border-radius: 8px !important;
            font-family: 'Space Grotesk', sans-serif !important;
            font-weight: 600 !important;
            font-size: 0.8rem !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
            width: 100% !important;
            transition: all 0.2s ease !important;
        }
        .stDownloadButton > button:hover {
            background: #FF0000 !important;
            color: #FFFFFF !important;
            border-color: #FF0000 !important;
        }

        /* ── Caption / small text ── */
        .stCaption, small, .stCaption p {
            color: #5A5A6A !important;
            font-size: 0.72rem !important;
        }

        /* ── Success / Warning / Error ── */
        .stSuccess { background: rgba(255, 0, 0, 0.06) !important; border-left: 3px solid #FF0000 !important; }
        .stWarning { background: rgba(200, 120, 40, 0.08) !important; border-left: 3px solid #C87828 !important; }
        .stError   { background: rgba(200, 30, 30, 0.10) !important; border-left: 3px solid #FF0000 !important; }

        /* ── Navbar ── */
        .nav-container {
            display: flex;
            justify-content: center;
            gap: 10px;
            padding: 10px 0;
            margin-bottom: 30px;
        }
        .stButton > button.nav-btn-active {
            background: linear-gradient(135deg, #FF0000 0%, #CC0000 100%) !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 15px rgba(255, 0, 0, 0.4) !important;
            transform: translateY(-2px);
        }

        /* Consola de Logs ── */
        .console-box {
            background: #000000;
            color: #00FF9D;
            font-family: 'Fira Code', 'Courier New', monospace;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #1E1E28;
            box-shadow: inset 0 0 20px rgba(0,255,157,0.05);
            height: 250px;
            overflow-y: auto;
            font-size: 0.8rem;
            line-height: 1.5;
        }

        /* KPI Card Personalizada */
        .onyx-card {
            background: var(--onyx-card);
            border: 1px solid var(--onyx-gray);
            border-radius: 18px;
            transition: all 0.3s ease;
        }
        .onyx-card:hover {
            transform: scale(1.02);
            border-color: var(--onyx-red);
        }

        /* Animaciones */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .onyx-animate {
            animation: fadeIn 0.7s cubic-bezier(0.23, 1, 0.32, 1) forwards;
        }

        /* Responsive */
        @media (max-width: 640px) {
            .onyx-header { font-size: 1.4rem; }
            div[data-testid="stMetric"] { margin-bottom: 8px; }
        }
        </style>
    """, unsafe_allow_html=True)
