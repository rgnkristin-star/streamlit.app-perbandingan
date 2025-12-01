import pandas as pd
import streamlit as st
from sqlalchemy import text
import json


class PemeriksaanPenunjang:
    def __init__(self, session):
        self.session = session

    def upload_excel(self, file, mitra, user):
        try:
            df = pd.read_excel(file)

            expected_base_cols = ["KODE", "DESKRIPSI", "GROUP TRANSAKSI", "SATUAN"]

            for col in expected_base_cols:
                if col not in df.columns:
                    st.error(f"❌ Kolom {col} tidak ditemukan dalam file!")
                    return

            additional_cols = [
                col for col in df.columns if col not in expected_base_cols
            ]

            for col in additional_cols:
                try:
                    stmt = text(
                        """
                        INSERT OR IGNORE INTO pemeriksaan_columns_metadata (column_name, display_name, created_by)
                        VALUES (:column_name, :display_name, :created_by)
                    """
                    )
                    self.session.execute(
                        stmt,
                        {"column_name": col, "display_name": col, "created_by": user},
                    )
                except Exception as e:
                    st.warning(f"⚠️ Kolom {col} sudah ada atau error: {e}")

            self.session.commit()

            success_count = 0
            for _, row in df.iterrows():

                if pd.isna(row["KODE"]) or pd.isna(row["DESKRIPSI"]):
                    continue

                additional_data = {}
                for col in additional_cols:
                    if not pd.isna(row[col]):
                        additional_data[col] = str(row[col])

                stmt = text(
                    """
                    INSERT INTO pemeriksaan_penunjang 
                    (mitra, kode, deskripsi, group_transaksi, satuan, additional_data, uploaded_by)
                    VALUES (:mitra, :kode, :deskripsi, :group_transaksi, :satuan, :additional_data, :user)
                """
                )
                self.session.execute(
                    stmt,
                    {
                        "mitra": mitra,
                        "kode": row["KODE"],
                        "deskripsi": row["DESKRIPSI"],
                        "group_transaksi": row["GROUP TRANSAKSI"],
                        "satuan": row["SATUAN"],
                        "additional_data": json.dumps(additional_data),
                        "user": user,
                    },
                )
                success_count += 1

            self.session.commit()
            st.success(
                f"✅ File berhasil diupload! {success_count} data pemeriksaan penunjang tersimpan."
            )
            st.info(
                f"📝 Kolom tambahan terdeteksi: {', '.join(additional_cols) if additional_cols else 'Tidak ada'}"
            )

        except Exception as e:
            st.error(f"❌ Error upload: {e}")

    def load_data(self):
        try:
            df = pd.read_sql(
                "SELECT * FROM pemeriksaan_penunjang ORDER BY uploaded_at DESC",
                self.session.bind,
            )

            if not df.empty and "additional_data" in df.columns:
                df["additional_data"] = df["additional_data"].apply(
                    lambda x: json.loads(x) if x else {}
                )

            return df
        except Exception as e:
            st.error(f"❌ Error loading data: {e}")
            return pd.DataFrame()

    def get_available_columns(self):
        """Mendapatkan daftar kolom tambahan yang tersedia"""
        try:
            stmt = text(
                "SELECT column_name, display_name FROM pemeriksaan_columns_metadata ORDER BY column_name"
            )
            result = self.session.execute(stmt).fetchall()
            return [row[0] for row in result]  # Return list of column names
        except Exception as e:
            st.error(f"❌ Error getting columns: {e}")
            return []

    def get_column_display_name(self, column_name):
        """Mendapatkan display name untuk kolom"""
        try:
            stmt = text(
                "SELECT display_name FROM pemeriksaan_columns_metadata WHERE column_name = :column_name"
            )
            result = self.session.execute(stmt, {"column_name": column_name}).fetchone()
            return result[0] if result else column_name
        except:
            return column_name

    # ========== FUNGSI HAPUS DATA PENUNJANG ==========
    def delete_data_by_id(self, data_id):
        """Hapus data penunjang berdasarkan ID"""
        try:
            stmt = text("DELETE FROM pemeriksaan_penunjang WHERE id = :id")
            result = self.session.execute(stmt, {"id": data_id})
            self.session.commit()
            return result.rowcount
        except Exception as e:
            st.error(f"❌ Error menghapus data: {e}")
            return 0

    def delete_data_by_filter(self, mitra=None, group=None, satuan=None):
        """Hapus data penunjang berdasarkan filter"""
        try:
            base_sql = "DELETE FROM pemeriksaan_penunjang WHERE 1=1"
            params = {}

            if mitra and mitra != "Semua":
                base_sql += " AND mitra = :mitra"
                params["mitra"] = mitra
            if group and group != "Semua":
                base_sql += " AND group_transaksi = :group"
                params["group"] = group
            if satuan and satuan != "Semua":
                base_sql += " AND satuan = :satuan"
                params["satuan"] = satuan

            stmt = text(base_sql)
            result = self.session.execute(stmt, params)
            self.session.commit()

            return result.rowcount
        except Exception as e:
            st.error(f"❌ Error menghapus data: {e}")
            return 0

    def delete_all_data(self):
        """Hapus semua data penunjang"""
        try:
            stmt = text("DELETE FROM pemeriksaan_penunjang")
            result = self.session.execute(stmt)
            self.session.commit()
            return result.rowcount
        except Exception as e:
            st.error(f"❌ Error menghapus semua data: {e}")
            return 0
