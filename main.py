import streamlit as st
import pandas as pd
import io
from db import SessionLocal
from models import HNAData, format_currency_id
from models_penunjang import PemeriksaanPenunjang
from sidebar_manager import SidebarManager
from navigation_header import NavigationHeader
from fuzzywuzzy import process
import re
from themes import get_theme_css


st.set_page_config(
    page_title="HNA Comparison System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


if "theme" not in st.session_state:
    st.session_state.theme = "light"


session = SessionLocal()
sidebar_mgr = SidebarManager(session)
nav_header = NavigationHeader(session)
hna_mgr = HNAData(session)
penunjang_mgr = PemeriksaanPenunjang(session)


theme_css = get_theme_css(st.session_state.theme)
st.markdown(theme_css, unsafe_allow_html=True)


st.markdown(
    """
    <meta name="color-scheme" content="light">
    <meta name="theme-color" content="#007bff">
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
<style>
/* Style untuk navigation tabs */
.stButton button {
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
}

.stButton button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
}

/* Hilangkan border default Streamlit */
.main .block-container {
    padding-top: 1rem;
}
</style>
""",
    unsafe_allow_html=True,
)


def preprocess_text(text):
    """Preprocess text untuk similarity matching yang lebih akurat"""
    if pd.isna(text):
        return ""
   
    text = str(text).lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def advanced_similarity_search(df, query, column="nama_barang", threshold=85, limit=20):
    """Advanced similarity search dengan multiple strategies"""
    if not query or df.empty:
        return df

    query_processed = preprocess_text(query)
    choices = df[column].dropna().unique().tolist()

    if not choices:
        return pd.DataFrame()

    exact_matches = df[df[column].str.lower() == query.lower()]
    if not exact_matches.empty:
        return exact_matches

    contains_matches = df[df[column].str.lower().str.contains(query.lower(), na=False)]
    if not contains_matches.empty:
        return contains_matches

    choices_processed = [preprocess_text(choice) for choice in choices]
    results = process.extract(query_processed, choices_processed, limit=limit)

    matched_original_names = []
    for processed_choice, score, original_choice in zip(
        choices_processed, [r[1] for r in results], choices
    ):
        if score >= threshold:
            matched_original_names.append(original_choice)

    if matched_original_names:
        return df[df[column].isin(matched_original_names)]

    return pd.DataFrame()


def render_upload_page(hna_mgr):
    """Render upload data page"""
    # Download template
    template_df = pd.DataFrame(
        columns=["Kode Item", "Nama Barang", "Group Transaki", "Satuan", "HNA"]
    )

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        template_df.to_excel(writer, index=False, sheet_name="Template HNA")

        worksheet = writer.sheets["Template HNA"]
        for row in range(2, 5):
            cell = worksheet[f"E{row}"]
            cell.number_format = "#,##0"

    st.download_button(
        label="📥 Download Template Excel",
        data=output.getvalue(),
        file_name="template_hna.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    with st.form("upload_form"):
        col1, col2 = st.columns(2)
        with col1:
            region = st.text_input("Regional*", placeholder="Contoh: Jawa Barat")
            mitra = st.text_input("Nama Mitra*", placeholder="Contoh: St. Yusup")
        with col2:
            bulan = st.selectbox(
                "Periode Bulan*",
                [""]
                + [
                    "Januari",
                    "Februari",
                    "Maret",
                    "April",
                    "Mei",
                    "Juni",
                    "Juli",
                    "Agustus",
                    "September",
                    "Oktober",
                    "November",
                    "Desember",
                ],
            )
            tahun = st.number_input(
                "Periode Tahun*", min_value=2000, max_value=2100, value=2025
            )

        uploaded_file = st.file_uploader(
            "Pilih File Excel*", type=["xlsx"], help="Format harus sesuai template"
        )

        submit_btn = st.form_submit_button("🚀 Import File", use_container_width=True)

        if submit_btn:
            if not all([region, mitra, bulan, tahun, uploaded_file]):
                st.error("❌ Harap lengkapi semua field yang wajib diisi (*)")
            else:
                hna_mgr.upload_excel(
                    uploaded_file,
                    region,
                    mitra,
                    bulan,
                    tahun,
                    st.session_state["username"],
                )


def render_data_page(hna_mgr):
    """Render data display page"""
    df = hna_mgr.load_data()

    if df.empty:
        st.warning("📭 Belum ada data HNA.")
        return

    # Filters
    st.subheader("🔍 Filter Data")
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        region_options = ["Semua"] + sorted(df["region"].unique().tolist())
        region_filter = st.selectbox("Region", region_options)
    with col2:
        mitra_options = ["Semua"] + sorted(df["mitra"].unique().tolist())
        mitra_filter = st.selectbox("Mitra", mitra_options)
    with col3:
        group_options = ["Semua"] + sorted(df["group_transaksi"].unique().tolist())
        group_filter = st.selectbox("Group Transaksi", group_options)
    with col4:
        satuan_options = ["Semua"] + sorted(df["satuan"].unique().tolist())
        satuan_filter = st.selectbox("Satuan", satuan_options)
    with col5:
        bulan_options = ["Semua"] + sorted(df["periode_bulan"].unique().tolist())
        bulan_filter = st.selectbox("Bulan", bulan_options)
    with col6:
        tahun_options = ["Semua"] + sorted(df["periode_tahun"].unique().tolist())
        tahun_filter = st.selectbox("Tahun", tahun_options)

    st.subheader("🔎 Pencarian Nama Obat")
    name_query = st.text_input(
        "Masukkan nama obat",
        placeholder="Contoh: VERBAN ELASTIS ELASTOMUL HAFT 8X4 PER CM",
        help="Pencarian akan mencari match exact terlebih dahulu, kemudian similarity",
    )

    if "similarity_threshold" not in st.session_state:
        st.session_state.similarity_threshold = 85
    if "search_mode" not in st.session_state:
        st.session_state.search_mode = "Auto (Exact + Similarity)"

    similarity_threshold = st.session_state.similarity_threshold
    search_mode = st.session_state.search_mode

    filtered_df = df.copy()

    if region_filter != "Semua":
        filtered_df = filtered_df[filtered_df["region"] == region_filter]
    if mitra_filter != "Semua":
        filtered_df = filtered_df[filtered_df["mitra"] == mitra_filter]
    if group_filter != "Semua":
        filtered_df = filtered_df[filtered_df["group_transaksi"] == group_filter]
    if satuan_filter != "Semua":
        filtered_df = filtered_df[filtered_df["satuan"] == satuan_filter]
    if bulan_filter != "Semua":
        filtered_df = filtered_df[filtered_df["periode_bulan"] == bulan_filter]
    if tahun_filter != "Semua":
        filtered_df = filtered_df[filtered_df["periode_tahun"] == tahun_filter]

    
    search_results = None
    if name_query:
        if search_mode == "Hanya Exact Match":
           
            search_results = filtered_df[
                filtered_df["nama_barang"].str.lower() == name_query.lower()
            ]
        elif search_mode == "Hanya Similarity":
         
            search_results = advanced_similarity_search(
                filtered_df, name_query, "nama_barang", similarity_threshold
            )
        else:  
            exact_matches = filtered_df[
                filtered_df["nama_barang"].str.lower() == name_query.lower()
            ]
            if not exact_matches.empty:
                search_results = exact_matches
                st.success("🎯 Ditemukan exact match!")
            else:
              
                search_results = advanced_similarity_search(
                    filtered_df, name_query, "nama_barang", similarity_threshold
                )
                if not search_results.empty:
                    st.info(
                        f"🔍 Ditemukan {len(search_results)} hasil similarity (threshold: {similarity_threshold}%)"
                    )
                else:
                    st.warning("❌ Tidak ditemukan hasil untuk pencarian ini")

        if search_results is not None:
            filtered_df = search_results

   
    st.subheader(f"📋 Hasil Filter ({len(filtered_df)} data)")

    if not filtered_df.empty:
        
        display_df = filtered_df.copy()

       
        display_df["hna_formatted"] = display_df["hna"].apply(format_currency_id)

       
        display_df = display_df.reset_index(drop=True)
        display_df.index = display_df.index + 1
        display_df = display_df.rename_axis("No").reset_index()

        
        selected_columns = [
            "No",
            "region",
            "mitra",
            "kode_item",
            "nama_barang",
            "group_transaksi",
            "satuan",
            "hna_formatted",
            "periode_bulan",
            "periode_tahun",
            "uploaded_by",
            "uploaded_at",
        ]

     
        available_columns = [
            col for col in selected_columns if col in display_df.columns
        ]
        display_df = display_df[available_columns]

       
        column_mapping = {
            "No": "No",
            "region": "Regional",
            "mitra": "Mitra",
            "kode_item": "Kode Item",
            "nama_barang": "Nama Barang",
            "group_transaksi": "Group Transaksi",
            "satuan": "Satuan",
            "hna_formatted": "HNA",
            "periode_bulan": "Periode Bulan",
            "periode_tahun": "Periode Tahun",
            "uploaded_by": "Uploaded By",
            "uploaded_at": "Uploaded At",
        }

        display_df = display_df.rename(columns=column_mapping)

        
        if (
            name_query
            and search_mode in ["Auto (Exact + Similarity)", "Hanya Similarity"]
            and not filtered_df.empty
        ):
            similarity_scores = []
            for name in filtered_df["nama_barang"]:
                score = process.extractOne(
                    preprocess_text(name_query), [preprocess_text(name)]
                )[1]
                similarity_scores.append(score)

            display_df["Similarity (%)"] = similarity_scores
            display_df = display_df.sort_values("Similarity (%)", ascending=False)

       
        try:
            display_df["Uploaded At"] = pd.to_datetime(
                display_df["Uploaded At"]
            ).dt.strftime("%Y-%m-%d %H:%M")
        except:
            pass

       
        st.dataframe(display_df, use_container_width=True, hide_index=True)

   
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
           
            download_df = filtered_df.reset_index(drop=True)
            download_df.index = download_df.index + 1
            download_df = download_df.rename_axis("No").reset_index()

           
            download_columns = [
                "No",
                "region",
                "mitra",
                "kode_item",
                "nama_barang",
                "group_transaksi",
                "satuan",
                "hna",
                "periode_bulan",
                "periode_tahun",
                "uploaded_by",
                "uploaded_at",
            ]
            download_columns = [
                col for col in download_columns if col in download_df.columns
            ]
            download_df = download_df[download_columns]

            download_mapping = {
                "No": "No",
                "region": "Regional",
                "mitra": "Mitra",
                "kode_item": "Kode Item",
                "nama_barang": "Nama Barang",
                "group_transaksi": "Group Transaksi",
                "satuan": "Satuan",
                "hna": "HNA",
                "periode_bulan": "Periode Bulan",
                "periode_tahun": "Periode Tahun",
                "uploaded_by": "Uploaded By",
                "uploaded_at": "Uploaded At",
            }

            download_df = download_df.rename(columns=download_mapping)
            download_df.to_excel(writer, index=False, sheet_name="HNA Data")

            # Set format untuk kolom HNA di Excel
            worksheet = writer.sheets["HNA Data"]
            for row in range(2, len(download_df) + 2):
                cell = worksheet[f"H{row}"]
                cell.number_format = "#,##0"

        st.download_button(
            label="📥 Download Data",
            data=output.getvalue(),
            file_name="HNA_Data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        st.warning("Tidak ada data yang sesuai dengan filter yang dipilih")


def render_upload_page_penunjang(penunjang_mgr):
    """Render upload data pemeriksaan penunjang page"""

    # Download template
    template_df = pd.DataFrame(
        columns=["KODE", "DESKRIPSI", "GROUP TRANSAKSI", "SATUAN"]
    )

    # Contoh data untuk template
    # example_data = {
    #     "KODE": ["LAB001", "RAD002"],
    #     "DESKRIPSI": ["HEMATOLOGY TEST", "X-RAY THORAX"],
    #     "GROUP TRANSAKSI": ["Laboratorium", "Radiologi"],
    #     "SATUAN": ["TEST", "EXAM"]
    # }
    # template_df = pd.DataFrame(example_data)

    # Informasi tentang kolom tambahan
    st.info(
        """
    **📝 Template Pemeriksaan Penunjang:**
    - **Kolom Kelas disesuaikan dengan kebutuhan masing masing tanpa menghapus kolom pada template yang tersedia.**
    - **Kolom Pakem (Wajib):** KODE, DESKRIPSI, GROUP TRANSAKSI, SATUAN
    - **Kolom Tambahan (Opsional):** Anda bisa menambahkan kolom lain di sebelah kanan, contoh: KATEGORI, SUB_KATEGORI, KELAS, dll.
    - **Kolom tambahan akan otomatis terdeteksi dan disimpan.**
    """
    )

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        template_df.to_excel(writer, index=False, sheet_name="Template Penunjang")

    st.download_button(
        label="📥 Download Template Pemeriksaan Penunjang",
        data=output.getvalue(),
        file_name="template_pemeriksaan_penunjang.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    # Upload form
    st.markdown("---")
    st.subheader("📤 Upload Data Pemeriksaan Penunjang")

    # Input untuk mitra
    mitra = st.text_input("Nama Mitra*", placeholder="Contoh: St. Yusup")

    uploaded_file = st.file_uploader(
        "Pilih File Excel Pemeriksaan Penunjang*",
        type=["xlsx"],
        help="File harus berisi kolom pakem: KODE, DESKRIPSI, GROUP TRANSAKSI, SATUAN",
    )

    if st.button("🚀 Upload File Pemeriksaan Penunjang", use_container_width=True):
        if not uploaded_file or not mitra:
            st.error("❌ Harap pilih file dan isi nama mitra yang akan diupload")
        else:
            penunjang_mgr.upload_excel(
                uploaded_file, mitra, st.session_state["username"]
            )


def render_data_page_penunjang(penunjang_mgr):
    """Render data display page pemeriksaan penunjang"""
    df = penunjang_mgr.load_data()
    if df.empty:
        st.warning("📭 Belum ada data Pemeriksaan Penunjang.")
        return

    # untuk mendapatkan daftar kolom tambahan yang tersedia
    available_columns = penunjang_mgr.get_available_columns()

    # Filter dan pencarian
    st.subheader("🔍 Filter Data Pemeriksaan Penunjang")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        mitra_options = ["Semua"] + sorted(df["mitra"].unique().tolist())
        mitra_filter = st.selectbox("Mitra", mitra_options)
    with col2:
        group_options = ["Semua"] + sorted(df["group_transaksi"].unique().tolist())
        group_filter = st.selectbox("Group Transaksi", group_options)
    with col3:
        satuan_options = ["Semua"] + sorted(df["satuan"].unique().tolist())
        satuan_filter = st.selectbox("Satuan", satuan_options)
    with col4:
        kelas_options = ["Semua"] + available_columns
        kelas_filter = st.selectbox("Pilih Kelas", kelas_options)
    with col5:
        search_query = st.text_input(
            "Cari Deskripsi", placeholder="Cari nama pemeriksaan..."
        )

    # Apply filters
    filtered_df = df.copy()

    if mitra_filter != "Semua":
        filtered_df = filtered_df[filtered_df["mitra"] == mitra_filter]
    if group_filter != "Semua":
        filtered_df = filtered_df[filtered_df["group_transaksi"] == group_filter]
    if satuan_filter != "Semua":
        filtered_df = filtered_df[filtered_df["satuan"] == satuan_filter]
    if search_query:
        filtered_df = filtered_df[
            filtered_df["deskripsi"].str.contains(search_query, case=False, na=False)
        ]


    st.subheader(f"📋 Data Pemeriksaan Penunjang ({len(filtered_df)} data)")

    if not filtered_df.empty:
        # Fungsi untuk memformat angka
        def format_number(value):
            if pd.isna(value) or value == "" or value is None:
                return ""
            try:
                
                num = float(value)
                # Format dengan pemisah ribuan dan 2 digit desimal
                return "{:,.2f}".format(num)
            except (ValueError, TypeError):
                # Jika bukan angka, kembalikan nilai asli
                return str(value)

    
        display_data = []

        for _, row in filtered_df.iterrows():
            base_data = {
                "No": len(display_data) + 1,
                "Mitra": row["mitra"],
                "Kode": row["kode"],
                "Deskripsi": row["deskripsi"],
                "Group Transaksi": row["group_transaksi"],
                "Satuan": row["satuan"],
            }

            
            if kelas_filter != "Semua" and row["additional_data"]:
                kelas_value = row["additional_data"].get(kelas_filter, "")
                base_data[kelas_filter] = format_number(kelas_value)

            display_data.append(base_data)

        display_df = pd.DataFrame(display_data)

        # Tampilkan dataframe utama
        st.dataframe(display_df, use_container_width=True, hide_index=True)

       
        st.subheader("🔍 Detail Pemeriksaan Penunjang")

        if len(filtered_df) == 1:
            selected_item = filtered_df.iloc[0]
            selected_item_desc = (
                f"{selected_item['kode']} - {selected_item['deskripsi']}"
            )
        else:
            
            item_options = [
                f"{row['kode']} - {row['deskripsi']}"
                for _, row in filtered_df.iterrows()
            ]
            selected_item_desc = st.selectbox(
                "Pilih item untuk melihat detail:", item_options
            )
            selected_item_idx = item_options.index(selected_item_desc)
            selected_item = filtered_df.iloc[selected_item_idx]

        
        st.write(f"**Detail untuk:** {selected_item_desc}")

        
        detail_headers = []
        detail_values = []

  
        detail_headers.extend(
            ["Mitra", "Kode", "Deskripsi", "Group Transaksi", "Satuan"]
        )
        detail_values.extend(
            [
                selected_item["mitra"],
                selected_item["kode"],
                selected_item["deskripsi"],
                selected_item["group_transaksi"],
                selected_item["satuan"],
            ]
        )

       
        additional_data = selected_item.get("additional_data", {})
        if additional_data:
            for key, value in additional_data.items():
                display_name = penunjang_mgr.get_column_display_name(key)
                detail_headers.append(display_name)
                
                formatted_value = format_number(value)
                detail_values.append(formatted_value)

       
        horizontal_detail_df = pd.DataFrame([detail_values], columns=detail_headers)

        
        st.dataframe(horizontal_detail_df, use_container_width=True, hide_index=True)

        if selected_item["mitra"] == "Surya Husada":
            st.info(
                """
            **Keterangan Kelas untuk Surya Husada:**
            - **Kelas 1**: Kelas Lain
            - **Kelas 2**: Kelas Tenun, Kelas Legong
            - **Kelas 3**: Dwaraka, Kosala
            """
            )

       
        st.caption(
            f"Data diupload oleh: {selected_item.get('uploaded_by', 'N/A')} pada {selected_item.get('uploaded_at', 'N/A')}"
        )

       
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
           
            download_data = []
            for _, row in filtered_df.iterrows():
                row_data = {
                    "Mitra": row["mitra"],
                    "Kode": row["kode"],
                    "Deskripsi": row["deskripsi"],
                    "Group Transaksi": row["group_transaksi"],
                    "Satuan": row["satuan"],
                }

                # Tambahkan semua kolom tambahan
                additional_data = row.get("additional_data", {})
                for col in available_columns:
                    row_data[col] = additional_data.get(col, "")

                download_data.append(row_data)

            download_df = pd.DataFrame(download_data)
            download_df.to_excel(writer, index=False, sheet_name="Data Penunjang")

           
            worksheet = writer.sheets["Data Penunjang"]

            
            column_letters = {}
            for idx, col_name in enumerate(download_df.columns):
                column_letters[col_name] = chr(65 + idx)  # A, B, C, ...

            # Format kolom yang berisi angka
            for col_name in available_columns:
                if col_name in column_letters:
                    col_letter = column_letters[col_name]
                    # Format semua baris di kolom ini
                    for row_num in range(
                        2, len(download_df) + 2
                    ):  # Mulai dari baris 2 (setelah header)
                        try:
                            cell = worksheet[f"{col_letter}{row_num}"]
                            value = download_df.iloc[row_num - 2][col_name]
                            # Cek jika value adalah angka
                            if (
                                value
                                and str(value).strip()
                                and str(value)
                                .replace(".", "")
                                .replace(",", "")
                                .isdigit()
                            ):
                                cell.number_format = "#,##0.00"
                        except Exception as e:
                            continue

        st.download_button(
            label="📥 Download Data Pemeriksaan Penunjang",
            data=output.getvalue(),
            file_name="Pemeriksaan_Penunjang_Data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        st.warning("Tidak ada data yang sesuai dengan filter yang dipilih")


def render_user_management_page(user_mgr):
    """Render user management page (admin only)"""
    if st.session_state["role"] != "admin":
        st.warning("⛔ Hanya admin yang bisa mengakses halaman ini")
        return

    with st.form("add_user_form"):
        st.subheader("Tambah User Baru")
        col1, col2 = st.columns(2)
        with col1:
            new_user = st.text_input("Username*", placeholder="Username baru")
            new_pass = st.text_input(
                "Password*", type="password", placeholder="Password"
            )
        with col2:
            role = st.selectbox("Role*", ["user", "admin"])

        submit_btn = st.form_submit_button("➕ Tambah User", use_container_width=True)

        if submit_btn:
            if not all([new_user, new_pass]):
                st.error("❌ Harap isi semua field yang wajib (*)")
            else:
                user_mgr.add_user(new_user, new_pass, role)


def render_delete_data_page(hna_mgr, penunjang_mgr):
    """Halaman untuk menghapus data (admin only)"""
    if st.session_state["role"] != "admin":
        st.warning("⛔ Hanya admin yang bisa mengakses halaman ini")
        return

    st.title("🗑️ Hapus Data")
    st.warning("**PERHATIAN:** Tindakan menghapus data tidak dapat dibatalkan!")

 
    tab1, tab2 = st.tabs(["🗂️ Hapus Data HNA", "🩺 Hapus Data Penunjang"])

    with tab1:
        st.subheader("Hapus Data HNA")

        # Load data HNA
        df_hna = hna_mgr.load_data()

        if not df_hna.empty:
            col1, col2 = st.columns([2, 1])

            with col1:
                st.info(f"📊 Total data HNA: {len(df_hna)} records")

                
                st.subheader("Pilih Data untuk Dihapus")

                
                display_cols = [
                    "id",
                    "region",
                    "mitra",
                    "kode_item",
                    "nama_barang",
                    "group_transaksi",
                    "hna",
                    "periode_bulan",
                    "periode_tahun",
                ]
                display_df = df_hna[display_cols].copy()
                display_df["hna"] = display_df["hna"].apply(format_currency_id)

                # Tambahkan checkbox untuk setiap row
                display_df["Pilih"] = False
                edited_df = st.data_editor(
                    display_df,
                    column_config={
                        "Pilih": st.column_config.CheckboxColumn(
                            "Pilih",
                            help="Pilih data yang akan dihapus",
                            default=False,
                        ),
                        "id": st.column_config.NumberColumn(
                            "ID", help="ID data", disabled=True
                        ),
                        "hna": st.column_config.TextColumn(
                            "HNA", help="Harga Netto Apotek"
                        ),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

                # Hitung yang dipilih
                selected_count = edited_df["Pilih"].sum()
                st.write(f"✅ {selected_count} data dipilih untuk dihapus")

            with col2:
                st.subheader("Aksi Hapus")

                # Hapus data terpilih
                if selected_count > 0:
                    if st.button(
                        f"🗑️ Hapus {selected_count} Data Terpilih",
                        type="primary",
                        use_container_width=True,
                    ):
                        selected_ids = edited_df[edited_df["Pilih"]]["id"].tolist()
                        success_count = 0

                        for data_id in selected_ids:
                            if hna_mgr.delete_data_by_id(data_id) > 0:
                                success_count += 1

                        st.success(f"✅ Berhasil menghapus {success_count} data!")
                        st.rerun()

                # Hapus berdasarkan filter
                st.subheader("Hapus Berdasarkan Filter")

                region_options = ["Semua"] + sorted(df_hna["region"].unique().tolist())
                mitra_options = ["Semua"] + sorted(df_hna["mitra"].unique().tolist())
                group_options = ["Semua"] + sorted(
                    df_hna["group_transaksi"].unique().tolist()
                )
                bulan_options = ["Semua"] + sorted(
                    df_hna["periode_bulan"].unique().tolist()
                )
                tahun_options = ["Semua"] + sorted(
                    df_hna["periode_tahun"].unique().tolist()
                )

                filter_region = st.selectbox("Region", region_options, key="hna_region")
                filter_mitra = st.selectbox("Mitra", mitra_options, key="hna_mitra")
                filter_group = st.selectbox(
                    "Group Transaksi", group_options, key="hna_group"
                )
                filter_bulan = st.selectbox("Bulan", bulan_options, key="hna_bulan")
                filter_tahun = st.selectbox("Tahun", tahun_options, key="hna_tahun")

                if st.button("🗑️ Hapus Berdasarkan Filter", use_container_width=True):
                    deleted_count = hna_mgr.delete_data_by_filter(
                        region=filter_region,
                        mitra=filter_mitra,
                        group=filter_group,
                        bulan=filter_bulan,
                        tahun=filter_tahun,
                    )
                    st.success(
                        f"✅ Berhasil menghapus {deleted_count} data berdasarkan filter!"
                    )
                    st.rerun()

                # Hapus semua data (danger zone)
                st.subheader("WARNING")
                st.error("Hapus SEMUA data HNA - TIDAK BISA DIBATALKAN!")

                confirm_text = st.text_input(
                    "Ketik 'HAPUS SEMUA' untuk konfirmasi:", key="confirm_hna"
                )
                if st.button(
                    " HAPUS SEMUA DATA HNA",
                    type="secondary",
                    use_container_width=True,
                ):
                    if confirm_text == "HAPUS SEMUA":
                        deleted_count = hna_mgr.delete_all_data()
                        st.success(f"✅ Berhasil menghapus {deleted_count} data HNA!")
                        st.rerun()
                    else:
                        st.error("❌ Konfirmasi tidak valid!")
        else:
            st.info("Tidak ada data HNA yang bisa dihapus")

    with tab2:
        st.subheader("Hapus Data Pemeriksaan Penunjang")

        
        df_penunjang = penunjang_mgr.load_data()

        if not df_penunjang.empty:
            col1, col2 = st.columns([2, 1])

            with col1:
                st.info(f"📊 Total data Penunjang: {len(df_penunjang)} records")

                
                st.subheader("Pilih Data untuk Dihapus")

               
                display_cols = [
                    "id",
                    "mitra",
                    "kode",
                    "deskripsi",
                    "group_transaksi",
                    "satuan",
                ]
                display_df = df_penunjang[display_cols].copy()

                # Tambahkan checkbox untuk setiap row
                display_df["Pilih"] = False
                edited_df = st.data_editor(
                    display_df,
                    column_config={
                        "Pilih": st.column_config.CheckboxColumn(
                            "Pilih",
                            help="Pilih data yang akan dihapus",
                            default=False,
                        ),
                        "id": st.column_config.NumberColumn(
                            "ID", help="ID data", disabled=True
                        ),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

                # Hitung yang dipilih
                selected_count = edited_df["Pilih"].sum()
                st.write(f"✅ {selected_count} data dipilih untuk dihapus")

            with col2:
                st.subheader("Aksi Hapus")

                # Hapus data terpilih
                if selected_count > 0:
                    if st.button(
                        f"🗑️ Hapus {selected_count} Data Penunjang",
                        type="primary",
                        use_container_width=True,
                        key="delete_selected_penunjang",
                    ):
                        selected_ids = edited_df[edited_df["Pilih"]]["id"].tolist()
                        success_count = 0

                        for data_id in selected_ids:
                            if penunjang_mgr.delete_data_by_id(data_id) > 0:
                                success_count += 1

                        st.success(
                            f"✅ Berhasil menghapus {success_count} data penunjang!"
                        )
                        st.rerun()

                # Hapus berdasarkan filter
                st.subheader("Hapus Berdasarkan Filter")

                mitra_options = ["Semua"] + sorted(
                    df_penunjang["mitra"].unique().tolist()
                )
                group_options = ["Semua"] + sorted(
                    df_penunjang["group_transaksi"].unique().tolist()
                )
                satuan_options = ["Semua"] + sorted(
                    df_penunjang["satuan"].unique().tolist()
                )

                filter_mitra = st.selectbox(
                    "Mitra", mitra_options, key="penunjang_mitra"
                )
                filter_group = st.selectbox(
                    "Group Transaksi", group_options, key="penunjang_group"
                )
                filter_satuan = st.selectbox(
                    "Satuan", satuan_options, key="penunjang_satuan"
                )

                if st.button(
                    "🗑️ Hapus Penunjang Berdasarkan Filter", use_container_width=True
                ):
                    deleted_count = penunjang_mgr.delete_data_by_filter(
                        mitra=filter_mitra, group=filter_group, satuan=filter_satuan
                    )
                    st.success(
                        f"✅ Berhasil menghapus {deleted_count} data penunjang berdasarkan filter!"
                    )
                    st.rerun()

                # Hapus semua data (danger zone)
                st.subheader("WARNING")
                st.error("Hapus SEMUA data Penunjang - TIDAK BISA DIBATALKAN!")

                confirm_text = st.text_input(
                    "Ketik 'HAPUS SEMUA PENUNJANG' untuk konfirmasi:",
                    key="confirm_penunjang",
                )
                if st.button(
                    "HAPUS SEMUA DATA PENUNJANG",
                    type="secondary",
                    use_container_width=True,
                ):
                    if confirm_text == "HAPUS SEMUA PENUNJANG":
                        deleted_count = penunjang_mgr.delete_all_data()
                        st.success(
                            f"✅ Berhasil menghapus {deleted_count} data penunjang!"
                        )
                        st.rerun()
                    else:
                        st.error("❌ Konfirmasi tidak valid!")
        else:
            st.info("📭 Tidak ada data Penunjang yang bisa dihapus")


# Render sidebar and get selected page
selected_page = sidebar_mgr.render_sidebar()

# Main content based on selected page
if st.session_state["login"]:
    if selected_page == "Upload Data":
        st.title("📤 Upload Data HNA")
        render_upload_page(hna_mgr)

    elif selected_page == "Tampilan Data":
        st.title("📊 Data HNA")
        render_data_page(hna_mgr)

    elif selected_page == "Upload Penunjang":
        st.title("🩺 Upload Data Pemeriksaan Penunjang")
        render_upload_page_penunjang(penunjang_mgr)

    elif selected_page == "Tampilan Penunjang":
        st.title("📋 Data Pemeriksaan Penunjang")
        render_data_page_penunjang(penunjang_mgr)

    elif selected_page == "Hapus Data":
        render_delete_data_page(hna_mgr, penunjang_mgr)

    elif selected_page == "Manajemen User":
        st.title("👥 Manajemen User")
        render_user_management_page(sidebar_mgr.user_mgr)
