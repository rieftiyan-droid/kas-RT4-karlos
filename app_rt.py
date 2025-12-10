import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
import os

# --- KONFIGURASI ---
st.set_page_config(page_title="Sistem RT Digital", page_icon="🏡", layout="wide")

# PASSWORD ADMIN
PASSWORD_RAHASIA = "admin123"

# NAMA FILE DATABASE
SHEET_NAME = "Database Kas RT"
FOLDER_GAMBAR = "bukti_bayar"

if not os.path.exists(FOLDER_GAMBAR):
    os.makedirs(FOLDER_GAMBAR)

# --- 1. FUNGSI KONEKSI ---
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

# --- 2. LOAD DATA ---
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
                df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
                df['Tahun'] = df['Tanggal'].dt.year
                df['Tanggal'] = df['Tanggal'].dt.strftime('%Y-%m-%d')
            return df
        except: pass
    return pd.DataFrame()

def load_master_warga():
    client = connect_to_gsheet()
    if client:
        try:
            sheet = client.open(SHEET_NAME).worksheet("Data Warga")
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            if not df.empty:
                df['ID_Rumah'] = df['Blok'].astype(str) + "-" + df['No'].astype(str)
                if 'Nama Penghuni' not in df.columns: df['Nama Penghuni'] = ""
            return df
        except: return pd.DataFrame() 
    return pd.DataFrame()

# --- 3. FUNGSI SIMPAN & HAPUS ---
def save_uploaded_file(uploadedfile):
    if uploadedfile is not None:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = os.path.splitext(uploadedfile.name)[1]
            filename = f"IMG_{timestamp}{ext}"
            with open(os.path.join(FOLDER_GAMBAR, filename), "wb") as f:
                f.write(uploadedfile.getbuffer())
            return filename
        except: return "-"
    return "-"

def save_new_data(data):
    client = connect_to_gsheet()
    if client:
        sheet = client.open(SHEET_NAME).sheet1
        sheet.append_row([
            data["ID"], data["Tanggal"], data["Nama Warga"], data["Blok"], 
            data["Status Rumah"], data["Jenis Iuran"], data["Bulan"], 
            int(data["Nominal"]), data["Keterangan"], data["Bukti Bayar"]
        ])

def delete_data(target_id):
    client = connect_to_gsheet()
    if client:
        try:
            sheet = client.open(SHEET_NAME).sheet1
            cell = sheet.find(str(target_id))
            sheet.delete_rows(cell.row)
            return True
        except: return False
    return False

# ==========================================
#               UI APLIKASI
# ==========================================

st.title("🏡 Portal Digital RT 04 RW 18 KPV")
st.caption("Mewujudkan pengelolaan keuangan yang amanah, transparan, dan penuh keberkahan demi kemaslahatan seluruh warga")
st.markdown("---")

# --- A. SIDEBAR ADMIN ---
st.sidebar.title("Menu Admin")
input_pass = st.sidebar.text_input("🔑 Password Admin", type="password")
is_admin = (input_pass == PASSWORD_RAHASIA)

if is_admin:
    st.sidebar.success("✅ Login Sukses")
    st.sidebar.markdown("---")
    
    menu_admin = st.sidebar.selectbox("Pilih Menu:", ["📝 Input Keuangan", "🗑️ Hapus Data"])
    
    # --- 1. INPUT KEUANGAN ---
    if menu_admin == "📝 Input Keuangan":
        st.sidebar.header("Input Transaksi")
        
        # OPSI DI LUAR FORM AGAR INTERAKTIF
        tipe_transaksi = st.sidebar.radio("Tipe", ["Pemasukan 💰", "Pengeluaran 💸"])
        
        sumber_dana = "Warga"
        if tipe_transaksi == "Pemasukan 💰":
            sumber_dana = st.sidebar.radio("Sumber Dana:", ["Warga (Iuran)", "Non-Warga (Umum)"], horizontal=True)
        
        with st.sidebar.form("form_keuangan"):
            nama_final = ""; blok_final = ""; status_final = "-"; jenis = ""; bulan = "-"
            
            # --- LOGIKA INPUT ---
            if tipe_transaksi == "Pemasukan 💰":
                if sumber_dana == "Warga (Iuran)":
                    df_warga = load_master_warga()
                    if not df_warga.empty:
                        df_warga['Label'] = df_warga['ID_Rumah'] + " (" + df_warga['Status'] + ")" + df_warga['Nama Penghuni'].apply(lambda x: " - " + str(x) if str(x).strip() != "" else "")
                        pilih = st.selectbox("Pilih Warga", df_warga['Label'].unique())
                        dt = df_warga[df_warga['Label'] == pilih].iloc[0]
                        nama_final = str(dt['Nama Penghuni']).strip() or f"Warga {dt['ID_Rumah']}"
                        blok_final = dt['ID_Rumah']; status_final = dt['Status']
                    else:
                        st.warning("Data Warga Kosong"); nama_final = st.text_input("Nama"); blok_final = st.text_input("Blok")
                    
                    jenis = st.selectbox("Jenis", ["Iuran Wajib", "Kematian", "Agustusan", "Sumbangan", "Lainnya"])
                    bulan = st.selectbox("Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember", "-"])
                
                else:
                    # NON-WARGA
                    jenis = st.selectbox("Sumber Dana", ["Kas Tahun Lalu", "Dana Desa", "Bunga Bank", "Donasi Eksternal", "Lainnya"])
                    nama_final = jenis
                    blok_final = "-"; status_final = "-"; bulan = "-"
            
            else:
                # PENGELUARAN
                nama_final = st.text_input("Uraian Belanja")
                jenis = st.selectbox("Kategori", ["Perbaikan Fasilitas", "Konsumsi Rapat", "Honor Keamanan/Sampah", "Sosial", "Lainnya"])
                blok_final = "-"
            
            nominal = st.number_input("Nominal (Rp)", min_value=0, step=5000)
            ket = st.text_area("Keterangan")
            file = st.file_uploader("Bukti", type=['jpg','png'])
            
            if st.form_submit_button("Simpan Data"):
                if nominal > 0:
                    img = save_uploaded_file(file)
                    final_nom = nominal if tipe_transaksi == "Pemasukan 💰" else -nominal
                    if not nama_final: nama_final = "Tanpa Nama"
                    new_dt = {
                        "ID": int(datetime.now().timestamp()), "Tanggal": datetime.now().strftime("%Y-%m-%d"),
                        "Nama Warga": nama_final, "Blok": blok_final, "Status Rumah": status_final,
                        "Jenis Iuran": jenis, "Bulan": bulan, "Nominal": final_nom, "Keterangan": ket, "Bukti Bayar": img
                    }
                    save_new_data(new_dt)
                    st.success("Tersimpan!"); st.rerun()
                else: st.warning("Nominal harus diisi.")

    # --- 2. HAPUS DATA ---
    elif menu_admin == "🗑️ Hapus Data":
        st.sidebar.header("Hapus Data")
        id_hapus = st.sidebar.text_input("Masukkan ID (Angka Unik)")
        if st.sidebar.button("Hapus Permanen"):
            if delete_data(id_hapus):
                st.success("Terhapus!"); st.rerun()
            else: st.error("ID tidak ditemukan")

    # --- RESET DATABASE ---
    st.sidebar.markdown("---")
    with st.sidebar.expander("⚠️ Reset System"):
        if st.button("🔴 Buat Header & Tabel Baru"):
            client = connect_to_gsheet()
            if client:
                try:
                    sh1 = client.open(SHEET_NAME).sheet1
                    sh1.clear()
                    sh1.append_row(["ID", "Tanggal", "Nama Warga", "Blok", "Status Rumah", "Jenis Iuran", "Bulan", "Nominal", "Keterangan", "Bukti Bayar"])
                    st.success("✅ Database Siap!")
                    st.rerun()
                except Exception as e: st.error(f"Gagal: {e}")

else:
    st.sidebar.info("👋 Halo Warga! Cek info & kas di sini.")

# --- B. DASHBOARD UTAMA ---
df = load_data()
df_warga = load_master_warga()

if not df.empty:
    col_h, col_f = st.columns([3, 1])
    with col_h: st.subheader("Laporan Keuangan")
    with col_f:
        list_tahun = sorted(df['Tahun'].dropna().unique(), reverse=True)
        if not list_tahun: list_tahun = [datetime.now().year]
        pilih_tahun = st.selectbox("📅 Tahun", list_tahun)
    
    df_filtered = df[df['Tahun'] == pilih_tahun]
    total_masuk = df_filtered[df_filtered['Nominal'] > 0]['Nominal'].sum()
    total_keluar = df_filtered[df_filtered['Nominal'] < 0]['Nominal'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Pemasukan", f"Rp {total_masuk:,.0f}")
    c2.metric("💸 Pengeluaran", f"Rp {abs(total_keluar):,.0f}")
    c3.metric("💳 Saldo Kas", f"Rp {total_masuk + total_keluar:,.0f}")
    st.markdown("---")

    t1, t2, t3, t4 = st.tabs(["✅ Monitoring", "📊 Mutasi", "💸 Rincian Pengeluaran", "🏠 Data Warga"])

    with t1:
        st.caption(f"Ceklis Iuran Wajib {pilih_tahun}")
        if not df_warga.empty:
            bln_list = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            df_mon = df_warga[['ID_Rumah', 'Status', 'Nama Penghuni']].copy(); df_mon.set_index('ID_Rumah', inplace=True)
            df_byr = df_filtered[(df_filtered['Jenis Iuran'].str.contains("Wajib", case=False, na=False)) & (df_filtered['Nominal'] > 0)]
            for b in bln_list:
                df_mon[b] = 0
                sub = df_byr[df_byr['Bulan'] == b]
                for _, r in sub.iterrows():
                    if r['Blok'] in df_mon.index: df_mon.at[r['Blok'], b] = r['Nominal']
            def color(v):
                if isinstance(v, (int, float)): return 'background-color: #d4edda; color: green' if v>0 else 'background-color: #f8d7da; color: red'
                return ''
            st.dataframe(df_mon.style.map(color, subset=bln_list).format("{:,.0f}", subset=bln_list), use_container_width=True, height=500)
        else: st.warning("Data Warga Kosong")

    with t2: st.dataframe(df_filtered[["Tanggal", "Nama Warga", "Jenis Iuran", "Nominal", "Keterangan"]], use_container_width=True)
    
    with t3: 
        keluar = df_filtered[df_filtered['Nominal'] < 0]
        if not keluar.empty: 
            tampil_keluar = keluar[["Tanggal", "Nama Warga", "Jenis Iuran", "Nominal", "Keterangan"]].rename(columns={"Nama Warga": "Uraian Pengeluaran"})
            st.dataframe(tampil_keluar, use_container_width=True)
        else: st.info("Belum ada pengeluaran")
        
    with t4: st.dataframe(df_warga, use_container_width=True)

else: st.info("Database kosong / Belum inisialisasi.")