import streamlit as st

def apply_styles():
    st.markdown("""
        <style>
        /* ================================================================
           ONYX LeadGen — Product Design System
           Dark, calm, professional. Accent: crimson. Surfaces: slate.
           Maintained in ui/styles.py — keep selectors alongside views.
           ================================================================ */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

        :root {
            --bg:          #0A0C10;
            --bg-2:        #0E1116;
            --surface:     #12151C;
            --surface-2:   #161A22;
            --surface-3:   #1B2029;
            --border:      #232836;
            --border-soft: #1B2029;
            --text:        #E6E9EF;
            --text-2:      #98A2B3;
            --text-3:      #6B7485;

            --accent:      #E5484D;
            --accent-strong:#F2555A;
            --accent-soft: rgba(229, 72, 77, 0.12);
            --accent-soft-2:rgba(229, 72, 77, 0.20);

            --green:  #46A758;
            --green-soft: rgba(70, 167, 88, 0.12);
            --amber:  #F5A524;
            --amber-soft: rgba(245, 165, 36, 0.12);
            --blue:   #5D9DF0;
            --blue-soft: rgba(93, 157, 240, 0.12);
            --violet: #A384F0;
            --violet-soft: rgba(163, 132, 240, 0.12);

            --radius: 12px;
            --radius-sm: 8px;
            --shadow: 0 1px 2px rgba(0,0,0,0.35), 0 8px 24px rgba(0,0,0,0.18);
        }

        html, body { scroll-behavior: smooth; }

        .stApp {
            background: var(--bg);
            font-family: 'Inter', -apple-system, ui-sans-serif, system-ui, sans-serif;
            color: var(--text);
        }
        .stApp > header { background: transparent !important; }

        /* ── Display type ── */
        h1, h2, h3, .onyx-header {
            font-family: 'Space Grotesk', 'Inter', sans-serif !important;
            font-weight: 700 !important;
            letter-spacing: -0.022em !important;
            color: var(--text) !important;
        }
        h4, h5, h6 {
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            letter-spacing: -0.01em !important;
            color: var(--text) !important;
        }

        /* ════════════════════════ SIDEBAR ════════════════════════ */
        [data-testid="stSidebar"] {
            background: var(--bg-2) !important;
            border-right: 1px solid var(--border-soft) !important;
        }
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top: 0.5rem; }
        @media (min-width: 768px) {
            [data-testid="stSidebar"] { min-width: 264px !important; max-width: 288px !important; }
        }

        .onyx-logo { text-align: left; padding: 1.1rem 0 0.15rem; line-height: 1.05; }
        .onyx-logo .l1 {
            font-family: 'Space Grotesk', sans-serif; font-size: 1.05rem; font-weight: 700;
            letter-spacing: 0.16em; text-transform: uppercase; color: var(--text-2);
        }
        .onyx-logo .l2 {
            font-family: 'Space Grotesk', sans-serif; font-size: 1.7rem; font-weight: 700;
            letter-spacing: 0.02em; color: #FFFFFF; display: block; margin-top: 2px;
            background: linear-gradient(135deg, #FF7B7B 0%, var(--accent-strong) 55%, #C93A3F 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
        }
        .onyx-version {
            color: var(--text-3); font-size: 0.7rem; letter-spacing: 0.1em;
            text-transform: uppercase; margin-bottom: 0.25rem;
        }

        .sidebar-label {
            color: var(--text-3); font-size: 0.68rem; font-weight: 700;
            letter-spacing: 0.12em; text-transform: uppercase; margin: 0 0 6px;
        }
        .sidebar-label:first-of-type { margin-top: 0.4rem; }

        .connection-status {
            display: flex; align-items: center; gap: 10px; padding: 9px 11px;
            border: 1px solid var(--border); background: var(--surface);
            border-radius: 10px; margin-bottom: 2px;
        }
        .connection-status .connection-dot {
            width: 8px; height: 8px; border-radius: 999px; background: var(--text-3);
            box-shadow: 0 0 0 3px rgba(107, 116, 133, 0.12); flex: 0 0 auto;
        }
        .connection-status[data-status="success"] .connection-dot { background: var(--green); box-shadow: 0 0 0 3px var(--green-soft); }
        .connection-status[data-status="warning"] .connection-dot { background: var(--amber); box-shadow: 0 0 0 3px var(--amber-soft); }
        .connection-status[data-status="error"]   .connection-dot { background: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
        .connection-status small { color: var(--text-3) !important; font-size: 0.7rem !important; display: block; }
        .connection-status strong { color: var(--text); font-size: 0.8rem; display: block; }

        /* Sidebar nav buttons */
        [data-testid="stSidebar"] .stButton > button {
            justify-content: flex-start !important;
            min-height: 38px !important;
            padding: 0.42rem 0.8rem !important;
            border-radius: 9px !important;
            font-weight: 600 !important;
            font-size: 0.84rem !important;
            color: var(--text-2) !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            transition: background-color 140ms ease, color 140ms ease !important;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            color: var(--text) !important;
            background: var(--surface-2) !important;
        }
        [data-testid="stSidebar"] .stButton > button[kind="primary"] {
            color: #FFFFFF !important;
            background: linear-gradient(180deg, var(--accent-strong), var(--accent)) !important;
            border-color: transparent !important;
            box-shadow: 0 2px 10px rgba(229, 72, 77, 0.30) !important;
        }

        /* ════════════════════════ PAGE LAYOUT ════════════════════════ */
        [data-testid="stMainBlockContainer"] {
            max-width: 1320px !important;
            padding-top: 1.5rem !important;
            padding-bottom: 3rem !important;
        }

        .page-kicker {
            font-size: 0.68rem; font-weight: 700; letter-spacing: 0.14em;
            text-transform: uppercase; color: var(--accent); margin-bottom: 6px;
        }
        .onyx-header {
            font-size: clamp(1.5rem, 2.6vw, 2rem) !important;
            line-height: 1.1; margin-bottom: 2px !important;
            letter-spacing: -0.03em !important;
        }
        .onyx-header-red { display: none; }
        .onyx-subtitle {
            color: var(--text-2); font-size: 0.9rem; margin: 0 0 1.4rem;
        }

        .onyx-svg-title { display: flex; align-items: center; gap: 9px; color: var(--text); margin: 0 0 12px; }
        .onyx-svg-title svg { color: var(--accent); flex: 0 0 auto; }
        .onyx-svg-title h2, .onyx-svg-title h3, .onyx-svg-title h4 { margin: 0 !important; padding: 0 !important; }
        .onyx-svg-title h2 { font-size: 1.55rem !important; }
        .onyx-svg-title h3 { font-size: 1.3rem !important; }
        .onyx-svg-title h4 { font-family: 'Space Grotesk', sans-serif !important; font-size: 1.02rem !important; }

        /* ════════════════════════ WIDGET BASICS ════════════════════════ */
        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stLinkButton"] a {
            min-height: 40px !important;
            border-radius: 9px !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.84rem !important;
            font-weight: 600 !important;
            letter-spacing: 0 !important;
            transition: background-color 140ms ease, border-color 140ms ease, color 140ms ease, transform 80ms ease !important;
        }
        .stButton > button[kind="secondary"] {
            background: var(--surface-2) !important;
            color: var(--text-2) !important;
            border: 1px solid var(--border) !important;
        }
        .stButton > button[kind="secondary"]:hover {
            background: var(--surface-3) !important;
            color: var(--text) !important;
            border-color: #2E3542 !important;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(180deg, var(--accent-strong), var(--accent)) !important;
            border: 1px solid transparent !important;
            color: #FFFFFF !important;
            box-shadow: 0 2px 10px rgba(229, 72, 77, 0.28) !important;
        }
        .stButton > button[kind="primary"]:hover { filter: brightness(1.08); }
        .stButton > button:active, .stDownloadButton > button:active { transform: translateY(1px); }
        .stButton > button:focus-visible, .stDownloadButton > button:focus-visible,
        input:focus-visible, [role="combobox"]:focus-visible {
            outline: 2px solid rgba(242, 85, 90, 0.7) !important;
            outline-offset: 2px !important;
        }

        [data-testid="stLinkButton"] a {
            background: var(--surface-2) !important; color: var(--text-2) !important;
            border: 1px solid var(--border) !important; text-decoration: none !important;
        }
        [data-testid="stLinkButton"] a:hover {
            background: var(--surface-3) !important; color: var(--text) !important;
            border-color: #2E3542 !important; text-decoration: none !important;
        }
        [data-testid="stLinkButton"] a[kind="primary"] {
            background: linear-gradient(180deg, var(--accent-strong), var(--accent)) !important;
            border-color: transparent !important; color: #FFFFFF !important;
            box-shadow: 0 2px 10px rgba(229, 72, 77, 0.28) !important;
        }
        [data-testid="stLinkButton"] a[kind="primary"]:hover { filter: brightness(1.08); color: #FFFFFF !important; }

        .stSelectbox label, .stMultiSelect label, .stTextInput label,
        .stNumberInput label, .stSlider label, .stCheckbox label,
        .stToggle label, .stRadio label, .stTextArea label {
            color: var(--text-2) !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.8rem !important;
            font-weight: 600 !important;
            letter-spacing: 0 !important;
            text-transform: none !important;
        }

        .stSelectbox > div > div,
        .stMultiSelect > div > div,
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stTextArea textarea {
            background-color: var(--surface-2) !important;
            border: 1px solid var(--border) !important;
            border-radius: 9px !important;
            color: var(--text) !important;
            -webkit-text-fill-color: var(--text) !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.85rem !important;
        }
        .stTextArea textarea { font-size: 0.86rem !important; }

        .stCheckbox [data-testid="stCheckbox"] [data-baseweb="checkbox"],
        .stToggle [data-baseweb="checkbox"], .stToggle [data-baseweb="baseweb-switch"] {
            border-color: var(--border) !important;
        }
        .stToggle [data-testid="stToggle"] [role="switch"],
        .stToggle [data-baseweb="baseweb-switch"] { background: var(--accent) !important; }
        .stSlider [data-baseweb="slider"] div[role="slider"] { background: var(--accent) !important; }

        .stRadio > div {
            background: var(--surface-2); border-radius: 9px; padding: 5px 7px;
            border: 1px solid var(--border);
        }
        .stRadio label { font-size: 0.8rem !important; font-weight: 600 !important; color: var(--text-2) !important; }

        .stCaption, small, .stCaption p, [data-testid="stCaptionContainer"] p {
            color: var(--text-3) !important;
            font-size: 0.78rem !important;
            line-height: 1.5 !important;
        }

        /* ════════════════════════ PANELS & CARDS ════════════════════════ */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--surface) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius) !important;
            padding: 18px 20px !important;
            margin-bottom: 14px !important;
            box-shadow: none !important;
            word-wrap: break-word !important;
        }

        /* KPI cards (st.metric & custom) */
        div[data-testid="stMetric"] {
            background: var(--surface) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius) !important;
            padding: 16px 18px !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
            font-family: 'Inter', sans-serif !important; font-size: 0.72rem !important;
            font-weight: 600 !important; letter-spacing: 0.02em !important;
            text-transform: none !important; color: var(--text-3) !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            font-family: 'Space Grotesk', sans-serif !important; font-size: 1.7rem !important;
            font-weight: 700 !important; color: var(--text) !important;
        }

        .onyx-card {
            background: var(--surface); border: 1px solid var(--border);
            border-radius: var(--radius); transition: border-color 160ms ease, transform 160ms ease;
        }
        .onyx-card:hover { border-color: #2E3542; }

        .kpi-value { font-family: 'Space Grotesk', sans-serif; font-weight: 700; color: var(--text); font-size: 1.9rem; line-height: 1; }
        .kpi-label { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.07em; text-transform: uppercase; color: var(--text-3); }

        /* ════════════════════════ ALERTS / FEEDBACK ════════════════════════ */
        .stSuccess { background: var(--green-soft) !important; border-left: 3px solid var(--green) !important; color: var(--text) !important; }
        .stWarning { background: var(--amber-soft) !important; border-left: 3px solid var(--amber) !important; color: var(--text) !important; }
        .stError   { background: var(--accent-soft) !important; border-left: 3px solid var(--accent) !important; color: var(--text) !important; }
        .stInfo    { background: var(--blue-soft) !important; border-left: 3px solid var(--blue) !important; color: var(--text) !important; }

        /* ════════════════════════ EXPANDERS ════════════════════════ */
        [data-testid="stExpander"] {
            background: var(--surface-2) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-sm) !important;
        }
        [data-testid="stExpander"] summary {
            color: var(--text-2) !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.84rem !important;
            font-weight: 600 !important;
            letter-spacing: 0 !important;
            text-transform: none !important;
        }

        /* ════════════════════════ TABLES / DATA ════════════════════════ */
        .stDataFrame, [data-testid="stDataEditor"] {
            border-radius: var(--radius-sm) !important;
            overflow: hidden !important;
            border: 1px solid var(--border) !important;
        }

        hr { border: none; border-top: 1px solid var(--border-soft) !important; margin: 1rem 0 !important; }

        .stDownloadButton > button {
            background: var(--surface-2) !important; color: var(--text) !important;
            border: 1px solid var(--border) !important;
        }
        .stDownloadButton > button:hover { background: var(--surface-3) !important; border-color: #2E3542 !important; }

        /* ════════════════════════ CUSTOM PRIMITIVES ════════════════════════ */

        /* Workflow steps (search) */
        .workflow-steps {
            display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 6px;
            margin-bottom: 18px;
        }
        .workflow-step {
            display: flex; align-items: center; gap: 8px;
            padding: 9px 11px; border: 1px solid var(--border);
            background: var(--surface-2); border-radius: 9px;
            color: var(--text-3); font-size: 0.76rem; font-weight: 600;
        }
        .workflow-step b {
            display: grid; place-items: center; width: 21px; height: 21px;
            border: 1px solid var(--border); border-radius: 999px;
            color: var(--text-2); background: var(--surface-3); font-size: 0.68rem;
        }
        .workflow-step.is-active { border-color: rgba(229,72,77,0.45); background: var(--accent-soft); color: var(--text); }
        .workflow-step.is-active b { background: var(--accent); border-color: var(--accent); color: #fff; }

        /* Chips & badges */
        .badges-wrapper { display: flex; flex-wrap: wrap; gap: 6px; }
        .premium-badge {
            display: inline-flex; align-items: center; min-height: 26px;
            padding: 3px 10px; border: 1px solid var(--border); border-radius: 7px;
            background: var(--surface-3); color: var(--text-2);
            font-size: 0.76rem; font-weight: 600;
        }
        .onyx-chip {
            display: inline-flex; align-items: center; gap: 6px;
            padding: 3px 10px; border-radius: 999px; font-size: 0.72rem; font-weight: 600;
        }
        .onyx-chip.neutral { background: var(--surface-3); color: var(--text-2); border: 1px solid var(--border); }
        .onyx-chip.accent  { background: var(--accent-soft-2); color: #FF8A8D; }
        .onyx-chip.green   { background: var(--green-soft); color: #7FD391; }
        .onyx-chip.amber   { background: var(--amber-soft); color: #F8C46A; }
        .onyx-chip.blue    { background: var(--blue-soft); color: #A9CBF7; }
        .onyx-chip.violet  { background: var(--violet-soft); color: #CBAEEF; }

        /* Summary / pitch boxes */
        .campaign-summary, .premium-terms-box {
            border: 1px solid var(--border);
            border-left: 3px solid var(--accent);
            border-radius: 10px; background: var(--surface-2);
            padding: 13px 15px; margin: 10px 0 14px;
            color: var(--text-2); font-size: 0.83rem; line-height: 1.55;
        }
        .campaign-summary strong { color: var(--text); }
        .campaign-summary p { margin: 0 0 6px; }
        .campaign-summary p:last-child { margin-bottom: 0; }

        /* Overview / KPI strip */
        .overview-strip {
            display: grid; grid-template-columns: repeat(4, minmax(0,1fr));
            gap: 10px; margin: 0 0 20px;
        }
        .overview-item {
            background: var(--surface); border: 1px solid var(--border);
            border-radius: var(--radius); padding: 13px 15px;
            display: flex; flex-direction: column; gap: 2px;
        }
        .overview-item span { color: var(--text-3); font-size: 0.72rem; font-weight: 600; }
        .overview-item strong { color: var(--text); font-family: 'Space Grotesk', sans-serif; font-size: 1.45rem; line-height: 1.15; }
        .overview-item small { color: var(--text-3) !important; font-size: 0.7rem !important; }

        /* Console (mission logs) */
        .console-box {
            background: #06080C; color: #8BE9A3;
            font-family: 'SF Mono', 'Fira Code', ui-monospace, monospace;
            padding: 14px 16px; border-radius: 10px;
            border: 1px solid var(--border);
            height: 210px; overflow-y: auto; font-size: 0.76rem; line-height: 1.6;
        }

        /* Feed / pipeline rows (dashboard) */
        .pipeline-row {
            display: grid; grid-template-columns: minmax(140px,1.4fr) 1fr 1fr auto;
            gap: 10px; align-items: center; padding: 10px 12px;
            border-bottom: 1px solid var(--border-soft);
            font-size: 0.82rem; color: var(--text-2);
        }
        .pipeline-row:last-child { border-bottom: 0; }
        .pipeline-row .pv { font-family: 'Space Grotesk', sans-serif; font-weight: 600; color: var(--text); }
        .pipeline-row .head { color: var(--text-3); font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; }
        .pipeline-bar { height: 5px; border-radius: 999px; background: var(--surface-3); overflow: hidden; }
        .pipeline-bar > div { height: 100%; border-radius: 999px; background: var(--accent); }

        .feed-item {
            display: flex; gap: 11px; align-items: center; padding: 9px 12px;
            border-radius: 9px; transition: background-color 120ms ease;
        }
        .feed-item:hover { background: var(--surface-2); }
        .feed-item .feed-avatar {
            width: 34px; height: 34px; border-radius: 9px; flex: 0 0 auto;
            background: var(--surface-3); border: 1px solid var(--border);
            display: grid; place-items: center; color: var(--text-2);
            font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 0.78rem;
        }

        /* Empty state */
        .empty-state {
            border: 1px dashed var(--border); border-radius: var(--radius);
            padding: 34px 20px; text-align: center; color: var(--text-3);
            font-size: 0.86rem; background: rgba(18,21,28,0.5);
        }
        .empty-state b { color: var(--text-2); }

        /* Progress & monitor */
        .mission-status {
            display: inline-flex; align-items: center; gap: 8px;
            font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
            color: #7FD391;
        }
        .mission-status::before {
            content: ''; width: 8px; height: 8px; border-radius: 999px;
            background: var(--green); box-shadow: 0 0 0 4px var(--green-soft);
            animation: onyx-pulse 1.6s ease-in-out infinite;
        }
        @keyframes onyx-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.45; } }

        /* ════════════════════════ RESPONSIVE ════════════════════════ */
        @media (max-width: 900px) {
            .overview-strip { grid-template-columns: repeat(2, minmax(0,1fr)); }
            .workflow-steps { grid-template-columns: repeat(2, minmax(0,1fr)); }
        }
        @media (max-width: 640px) {
            [data-testid="stMainBlockContainer"] { padding: 1rem 0.9rem 2rem !important; }
            .onyx-header { font-size: 1.4rem !important; }
            .overview-strip { grid-template-columns: repeat(1, minmax(0,1fr)); }
            div[data-testid="stVerticalBlockBorderWrapper"] { padding: 14px !important; }
        }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
        </style>
    """, unsafe_allow_html=True)
