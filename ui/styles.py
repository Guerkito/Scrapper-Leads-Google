import streamlit as st

def apply_styles():
    st.markdown("""
        <style>
        :root {
            --onyx-red: #DC2626;
            --onyx-red-hover: #EF4444;
            --onyx-red-glow: rgba(220, 38, 38, 0.24);
            --onyx-black: #070B12;
            --onyx-card: #111827;
            --onyx-silver: #F8FAFC;
            --onyx-muted: #A7B2C4;
            --onyx-gray: #273449;
            --glass-bg: rgba(17, 24, 39, 0.94);
            --glass-border: #273449;
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
            [data-testid="stSidebar"] { min-width: 280px !important; max-width: 300px !important; }
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
            border: 1px solid var(--glass-border) !important;
            border-radius: 22px !important;
            padding: 28px !important;
            transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease !important;
            box-shadow: 0 12px 40px rgba(0,0,0,0.5), 
                        0 0 0 1px rgba(255,255,255,0.03) inset !important;
            margin-bottom: 24px !important;
            overflow: hidden !important;
            word-wrap: break-word !important;
            position: relative !important;
        }
        
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: rgba(255, 0, 0, 0.35) !important;
            transform: translateY(-2px) !important;
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
            font-size: 0.74rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.025em !important;
            transition: all 0.3s ease !important;
            padding: 0.55rem 0.45rem !important;
            white-space: nowrap !important;
            height: auto !important;
            min-height: 45px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #16161E !important;
            color: #FF0000 !important;
            border: 1px solid #2A2A3A !important;
        }
        .stButton > button p,
        .stButton > button [data-testid="stMarkdownContainer"] {
            font-size: inherit !important;
            line-height: 1.1 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
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
        .onyx-svg-title {
            display: flex;
            align-items: center;
            gap: 10px;
            color: #FFFFFF;
            margin: 0 0 16px;
        }
        .onyx-svg-title svg {
            color: #FF0000;
            flex: 0 0 auto;
            filter: drop-shadow(0 0 8px rgba(255, 0, 0, 0.35));
        }
        .onyx-svg-title h2,
        .onyx-svg-title h3,
        .onyx-svg-title h4 {
            margin: 0 !important;
            padding: 0 !important;
            font-family: 'Space Grotesk', sans-serif !important;
            font-weight: 700 !important;
            letter-spacing: 0.02em !important;
            color: #FFFFFF !important;
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
        .stNumberInput > div > div > input,
        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input {
            background-color: #12121A !important;
            border: 1px solid var(--onyx-gray) !important;
            border-radius: 10px !important;
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.85rem !important;
        }
        /* Forzar que el texto del input al escribir sea siempre claro */
        input {
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
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
            transform: none;
            border-color: var(--onyx-gray);
        }

        /* Animaciones */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .onyx-animate {
            animation: fadeIn 0.25s ease-out forwards;
        }

        /* ── Capa de usabilidad: jerarquía, contraste y densidad ── */
        [data-testid="stMainBlockContainer"] {
            max-width: 1380px !important;
            padding-top: 2rem !important;
            padding-bottom: 3rem !important;
        }

        p, li {
            line-height: 1.55;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            padding: 20px !important;
            border-radius: 14px !important;
            margin-bottom: 16px !important;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.22) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: var(--glass-border) !important;
            transform: none !important;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.22) !important;
        }

        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stLinkButton"] a {
            min-height: 44px !important;
            border-radius: 10px !important;
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif !important;
            font-size: 0.84rem !important;
            font-weight: 650 !important;
            letter-spacing: 0 !important;
            text-transform: none !important;
            transition: background-color 160ms ease, border-color 160ms ease, color 160ms ease !important;
        }
        .stButton > button:hover,
        .stDownloadButton > button:hover {
            transform: none !important;
            box-shadow: none !important;
        }
        .stButton > button:disabled,
        .stDownloadButton > button:disabled {
            cursor: not-allowed !important;
            opacity: 0.48 !important;
            filter: saturate(0.45) !important;
        }
        .stButton > button[kind="secondary"] {
            background: #151D2C !important;
            color: #E2E8F0 !important;
            border-color: #334155 !important;
        }
        .stButton > button[kind="secondary"]:hover {
            background: #1E293B !important;
            color: #FFFFFF !important;
            border-color: #475569 !important;
        }
        .stButton > button[kind="primary"] {
            background: #B91C1C !important;
            border: 1px solid #DC2626 !important;
            box-shadow: 0 3px 12px rgba(185, 28, 28, 0.24) !important;
        }
        .stButton > button[kind="primary"]:hover {
            background: #991B1B !important;
            border-color: #EF4444 !important;
            box-shadow: none !important;
        }
        .stButton > button p,
        .stButton > button [data-testid="stMarkdownContainer"] {
            white-space: normal !important;
            line-height: 1.25 !important;
        }
        .stButton > button:focus-visible,
        .stDownloadButton > button:focus-visible,
        input:focus-visible,
        [role="combobox"]:focus-visible {
            outline: 3px solid rgba(248, 113, 113, 0.72) !important;
            outline-offset: 2px !important;
        }

        .stSelectbox label, .stMultiSelect label,
        .stTextInput label, .stNumberInput label,
        .stSlider label, .stCheckbox label, .stToggle label,
        .stRadio label {
            color: #CBD5E1 !important;
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif !important;
            font-size: 0.82rem !important;
            font-weight: 600 !important;
            letter-spacing: 0 !important;
            text-transform: none !important;
        }
        .stCaption, small, .stCaption p,
        [data-testid="stCaptionContainer"] p {
            color: #94A3B8 !important;
            font-size: 0.8rem !important;
            line-height: 1.45 !important;
        }
        .stSuccess {
            background: rgba(34, 197, 94, 0.10) !important;
            border-left: 3px solid #22C55E !important;
        }
        .stWarning {
            background: rgba(245, 158, 11, 0.10) !important;
            border-left: 3px solid #F59E0B !important;
        }
        .stError {
            background: rgba(239, 68, 68, 0.10) !important;
            border-left: 3px solid #EF4444 !important;
        }

        .onyx-header {
            font-size: clamp(1.65rem, 3vw, 2.25rem);
            letter-spacing: -0.03em;
            text-transform: none;
        }
        .onyx-subtitle {
            color: var(--onyx-muted);
            font-size: 0.88rem;
            letter-spacing: 0;
            text-transform: none;
            margin: 0.35rem 0 1rem;
        }
        .onyx-svg-title {
            margin-bottom: 10px;
        }
        .onyx-svg-title svg {
            color: #F87171;
            filter: none;
        }
        .onyx-svg-title h2,
        .onyx-svg-title h3,
        .onyx-svg-title h4 {
            letter-spacing: -0.01em !important;
        }

        .sidebar-label {
            color: #94A3B8;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin: 0 0 10px;
        }
        .connection-status {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            border: 1px solid var(--onyx-gray);
            background: var(--onyx-card);
            border-radius: 10px;
        }
        .connection-status .connection-dot {
            width: 9px;
            height: 9px;
            border-radius: 999px;
            background: #94A3B8;
            box-shadow: 0 0 0 4px rgba(148, 163, 184, 0.12);
        }
        .connection-status[data-status="success"] .connection-dot {
            background: #22C55E;
            box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.13);
        }
        .connection-status[data-status="warning"] .connection-dot {
            background: #F59E0B;
        }
        .connection-status[data-status="error"] .connection-dot {
            background: #EF4444;
        }
        .connection-status small,
        .connection-status strong {
            display: block;
        }
        .connection-status small {
            color: #94A3B8 !important;
            font-size: 0.72rem !important;
        }
        .connection-status strong {
            color: #F8FAFC;
            font-size: 0.82rem;
        }

        .st-key-main_navigation {
            margin-bottom: 12px;
        }
        .st-key-main_navigation .stButton > button {
            min-height: 40px !important;
            padding: 0.45rem 0.65rem !important;
        }
        .st-key-main_navigation .stButton > button[kind="secondary"] {
            color: #CBD5E1 !important;
            background: transparent !important;
            border-color: transparent !important;
        }
        .st-key-main_navigation .stButton > button[kind="secondary"]:hover {
            color: #FFFFFF !important;
            background: #172033 !important;
        }

        .overview-strip {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            background: rgba(17, 24, 39, 0.72);
            border: 1px solid var(--onyx-gray);
            border-radius: 12px;
            margin: 0 0 18px;
            overflow: hidden;
        }
        .overview-item {
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 1px 10px;
            padding: 12px 16px;
            border-right: 1px solid var(--onyx-gray);
        }
        .overview-item:last-child { border-right: 0; }
        .overview-item span {
            color: #CBD5E1;
            font-size: 0.78rem;
            font-weight: 600;
        }
        .overview-item strong {
            grid-row: span 2;
            align-self: center;
            color: #FFFFFF;
            font-size: 1.3rem;
            line-height: 1;
        }
        .overview-item small {
            color: #7F8CA3 !important;
            font-size: 0.7rem !important;
        }

        .workflow-steps {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 8px;
            margin-bottom: 18px;
        }
        .workflow-step {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #94A3B8;
            font-size: 0.77rem;
            font-weight: 600;
        }
        .workflow-step b {
            display: grid;
            place-items: center;
            width: 24px;
            height: 24px;
            border: 1px solid #3B4A61;
            border-radius: 999px;
            color: #F8FAFC;
            background: #172033;
            font-size: 0.72rem;
        }
        .campaign-summary,
        .premium-terms-box {
            border: 1px solid #334155;
            border-left: 3px solid #DC2626;
            border-radius: 10px;
            background: #0D1422;
            padding: 14px 16px;
            margin: 10px 0 14px;
            color: #CBD5E1;
            font-size: 0.84rem;
            line-height: 1.5;
        }
        .campaign-summary strong { color: #FFFFFF; }
        .campaign-summary p { margin: 0 0 7px; }
        .campaign-summary p:last-child { margin-bottom: 0; }
        .badges-wrapper {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }
        .premium-badge {
            display: inline-flex;
            align-items: center;
            min-height: 28px;
            padding: 4px 9px;
            border: 1px solid #3B4A61;
            border-radius: 7px;
            background: #172033;
            color: #E2E8F0;
            font-size: 0.76rem;
            font-weight: 600;
        }

        [data-testid="stExpander"] summary {
            color: #CBD5E1 !important;
            font-family: Inter, ui-sans-serif, system-ui, sans-serif !important;
            font-size: 0.84rem !important;
            letter-spacing: 0 !important;
            text-transform: none !important;
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }

        /* Responsive */
        @media (max-width: 900px) {
            .overview-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .overview-item:nth-child(2) { border-right: 0; }
            .overview-item:nth-child(-n + 2) { border-bottom: 1px solid var(--onyx-gray); }
            .workflow-steps { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .st-key-main_navigation [data-testid="stHorizontalBlock"] {
                display: grid !important;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 6px !important;
            }
        }
        @media (max-width: 640px) {
            [data-testid="stMainBlockContainer"] {
                padding: 4.5rem 1rem 2rem !important;
            }
            .onyx-header { font-size: 1.5rem; }
            .overview-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .overview-item { padding: 11px 12px; }
            .overview-item:nth-child(odd) { border-right: 1px solid var(--onyx-gray); }
            .overview-item:nth-child(even) { border-right: 0; }
            .overview-item:nth-child(-n + 2) { border-bottom: 1px solid var(--onyx-gray); }
            .overview-item:nth-child(n + 3) { border-bottom: 0; }
            .overview-item strong { font-size: 1.15rem; }
            .workflow-steps { grid-template-columns: 1fr 1fr; }
            .st-key-main_navigation [data-testid="stHorizontalBlock"] {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            div[data-testid="stVerticalBlockBorderWrapper"] { padding: 14px !important; }
        }
        </style>
    """, unsafe_allow_html=True)
