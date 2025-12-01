import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
from db import SessionLocal
import json

# Konfigurasi Google Sheets API
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

class GoogleSheetsExporter:
    def __init__(self, credential_file='credentials.json'):
        self.credential_file = credential_file
        self.setup_connection()
    
    def setup_connection(self):
        """Setup koneksi ke Google Sheets"""
        try:
            creds = Credentials.from_service_account_file(self.credential_file, scopes=SCOPES)
            self.client = gspread.authorize(creds)
            st.success("✅ Terhubung dengan Google Sheets")
        except Exception as e:
            st.error(f"❌ Error koneksi Google Sheets: {e}")
    
    def export_hna_to_sheets(self, spreadsheet_name="HNA_Data_Database"):
        """Export data HNA ke Google Sheets"""
        try:
            # Load data dari database
            session = SessionLocal()
            df = pd.read_sql("SELECT * FROM hna_data ORDER BY uploaded_at DESC", session.bind)
            session.close()
            
            if df.empty:
                st.warning("Tidak ada data HNA untuk diexport")
                return
            
            # Buka atau buat spreadsheet
            try:
                spreadsheet = self.client.open(spreadsheet_name)
            except gspread.SpreadsheetNotFound:
                spreadsheet = self.client.create(spreadsheet_name)
                # Share spreadsheet (opsional - agar bisa diakses orang lain)
                spreadsheet.share(None, perm_type='anyone', role='writer')
            
            # Pilih worksheet pertama
            worksheet = spreadsheet.sheet1
            
            # Clear existing data
            worksheet.clear()
            
            # Convert dataframe ke list of lists
            data = [df.columns.tolist()] + df.values.tolist()
            
            # Update worksheet dengan data baru
            worksheet.update('A1', data)
            
            st.success(f"✅ Data HNA berhasil diexport! {len(df)} records")
            st.info(f"📊 Link Spreadsheet: {spreadsheet.url}")
            
        except Exception as e:
            st.error(f"❌ Error export HNA: {e}")
    
    def export_penunjang_to_sheets(self, spreadsheet_name="Penunjang_Data_Database"):
        """Export data pemeriksaan penunjang ke Google Sheets"""
        try:
            # Load data dari database
            session = SessionLocal()
            df = pd.read_sql("SELECT * FROM pemeriksaan_penunjang ORDER BY uploaded_at DESC", session.bind)
            session.close()
            
            if df.empty:
                st.warning("Tidak ada data Penunjang untuk diexport")
                return
            
            # Parse JSON additional_data
            if not df.empty and 'additional_data' in df.columns:
                df['additional_data'] = df['additional_data'].apply(
                    lambda x: json.loads(x) if x else {}
                )
                
                # Extract additional columns
                additional_cols = set()
                for data in df['additional_data']:
                    if data:
                        additional_cols.update(data.keys())
                
                # Add additional columns to dataframe
                for col in additional_cols:
                    df[col] = df['additional_data'].apply(lambda x: x.get(col, ''))
                
                # Drop the original additional_data column
                df = df.drop('additional_data', axis=1)
            
            # Buka atau buat spreadsheet
            try:
                spreadsheet = self.client.open(spreadsheet_name)
            except gspread.SpreadsheetNotFound:
                spreadsheet = self.client.create(spreadsheet_name)
                spreadsheet.share(None, perm_type='anyone', role='writer')
            
            # Pilih worksheet pertama
            worksheet = spreadsheet.sheet1
            
            # Clear existing data
            worksheet.clear()
            
            # Convert dataframe ke list of lists
            data = [df.columns.tolist()] + df.values.tolist()
            
            # Update worksheet dengan data baru
            worksheet.update('A1', data)
            
            st.success(f"✅ Data Penunjang berhasil diexport! {len(df)} records")
            st.info(f"📊 Link Spreadsheet: {spreadsheet.url}")
            
        except Exception as e:
            st.error(f"❌ Error export Penunjang: {e}")

# Tambahkan fungsi export ke main.py
def render_export_page():
    """Halaman untuk export data ke Google Sheets"""
    st.title("📤 Export ke Looker Studio")
    
    exporter = GoogleSheetsExporter()
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Export Data HNA ke Google Sheets", use_container_width=True):
            exporter.export_hna_to_sheets()
    
    with col2:
        if st.button("🔄 Export Data Penunjang ke Google Sheets", use_container_width=True):
            exporter.export_penunjang_to_sheets()
    
    st.markdown("---")
    st.subheader("📝 Panduan Looker Studio")
    
    st.info("""
    **Setelah export berhasil:**
    
    1. **Buka Looker Studio** di [lookerstudio.google.com](https://lookerstudio.google.com)
    2. **Klik "Create"** → **"Report"**
    3. **Pilih Google Sheets** sebagai data source
    4. **Pilih spreadsheet** yang sudah diexport
    5. **Klik "Add to report"**
    6. **Buat dashboard** dengan drag & drop
    7. **Share link** ke tim Anda
    """)