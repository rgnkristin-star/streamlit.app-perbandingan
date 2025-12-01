import streamlit as st
from themes import get_theme_css


class NavigationHeader:
    def __init__(self, session):
        self.session = session
        self._initialize_session_state()

    def _initialize_session_state(self):
        """Initialize session state untuk navigation"""
        if "active_tab" not in st.session_state:
            st.session_state.active_tab = "Upload Data"

    def render_navigation_header(self):
        """Render navigation header dengan tabs"""

        theme_css = get_theme_css(st.session_state.theme)
        st.markdown(theme_css, unsafe_allow_html=True)

        self._render_main_header()

        self._render_navigation_tabs()

    def _render_main_header(self):
        """Render bagian utama header"""
        st.markdown(
            """
            <div style='
                background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
                padding: 1.5rem;
                border-radius: 10px;
                margin-bottom: 1rem;
                color: white;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            '>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div>
                        <h1 style='margin: 0; color: white; font-size: 2rem;'>🏥 HNA Comparison System</h1>
                        <p style='margin: 0; opacity: 0.9;'>Sistem Perbandingan Harga Obat dan Pemeriksaan Penunjang</p>
                    </div>
                    <div style='text-align: right;'>
                        <div style='
                            background: rgba(255,255,255,0.2); 
                            padding: 0.5rem 1rem; 
                            border-radius: 20px; 
                            display: inline-block; 
                            margin-left: 1rem;
                            backdrop-filter: blur(10px);
                        '>
                            <strong>👤</strong> {username}
                        </div>
                        <div style='
                            background: {role_color}; 
                            padding: 0.5rem 1rem; 
                            border-radius: 20px; 
                            display: inline-block; 
                            margin-left: 1rem;
                            color: white;
                        '>
                            <strong>🎯</strong> {role}
                        </div>
                    </div>
                </div>
            </div>
            """.format(
                username=st.session_state.get("username", "Guest"),
                role=st.session_state.get("role", "guest").upper(),
                role_color=(
                    "#28a745"
                    if st.session_state.get("role") == "user"
                    else (
                        "#dc3545"
                        if st.session_state.get("role") == "admin"
                        else "#6c757d"
                    )
                ),
            ),
            unsafe_allow_html=True,
        )

    def _render_navigation_tabs(self):
        """Render navigation tabs"""

        menu_items = self._get_menu_items()

        tab_titles = [item["label"] for item in menu_items]

        cols = st.columns(len(menu_items))

        selected_tab = st.session_state.active_tab

        for idx, (col, menu_item) in enumerate(zip(cols, menu_items)):
            with col:
                is_active = selected_tab == menu_item["value"]
                button_style = self._get_tab_style(is_active)

                if st.button(
                    menu_item["label"],
                    key=f"nav_tab_{idx}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state.active_tab = menu_item["value"]
                    st.rerun()

    def _get_tab_style(self, is_active):
        """Return style untuk tab berdasarkan status aktif"""
        if is_active:
            return {"background": "#007bff", "color": "white"}
        else:
            return {"background": "#f8f9fa", "color": "#495057"}

    def _get_menu_items(self):
        """Get available menu items based on user role"""
        base_menus = [
            {
                "label": "📤 Upload HNA",
                "value": "Upload Data",
                "roles": ["user", "admin"],
            },
            {
                "label": "📊 Data HNA",
                "value": "Tampilan Data",
                "roles": ["user", "admin"],
            },
            {
                "label": "🩺 Upload Penunjang",
                "value": "Upload Penunjang",
                "roles": ["user", "admin"],
            },
            {
                "label": "📋 Data Penunjang",
                "value": "Tampilan Penunjang",
                "roles": ["user", "admin"],
            },
        ]

        user_role = st.session_state.get("role", "guest")
        filtered_menus = [menu for menu in base_menus if user_role in menu["roles"]]

        if user_role == "admin":
            filtered_menus.append(
                {
                    "label": "👥 Manajemen User",
                    "value": "Manajemen User",
                    "roles": ["admin"],
                }
            )

        return filtered_menus

    def get_active_tab(self):
        """Get active tab value"""
        return st.session_state.active_tab

    def set_active_tab(self, tab_value):
        """Set active tab"""
        st.session_state.active_tab = tab_value
