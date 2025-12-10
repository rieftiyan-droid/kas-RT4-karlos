import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
import os

# --- KONFIGURASI ---
st.set_page_config(page_title="Sistem Kas RT Digital", page_icon="🏡", layout="wide")

# PASSWORD ADMIN
PASSWORD_RAHASIA = "adminsaja1234"

# NAMA FILE DATABASE GOOGLE SHEET
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
                df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
                df['Tahun'] = df['Tanggal'].dt.year
                df['Tanggal'] = df['Tanggal'].dt.strftime('%Y-%m-%d')
                
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
            if not df.empty:
                df['ID_Rumah'] = df['Blok'].astype(str) + "-" + df['No'].astype(str)
                # Pastikan kolom Nama Penghuni ada, kalau tidak ada anggap string kosong
                if 'Nama Penghuni' not in df.columns:
                    df['Nama Penghuni'] = ""
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

# ==========================================
#               TAMPILAN UTAMA
# ==========================================

st.title("🏡 Portal Keuangan & Kas RT 4 RW 18 KPV")
st.caption("Mewujudkan pengelolaan keuangan yang amanah, transparan, dan penuh keberkahan demi kemaslahatan seluruh warga")
st.markdown("---")

# --- SIDEBAR (LOGIN & ADMIN) ---
st.sidebar.title("Menu Admin")
input_pass = st.sidebar.text_input("🔑 Password Admin", type="password")
is_admin = (input_pass == PASSWORD_RAHASIA)

if is_admin:
    st.sidebar.success("✅ Mode Admin Aktif")
    st.sidebar.markdown("---")
    
    # --- FORM INPUT ---
    st.sidebar.header("📝 Input Transaksi")
    tipe_transaksi = st.sidebar.radio("Tipe Transaksi", ["Pemasukan 💰", "Pengeluaran 💸"])
    
    with st.sidebar.form("form_tambah"):
        nama_final = ""
        blok_final = ""
        status_final = "-"
        jenis = ""
        bulan = "-"
        
        # LOGIKA INPUT PEMASUKAN
        if tipe_transaksi == "Pemasukan 💰":
            sumber_dana = st.radio("Sumber Dana:", ["Dari Warga", "Luar Warga (Umum)"], horizontal=True)
            
            if sumber_dana == "Dari Warga":
                df_warga = load_master_warga()
                if not df_warga.empty:
                    # Bikin label dropdown. Kalau nama kosong, cuma tampilkan Blok.
                    df_warga['Label'] = df_warga['ID_Rumah'] + " (" + df_warga['Status'] + ")" + df_warga['Nama Penghuni'].apply(lambda x: " - " + str(x) if str(x).strip() != "" else "")
                    
                    pilihan_warga = st.selectbox("Pilih Warga", df_warga['Label'].unique())
                    data_terpilih = df_warga[df_warga['Label'] == pilihan_warga].iloc[0]
                    
                    # LOGIKA BARU: Jika nama kosong, pakai ID Rumah
                    nama_asli = str(data_terpilih['Nama Penghuni']).strip()
                    if nama_asli == "":
                        nama_final = f"Warga {data_terpilih['ID_Rumah']}" # Contoh: Warga AA-1
                    else:
                        nama_final = nama_asli
                        
                    blok_final = data_terpilih['ID_Rumah']
                    status_final = data_terpilih['Status']
                else:
                    st.warning("⚠️ Data Warga kosong!"); nama_final = st.text_input("Nama Warga"); blok_final = st.text_input("Blok")
                
                jenis = st.selectbox("Jenis Iuran", ["Iuran Wajib", "Kematian", "Agustusan", "Sumbangan Sukarela", "Lainnya"])
                bulan = st.selectbox("Untuk Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember", "-"])
            else: 
                jenis = st.selectbox("Sumber Pemasukan", ["Kas Tahun Sebelumnya", "Dana Desa/RW", "Bunga Bank", "Donasi Eksternal", "Lainnya"])
                nama_final = jenis; blok_final = "-"; status_final = "-"; bulan = "-" 
            
            nominal_input = st.number_input("Nominal (Rp)", min_value=0, step=5000)
            
        else: # PENGELUARAN
            nama_final = st.text_input("Uraian Pengeluaran")
            jenis = st.selectbox("Kategori", ["Perbaikan Fasilitas", "Konsumsi Rapat", "Honor Keamanan/Sampah", "Sosial", "Lainnya"])
            blok_final = "-"; status_final = "-"; bulan = "-" 
            nominal_input = st.number_input("Nominal Keluar (Rp)", min_value=0, step=5000)
            
        ket = st.text_area("Keterangan (Opsional)")
        uploaded_file = st.file_uploader("Upload Bukti", type=['jpg', 'png'])
        
        if st.form_submit_button("Simpan Data"):
            # Validasi diperlonggar: Asal Nominal diisi, simpan!
            if nominal_input > 0:
                with st.spinner("Menyimpan..."):
                    img_name = save_uploaded_file(uploaded_file)
                    final_nominal = nominal_input if tipe_transaksi == "Pemasukan 💰" else -nominal_input
                    
                    # Pastikan nama tidak kosong total saat disimpan
                    if not nama_final: nama_final = "Tanpa Nama"

                    new_data = {
                        "ID": int(datetime.now().timestamp()), "Tanggal": datetime.now().strftime("%Y-%m-%d"),
                        "Nama Warga": nama_final, "Blok": blok_final, "Status Rumah": status_final,
                        "Jenis Iuran": jenis, "Bulan": bulan, "Nominal": final_nominal, "Keterangan": ket, "Bukti Bayar": img_name
                    }
                    save_new_data(new_data)
                    st.success("✅ Tersimpan!"); st.rerun()
            else:
                st.warning("⚠️ Nominal uang wajib diisi (tidak boleh 0).")

    # --- TOMBOL RESET ---
    st.sidebar.markdown("---")
    with st.sidebar.expander("⚠️ Area Reset"):
        if st.button("🔴 Reset Database & Header"):
            client = connect_to_gsheet()
            if client:
                try:
                    sh = client.open(SHEET_NAME).sheet1
                    sh.clear()
                    sh.append_row(["ID", "Tanggal", "Nama Warga", "Blok", "Status Rumah", "Jenis Iuran", "Bulan", "Nominal", "Keterangan", "Bukti Bayar"])
                    st.success("✅ Database berhasil diperbaiki!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal: {e}")
                
else:
    st.sidebar.info("👋 Halo Warga RT 4 RW 18 KPV! Cek transparansi kas di sini.")

# --- DASHBOARD UTAMA ---
df = load_data()
df_warga = load_master_warga()

if not df.empty:
    col_h, col_f = st.columns([3, 1])
    with col_h: st.subheader("Laporan Keuangan RT")
    with col_f:
        list_tahun = sorted(df['Tahun'].dropna().unique(), reverse=True)
        if not list_tahun: list_tahun = [datetime.now().year]
        pilih_tahun = st.selectbox("📅 Tahun", list_tahun)
    
    df_filtered = df[df['Tahun'] == pilih_tahun]
    total_masuk = df_filtered[df_filtered['Nominal'] > 0]['Nominal'].sum()
    total_keluar = df_filtered[df_filtered['Nominal'] < 0]['Nominal'].sum()
    saldo_akhir = total_masuk + total_keluar
    
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Pemasukan", f"Rp {total_masuk:,.0f}")
    c2.metric("💸 Pengeluaran", f"Rp {abs(total_keluar):,.0f}")
    c3.metric("💳 Saldo Kas", f"Rp {saldo_akhir:,.0f}")
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(["✅ Monitoring Warga", "📊 Mutasi Kas", "💸 Rincian Pengeluaran", "🏠 Data Warga"])

    with tab1:
        st.caption(f"Status Iuran Wajib Warga Tahun {pilih_tahun}")
        if not df_warga.empty:
            bulan_urut = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            df_monitor = df_warga[['ID_Rumah', 'Status', 'Nama Penghuni']].copy(); df_monitor.set_index('ID_Rumah', inplace=True)
            df_bayar = df_filtered[(df_filtered['Jenis Iuran'].str.contains("Wajib", case=False, na=False)) & (df_filtered['Nominal'] > 0)]
            for bln in bulan_urut:
                df_monitor[bln] = 0 
                bayar_bln = df_bayar[df_bayar['Bulan'] == bln]
                for _, row in bayar_bln.iterrows():
                    if row['Blok'] in df_monitor.index: df_monitor.at[row['Blok'], bln] = row['Nominal']
            def warnai_sel(val):
                if isinstance(val, (int, float)):
                    if val > 0: return 'background-color: #d4edda; color: green'
                    if val == 0: return 'background-color: #f8d7da; color: red'
                return ''
            st.dataframe(df_monitor.style.map(warnai_sel, subset=bulan_urut).format("{:,.0f}", subset=bulan_urut), use_container_width=True, height=600)
        else:
            st.warning("⚠️ Data Warga belum ada.")

    with tab2: st.dataframe(df_filtered[["Tanggal", "Nama Warga", "Jenis Iuran", "Nominal", "Keterangan"]], use_container_width=True)
    with tab3:
        df_keluar = df_filtered[df_filtered['Nominal'] < 0]
        if not df_keluar.empty: st.dataframe(df_keluar[["Tanggal", "Nama Warga", "Jenis Iuran", "Nominal", "Keterangan"]], use_container_width=True)
        else: st.info("Belum ada pengeluaran.")
    with tab4: st.dataframe(df_warga, use_container_width=True)
    
    if is_admin:
        st.markdown("---")
        with st.expander("⚠️ Hapus Data per Baris"):
            id_hapus = st.number_input("ID Hapus", min_value=0)
            if st.button("Hapus Permanen"):
                if delete_data(id_hapus): st.success("Terhapus"); st.rerun()
                else: st.error("Gagal")
else:
    st.info("Database kosong.")