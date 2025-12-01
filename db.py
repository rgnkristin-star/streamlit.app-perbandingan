import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import sqlite3

load_dotenv()

#DEFAULT PAKAI SQLite
DB_TYPE = os.getenv("DB_TYPE", "sqlite")

if DB_TYPE == "mysql":
    # Konfigurasi MySQL (untuk development)
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")  
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_NAME = os.getenv("DB_NAME")
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"
else:
    # Gunakan SQLite (untuk production/portable)
    DB_NAME = os.getenv("DB_NAME", "hna_compare")
    DATABASE_URL = f"sqlite:///./{DB_NAME}.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Migrasi data dari mysql ke sqlite
def migrate_mysql_to_sqlite():
    """Migrate data dari MySQL ke SQLite jika diperlukan"""
    try:
        if not os.path.exists(f"{DB_NAME}.db"):
            print("🗃️ Membuat database SQLite...")
            
            # Buat koneksi SQLite
            sqlite_conn = sqlite3.connect(f"{DB_NAME}.db")
            cursor = sqlite_conn.cursor()
            
            # Buat tabel users
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Buat tabel hna_data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hna_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    region TEXT NOT NULL,
                    mitra TEXT NOT NULL,
                    kode_item TEXT NOT NULL,
                    nama_barang TEXT NOT NULL,
                    group_transaksi TEXT NOT NULL,
                    satuan TEXT NOT NULL,
                    hna REAL NOT NULL,
                    periode_bulan TEXT NOT NULL,
                    periode_tahun INTEGER NOT NULL,
                    uploaded_by TEXT NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Buat tabel pemeriksaan_penunjang
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pemeriksaan_penunjang (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mitra TEXT NOT NULL,
                    kode TEXT NOT NULL,
                    deskripsi TEXT NOT NULL,
                    group_transaksi TEXT NOT NULL,
                    satuan TEXT NOT NULL,
                    additional_data TEXT,
                    uploaded_by TEXT NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Buat tabel pemeriksaan_columns_metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pemeriksaan_columns_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    column_name TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tambah user admin default jika belum ada
            cursor.execute("""
                INSERT OR IGNORE INTO users (username, password, role) 
                VALUES ('admin', 'admin', 'admin')
            """)
            
            sqlite_conn.commit()
            sqlite_conn.close()
            
            print("✅ Database SQLite berhasil dibuat!")
        return True
    except Exception as e:
        print(f"❌ Error membuat database SQLite: {e}")
        return False

# Jalankan migrasi saat import
migrate_mysql_to_sqlite()