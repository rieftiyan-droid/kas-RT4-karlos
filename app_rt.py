import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
import os

# --- KONFIGURASI ---
st.set_page_config(page_title="Sistem Kas RT Digital", page_icon="🏡", layout="wide")

# PASSWORD ADMIN
PASSWORD_RAHASIA = "admin123"

# NAMA FILE DATABASE GOOGLE SHEET
SHEET_NAME = "Database Kas RT"
FOLDER_GAMBAR = "bukti_bayar"

# Buat folder gambar jika belum ada
if not os.path.exists(FOLDER_GAMBAR):
    os.makedirs(FOLDER_GAMBAR)

# --- 1. FUNGSI KONEKSI KE GOOGLE SHEETS ---
def connect_to_gsheet():
    try:
        # Cek apakah jalan di Laptop (Lokal)
        if os.path.exists("credentials.json"):
            client = gspread.service_account(filename="credentials.json")
        # Cek apakah jalan di Streamlit Cloud (Internet)
        elif "gcp_service_account" in st.secrets:
            client = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        else:
            return None
        return client
    except Exception as e:
        return None

# --- 2. LOAD DATA TRANSAKSI (SHEET 1) ---
def load_data():
    client = connect_to_gsheet()
    if client:
        try:
            sheet = client.open(SHEET_NAME).sheet1
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            if df.empty: return pd.DataFrame()
            
            # Bersihkan data: Ubah Nominal jadi Angka
            if 'Nominal' in df.columns:
                df['Nominal'] = pd.to_numeric(df['Nominal'], errors='coerce').fillna(0)
            
            # Ambil Tahun dari Tanggal
            if 'Tanggal' in df.columns:
                df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
                df['Tahun'] = df['Tanggal'].dt.year
                # Kembalikan format tanggal jadi string agar rapi di tabel
                df['Tanggal'] = df['Tanggal'].dt.strftime('%Y-%m-%d')
                
            return df
        except:
            pass
    return pd.DataFrame()

# --- 3. LOAD MASTER DATA WARGA (SHEET "Data Warga") ---
def load_master_warga():
    client = connect_to_gsheet()
    if client:
        try:
            sheet = client.open(SHEET_NAME).worksheet("Data Warga")
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            
            # Buat ID Unik (Gabungan Blok dan No)
            # Contoh: Blok "AA", No "1" -> ID "AA-1"
            if not df.empty:
                df['ID_Rumah'] = df['Blok'].astype(str) + "-" + df['No'].astype(str)
            return df
        except:
            return pd.DataFrame() 
    return pd.DataFrame()

# --- 4. FUNGSI SIMPAN & HAPUS ---
def save_uploaded_file(uploadedfile):
    if uploadedfile is not None:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = os.path.splitext(uploadedfile.name)[1]
            filename = f"IMG_{timestamp}{ext}"
            with open(os.path.join(FOLDER_GAMBAR, filename), "wb") as f:
                f.write(uploadedfile.getbuffer())
            return filename
        except:
            return "-"
    return "-"

def save_new_data(data):
    client = connect_to_gsheet()
    if client:
        sheet = client.open(SHEET_NAME).sheet1
        sheet.append_row([
            data["ID"], data["Tanggal"], data["Nama Warga"], 
            data["Blok"], data["Status Rumah"], 
            data["Jenis Iuran"], data["Bulan"], 
            int(data["Nominal"]), data["Keterangan"], data["Bukti Bayar"]
        ])

def delete_data(target_id):
    client = connect_to_gsheet()
    if client:
        sheet = client.open(SHEET_NAME).sheet1
        try:
            cell = sheet.find(str(target_id))
            sheet.delete_rows(cell.row)
            return True
        except:
            return False
    return False

# ==========================================
#               TAMPILAN UTAMA (UI)
# ==========================================

st.title("🏡 Portal Keuangan & Monitoring Warga RT")
st.caption("Transparansi dan Akuntabilitas Kas Lingkungan")
st.markdown("---")

# --- A. SIDEBAR (LOGIN & INPUT) ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1909/1909672.png", width=80)
st.sidebar.title("Menu Admin")

# Kotak Password
input_pass = st.sidebar.text_input("🔑 Password Admin", type="password")
is_admin = (input_pass == PASSWORD_RAHASIA)

if is_admin:
    st.sidebar.success("✅ Mode Admin Aktif")
    st.sidebar.markdown("---")
    st.sidebar.header("📝 Input Transaksi")
    
    # Pilihan Input
    tipe_transaksi = st.sidebar.radio("Tipe Transaksi", ["Pemasukan 💰", "Pengeluaran 💸"])
    
    with st.sidebar.form("form_tambah"):
        nama_final = ""
        blok_final = ""
        status_final = "-"
        
        # --- LOGIKA 1: INPUT PEMASUKAN (WAJIB ADA BLOK) ---
        if tipe_transaksi == "Pemasukan 💰":
            st.info("ℹ️ Input Dana Masuk dari Warga")
            df_warga = load_master_warga()
            
            if not df_warga.empty:
                # Dropdown Warga (Otomatis Blok & Status)
                df_warga['Label'] = df_warga['ID_Rumah'] + " (" + df_warga['Status'] + ") - " + df_warga['Nama Penghuni']
                pilihan_warga = st.selectbox("Pilih Warga / Rumah", df_warga['Label'].unique())
                
                # Ambil data otomatis
                data_terpilih = df_warga[df_warga['Label'] == pilihan_warga].iloc[0]
                nama_final = data_terpilih['Nama Penghuni']
                blok_final = data_terpilih['ID_Rumah'] 
                status_final = data_terpilih['Status']
            else:
                st.warning("⚠️ Data Warga kosong! Buat sheet 'Data Warga' dulu.")
                nama_final = st.text_input("Nama Warga (Manual)")
                blok_final = st.text_input("Blok (Manual)")

            jenis = st.selectbox("Jenis Pemasukan", ["Iuran Wajib", "Kematian", "Agustusan", "Sumbangan", "Lainnya"])
            bulan = st.selectbox("Untuk Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember", "-"])
            nominal_input = st.number_input("Nominal (Rp)", min_value=0, step=5000)
            
        # --- LOGIKA 2: INPUT PENGELUARAN (TANPA BLOK) ---
        else:
            st.error("ℹ️ Input Dana Keluar / Belanja")
            # Nama Warga diganti jadi Uraian
            nama_final = st.text_input("Uraian Pengeluaran (Contoh: Beli Lampu, Honor Sampah)")
            
            # Data Blok & Status di-set kosong/strip
            blok_final = "-"
            status_final = "-"
            
            jenis = st.selectbox("Kategori Pengeluaran", ["Perbaikan Fasilitas", "Konsumsi Rapat", "Honor Keamanan/Sampah", "Sosial", "Lainnya"])
            
            # Bulan biasanya tidak relevan untuk belanja, di-set strip
            bulan = "-" 
            
            nominal_input = st.number_input("Nominal Keluar (Rp)", min_value=0, step=5000)
            
        ket = st.text_area("Keterangan Tambahan")
        uploaded_file = st.file_uploader("Upload Bukti/Struk", type=['jpg', 'png'])
        
        # Tombol Simpan
        if st.form_submit_button("Simpan Data"):
            if nominal_input > 0 and nama_final:
                with st.spinner("Menyimpan ke Cloud..."):
                    img_name = save_uploaded_file(uploaded_file)
                    
                    # Jika Pengeluaran, jadikan Minus
                    final_nominal = nominal_input if tipe_transaksi == "Pemasukan 💰" else -nominal_input
                    
                    new_data = {
                        "ID": int(datetime.now().timestamp()),
                        "Tanggal": datetime.now().strftime("%Y-%m-%d"),
                        "Nama Warga": nama_final, 
                        "Blok": blok_final, 
                        "Status Rumah": status_final,
                        "Jenis Iuran": jenis, 
                        "Bulan": bulan, 
                        "Nominal": final_nominal, 
                        "Keterangan": ket, 
                        "Bukti Bayar": img_name
                    }
                    save_new_data(new_data)
                    st.success("✅ Data Berhasil Disimpan!")
                    st.rerun()
            else:
                st.warning("Mohon lengkapi Nama/Uraian dan Nominal.")
else:
    # Tampilan Sidebar Warga Biasa
    st.sidebar.info("👋 Halo Warga! Silakan cek status pembayaran Anda di layar utama.")


# --- B. DASHBOARD UTAMA ---
df = load_data()
df_warga = load_master_warga()

if not df.empty:
    # --- FILTER TAHUN ---
    col_header, col_filter = st.columns([3, 1])
    with col_header:
        st.subheader("Laporan Keuangan RT")
    with col_filter:
        list_tahun = sorted(df['Tahun'].dropna().unique(), reverse=True)
        if not list_tahun: list_tahun = [datetime.now().year]
        pilih_tahun = st.selectbox("📅 Pilih Tahun", list_tahun)
    
    # Filter DataFrame berdasarkan tahun
    df_filtered = df[df['Tahun'] == pilih_tahun]
    
    # --- KARTU RINGKASAN (METRICS) ---
    total_masuk = df_filtered[df_filtered['Nominal'] > 0]['Nominal'].sum()
    total_keluar = df_filtered[df_filtered['Nominal'] < 0]['Nominal'].sum()
    saldo_akhir = total_masuk + total_keluar
    
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Pemasukan", f"Rp {total_masuk:,.0f}")
    c2.metric("💸 Pengeluaran", f"Rp {abs(total_keluar):,.0f}")
    c3.metric("💳 Saldo Kas", f"Rp {saldo_akhir:,.0f}")
    
    st.markdown("---")

    # --- TABULASI MENU ---
    tab1, tab2, tab3, tab4 = st.tabs(["✅ Monitoring Iuran Wajib", "📊 Mutasi Kas", "💸 Rincian Pengeluaran", "🏠 Database Warga"])

    # === TAB 1: MONITORING (MATRIKS) ===
    with tab1:
        st.caption(f"Status Pembayaran 'Iuran Wajib' Tahun {pilih_tahun}")
        st.write("🟥 Merah: Belum Bayar | 🟩 Hijau: Lunas | ⬜ Abu: Rumah Kosong")
        
        if not df_warga.empty:
            bulan_urut = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            
            # 1. Buat Tabel Dasar (Index: Blok/ID_Rumah)
            df_monitor = df_warga[['ID_Rumah', 'Status', 'Nama Penghuni']].copy()
            df_monitor.set_index('ID_Rumah', inplace=True)
            
            # 2. Ambil Transaksi 'Wajib' Tahun Ini
            df_bayar = df_filtered[
                (df_filtered['Jenis Iuran'].str.contains("Wajib", case=False, na=False)) & 
                (df_filtered['Nominal'] > 0)
            ]
            
            # 3. Isi Tabel Monitor
            for bln in bulan_urut:
                df_monitor[bln] = 0 # Default 0 (Belum Bayar)
                
                # Cek pembayaran bulan ini
                bayar_bln = df_bayar[df_bayar['Bulan'] == bln]
                for _, row in bayar_bln.iterrows():
                    # Jika Blok ada di daftar warga, tandai Nominalnya
                    if row['Blok'] in df_monitor.index:
                        df_monitor.at[row['Blok'], bln] = row['Nominal']

            # 4. Styling (Pewarnaan)
            def warnai_sel(val):
                if isinstance(val, (int, float)):
                    if val > 0: return 'background-color: #d4edda; color: green; font-weight: bold' # Hijau
                    if val == 0: return 'background-color: #f8d7da; color: red' # Merah
                return ''
            
            # Tampilkan Tabel
            st.dataframe(
                df_monitor.style.map(warnai_sel, subset=bulan_urut).format("{:,.0f}", subset=bulan_urut),
                use_container_width=True,
                height=600
            )
        else:
            st.warning("⚠️ Data Warga belum muncul. Pastikan sheet 'Data Warga' sudah dibuat di Google Sheet.")

    # === TAB 2: MUTASI KAS ===
    with tab2:
        st.caption("Daftar seluruh transaksi (Masuk & Keluar)")
        st.dataframe(df_filtered[["Tanggal", "Nama Warga", "Blok", "Jenis Iuran", "Nominal", "Keterangan"]], use_container_width=True)

    # === TAB 3: PENGELUARAN ===
    with tab3:
        st.caption("Khusus daftar belanja/pengeluaran RT")
        df_keluar = df_filtered[df_filtered['Nominal'] < 0]
        if not df_keluar.empty:
            c_pie, c_tab = st.columns([1, 2])
            with c_pie:
                fig = px.pie(df_keluar, values=df_keluar['Nominal'].abs(), names='Jenis Iuran', title='Kategori Pengeluaran')
                st.plotly_chart(fig, use_container_width=True)
            with c_tab:
                st.dataframe(df_keluar[["Tanggal", "Nama Warga", "Jenis Iuran", "Nominal", "Keterangan"]], use_container_width=True)
        else:
            st.info("Belum ada pengeluaran tahun ini.")

    # === TAB 4: DATABASE WARGA ===
    with tab4:
        st.dataframe(df_warga, use_container_width=True)

    # --- FITUR HAPUS DATA (ADMIN ONLY) ---
    if is_admin:
        st.markdown("---")
        with st.expander("⚠️ Menu Hapus Data (Admin)"):
            id_hapus = st.number_input("Masukkan ID Transaksi untuk dihapus", min_value=0)
            if st.button("Hapus Data Permanen"):
                if delete_data(id_hapus):
                    st.success("✅ Data berhasil dihapus.")
                    st.rerun()
                else:
                    st.error("❌ ID tidak ditemukan.")

else:
    # JIKA DATABASE KOSONG / ERROR
    st.info("Database belum siap atau masih kosong.")
    if is_admin:
        if st.button("Inisialisasi Header Baru (Reset)"):
            client = connect_to_gsheet()
            if client:
                try:
                    sh = client.open(SHEET_NAME).sheet1
                    sh.clear()
                    sh.append_row(["ID", "Tanggal", "Nama Warga", "Blok", "Status Rumah", "Jenis Iuran", "Bulan", "Nominal", "Keterangan", "Bukti Bayar"])
                    st.success("Header berhasil dibuat! Silakan refresh halaman.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal: {e}")