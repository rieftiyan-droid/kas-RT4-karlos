import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Kas RT Digital", page_icon="🏡", layout="wide")

# PASSWORD ADMIN
PASSWORD_RAHASIA = "admin123"

# NAMA FILE DATABASE
SHEET_NAME = "Database Kas RT"
FOLDER_GAMBAR = "bukti_bayar"

if not os.path.exists(FOLDER_GAMBAR):
    os.makedirs(FOLDER_GAMBAR)

# --- FUNGSI KONEKSI ---
def connect_to_gsheet():
    try:
        if os.path.exists("credentials.json"):
            client = gspread.service_account(filename="credentials.json")
        elif "gcp_service_account" in st.secrets:
            client = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        else:
            return None
        return client
    except:
        return None

# --- FUNGSI LOAD DATA ---
def load_data():
    client = connect_to_gsheet()
    if client:
        try:
            sheet = client.open(SHEET_NAME).sheet1
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            if df.empty: return pd.DataFrame()
            if 'Nominal' in df.columns:
                df['Nominal'] = pd.to_numeric(df['Nominal'], errors='coerce').fillna(0)
            if 'Tanggal' in df.columns:
                df['Tahun'] = pd.to_datetime(df['Tanggal']).dt.year
            return df
        except:
            pass
    return pd.DataFrame()

def load_master_warga():
    client = connect_to_gsheet()
    if client:
        try:
            sheet = client.open(SHEET_NAME).worksheet("Data Warga")
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            # Buat ID Unik untuk pencocokan (Blok-No)
            if not df.empty:
                df['ID_Rumah'] = df['Blok'].astype(str) + "-" + df['No'].astype(str)
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

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

# --- UI UTAMA ---
st.title("🏡 Portal Keuangan & Monitoring Warga")
st.markdown("---")

# --- SIDEBAR ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1909/1909672.png", width=100)
st.sidebar.title("Menu Admin")

input_pass = st.sidebar.text_input("🔑 Password Admin", type="password")
is_admin = (input_pass == PASSWORD_RAHASIA)

if is_admin:
    st.sidebar.success("✅ Mode Admin Aktif")
    st.sidebar.markdown("---")
    st.sidebar.header("📝 Input Transaksi")
    
    tipe_transaksi = st.sidebar.radio("Tipe", ["Pemasukan 💰", "Pengeluaran 💸"])
    
    with st.sidebar.form("form_tambah"):
        nama_final = ""
        blok_final = ""
        status_final = "-"
        
        if tipe_transaksi == "Pemasukan 💰":
            df_warga = load_master_warga()
            if not df_warga.empty:
                df_warga['Label'] = df_warga['ID_Rumah'] + " (" + df_warga['Status'] + ") - " + df_warga['Nama Penghuni']
                pilihan_warga = st.selectbox("Pilih Warga", df_warga['Label'].unique())
                data_terpilih = df_warga[df_warga['Label'] == pilihan_warga].iloc[0]
                nama_final = data_terpilih['Nama Penghuni']
                blok_final = data_terpilih['ID_Rumah']
                status_final = data_terpilih['Status']
            else:
                st.warning("Data Warga kosong!")
                nama_final = st.text_input("Nama")
                blok_final = st.text_input("Blok")

            jenis = st.selectbox("Jenis", ["Iuran Wajib", "Kematian", "Agustusan", "Sumbangan", "Lainnya"])
            bulan = st.selectbox("Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember", "-"])
            nominal_input = st.number_input("Nominal", min_value=0, step=5000)
            
        else:
            nama_final = st.text_input("Uraian Pengeluaran")
            blok_final = "-"
            jenis = st.selectbox("Kategori", ["Perbaikan", "Konsumsi", "Honor", "Sosial", "Lainnya"])
            bulan = "-"
            nominal_input = st.number_input("Nominal Keluar", min_value=0, step=5000)
            
        ket = st.text_area("Keterangan")
        uploaded_file = st.file_uploader("Upload Bukti", type=['jpg', 'png'])
        
        if st.form_submit_button("Simpan"):
            if nominal_input > 0:
                with st.spinner("Menyimpan..."):
                    img_name = save_uploaded_file(uploaded_file)
                    final_nominal = nominal_input if tipe_transaksi == "Pemasukan 💰" else -nominal_input
                    new_data = {
                        "ID": int(datetime.now().timestamp()), "Tanggal": datetime.now().strftime("%Y-%m-%d"),
                        "Nama Warga": nama_final, "Blok": blok_final, "Status Rumah": status_final,
                        "Jenis Iuran": jenis, "Bulan": bulan, "Nominal": final_nominal, 
                        "Keterangan": ket, "Bukti Bayar": img_name
                    }
                    save_new_data(new_data)
                    st.success("Tersimpan!")
                    st.rerun()

# --- DASHBOARD ---
df = load_data()
df_warga = load_master_warga()

if not df.empty:
    list_tahun = sorted(df['Tahun'].unique(), reverse=True) if 'Tahun' in df.columns else [datetime.now().year]
    pilih_tahun = st.selectbox("📅 Tahun Laporan", list_tahun)
    df_filtered = df[df['Tahun'] == pilih_tahun] if 'Tahun' in df.columns else df
    
    # Ringkasan
    total_masuk = df_filtered[df_filtered['Nominal'] > 0]['Nominal'].sum()
    total_keluar = df_filtered[df_filtered['Nominal'] < 0]['Nominal'].sum()
    st.metric("Saldo Akhir Kas", f"Rp {total_masuk + total_keluar:,.0f}")

    tab1, tab2, tab3 = st.tabs(["✅ Ceklis Iuran Wajib", "📊 Data Transaksi", "🏠 Database Warga"])

    # --- TAB CEKLIS IURAN WAJIB (FITUR UTAMA) ---
    with tab1:
        st.subheader("Monitoring Pembayaran Iuran Wajib")
        st.caption("🟥 Merah = Belum Bayar | 🟩 Hijau = Lunas | ⬜ Abu = Rumah Kosong")
        
        if not df_warga.empty:
            # 1. Siapkan DataFrame Kosong (Semua Warga x Bulan)
            bulan_urut = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            
            # Buat tabel dasar dari Data Warga
            df_monitor = df_warga[['ID_Rumah', 'Status', 'Nama Penghuni']].copy()
            df_monitor.set_index('ID_Rumah', inplace=True)
            
            # 2. Ambil Data Pembayaran Wajib Tahun Ini
            df_bayar = df_filtered[
                (df_filtered['Jenis Iuran'].str.contains("Wajib", na=False)) & 
                (df_filtered['Nominal'] > 0)
            ]
            
            # 3. Isi Data Pembayaran ke Tabel Monitor
            for bln in bulan_urut:
                df_monitor[bln] = 0 # Set default 0 (Belum Bayar)
                
                # Cek siapa yang bayar di bulan ini
                bayar_bln = df_bayar[df_bayar['Bulan'] == bln]
                for _, row in bayar_bln.iterrows():
                    # Jika Blok warga ada di daftar pembayaran, update jadi nominal
                    if row['Blok'] in df_monitor.index:
                        df_monitor.at[row['Blok'], bln] = row['Nominal']

            # 4. Fungsi Pewarnaan (Styling)
            def warnai_tabel(val):
                if isinstance(val, int) or isinstance(val, float):
                    if val > 0:
                        return 'background-color: #d4edda; color: green' # Hijau (Bayar)
                    elif val == 0:
                        return 'background-color: #f8d7da; color: red' # Merah (Nunggak)
                return ''

            def warnai_baris(row):
                # Jika status Kosong, warna abu-abu semua
                if row['Status'] == 'Kosong':
                    return ['background-color: #e2e3e5; color: #6c757d'] * len(row)
                else:
                    # Logic per sel
                    styles = []
                    for col in row.index:
                        val = row[col]
                        if col in bulan_urut: # Kolom Bulan
                            if val > 0:
                                styles.append('background-color: #88ea88; color: black; font-weight: bold') # Hijau Terang
                            else:
                                styles.append('background-color: #ffaaaa; color: black') # Merah Terang
                        else:
                            styles.append('') # Kolom Nama/Status
                    return styles

            # Tampilkan Tabel
            st.dataframe(
                df_monitor.style.apply(warnai_baris, axis=1).format("{:,.0f}", subset=bulan_urut),
                use_container_width=True,
                height=600
            )
            
        else:
            st.warning("Silakan isi sheet 'Data Warga' di Google Sheets terlebih dahulu.")

    with tab2:
        st.dataframe(df_filtered, use_container_width=True)
        
    with tab3:
        if not df_warga.empty:
            st.dataframe(df_warga, use_container_width=True)

    # ADMIN DELETE
    if is_admin:
        with st.expander("Hapus Data"):
            del_id = st.number_input("ID", min_value=0)
            if st.button("Hapus"):
                if delete_data(del_id):
                    st.success("Dihapus"); st.rerun()
else:
    st.info("Menunggu inisialisasi...")
    if is_admin:
        if st.button("Inisialisasi Header Baru"):
            client = connect_to_gsheet()
            if client:
                sh = client.open(SHEET_NAME).sheet1
                sh.clear()
                sh.append_row(["ID", "Tanggal", "Nama Warga", "Blok", "Status Rumah", "Jenis Iuran", "Bulan", "Nominal", "Keterangan", "Bukti Bayar"])
                st.rerun()