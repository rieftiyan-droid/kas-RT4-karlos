import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Kas RT Digital", page_icon="☁️", layout="wide")

# --- PASSWORD ADMIN ---
PASSWORD_RAHASIA = "admin123"

# NAMA FILE & FOLDER
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
        return client.open(SHEET_NAME).sheet1
    except:
        return None

# --- FUNGSI LOAD DATA ---
def load_data():
    sheet = connect_to_gsheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            if df.empty: return pd.DataFrame()
            if 'Nominal' in df.columns:
                df['Nominal'] = pd.to_numeric(df['Nominal'], errors='coerce').fillna(0)
            return df
        except:
            pass
    return pd.DataFrame(columns=["ID", "Tanggal", "Nama Warga", "Blok", "Jenis Iuran", "Bulan", "Nominal", "Keterangan", "Bukti Bayar"])

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
    sheet = connect_to_gsheet()
    if sheet:
        sheet.append_row([data["ID"], data["Tanggal"], data["Nama Warga"], data["Blok"], data["Jenis Iuran"], data["Bulan"], int(data["Nominal"]), data["Keterangan"], data["Bukti Bayar"]])

def delete_data(target_id):
    sheet = connect_to_gsheet()
    if sheet:
        try:
            cell = sheet.find(str(target_id))
            sheet.delete_rows(cell.row)
            return True
        except:
            return False
    return False

# --- UI UTAMA ---
st.title("🏡 Portal Informasi Kas RT")
st.caption("Transparansi Keuangan Warga")
st.markdown("---")

# --- SIDEBAR: LOGIN ADMIN ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1909/1909672.png", width=100)
st.sidebar.title("Menu Akses")

input_pass = st.sidebar.text_input("🔑 Password Admin", type="password", placeholder="Isi untuk edit data...")
is_admin = (input_pass == PASSWORD_RAHASIA)

if is_admin:
    st.sidebar.success("✅ Mode Admin Aktif")
    st.sidebar.markdown("---")
    st.sidebar.header("📝 Input Data Baru")
    
    with st.sidebar.form("form_tambah"):
        nama = st.text_input("Nama Warga")
        blok = st.text_input("Blok / No Rumah")
        jenis = st.selectbox("Jenis Iuran", ["Iuran Wajib", "Kematian", "Agustusan", "Sumbangan", "Lainnya"])
        bulan = st.selectbox("Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember", "-"])
        nominal = st.number_input("Nominal", min_value=0, step=5000)
        ket = st.text_area("Keterangan")
        st.markdown("**Bukti Bayar**")
        uploaded_file = st.file_uploader("Upload Foto", type=['jpg', 'png'])
        
        if st.form_submit_button("Simpan Data"):
            if nama and nominal > 0:
                with st.spinner("Menyimpan..."):
                    img_name = save_uploaded_file(uploaded_file)
                    new_data = {
                        "ID": int(datetime.now().timestamp()),
                        "Tanggal": datetime.now().strftime("%Y-%m-%d"),
                        "Nama Warga": nama, "Blok": blok, "Jenis Iuran": jenis,
                        "Bulan": bulan, "Nominal": nominal, "Keterangan": ket,
                        "Bukti Bayar": img_name
                    }
                    save_new_data(new_data)
                    st.success("Tersimpan!")
                    st.rerun()
else:
    st.sidebar.info("👋 Halo Warga! Silakan cek status pembayaran Anda di layar utama.")

# --- DASHBOARD WARGA (VIEW ONLY) ---
df = load_data()

if not df.empty:
    # FITUR BARU: TAB VIEW WARGA
    tab1, tab2, tab3 = st.tabs(["📊 Rekap Kas", "📅 Laporan Per Bulan", "✅ Kartu Iuran Wajib"])

    # TAB 1: DASHBOARD UMUM
    with tab1:
        col1, col2 = st.columns(2)
        col1.metric("Total Saldo Kas", f"Rp {df['Nominal'].sum():,.0f}")
        col2.metric("Total Transaksi", f"{len(df)} Kali")
        
        st.subheader("Grafik Pemasukan")
        if 'Jenis Iuran' in df.columns:
            fig = px.bar(df, x="Jenis Iuran", y="Nominal", color="Jenis Iuran", title="Pemasukan per Kategori")
            st.plotly_chart(fig, use_container_width=True)
            
        st.subheader("Galeri Bukti Transfer Terkini")
        if 'Bukti Bayar' in df.columns:
            df_img = df[df['Bukti Bayar'] != "-"]
            if not df_img.empty:
                # Tampilkan 3 gambar terakhir saja biar rapi
                cols = st.columns(3)
                for idx, row in df_img.tail(3).iterrows():
                    fpath = os.path.join(FOLDER_GAMBAR, row['Bukti Bayar'])
                    if os.path.exists(fpath):
                        with cols[idx % 3]:
                            st.image(fpath, caption=f"{row['Nama Warga']} ({row['Nominal']})", use_container_width=True)

    # TAB 2: LAPORAN PER BULAN (FILTER)
    with tab2:
        st.header("Siapa yang bayar bulan ini?")
        pilih_bulan = st.selectbox("Pilih Bulan:", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
        
        # Filter data
        df_bulan = df[df['Bulan'] == pilih_bulan]
        
        if not df_bulan.empty:
            st.success(f"Ditemukan {len(df_bulan)} pembayaran di bulan {pilih_bulan}")
            # Tampilkan tabel sederhana
            st.dataframe(df_bulan[["Tanggal", "Nama Warga", "Blok", "Jenis Iuran", "Nominal"]], use_container_width=True, hide_index=True)
            st.metric(f"Total Masuk {pilih_bulan}", f"Rp {df_bulan['Nominal'].sum():,.0f}")
        else:
            st.warning(f"Belum ada data pembayaran untuk bulan {pilih_bulan}.")

    # TAB 3: MATRIKS IURAN WAJIB (FITUR UTAMA)
    with tab3:
        st.header("Kartu Kontrol Iuran Wajib")
        st.caption("Ceklis pembayaran 'Iuran Wajib' per warga selama setahun.")
        
        # 1. Filter hanya jenis 'Iuran Wajib' (atau yang mengandung kata Wajib)
        df_wajib = df[df['Jenis Iuran'].str.contains("Wajib", case=False, na=False)]
        
        if not df_wajib.empty:
            # 2. Buat Pivot Table (Baris=Nama, Kolom=Bulan, Isi=Nominal)
            # aggfunc='sum' dipakai kalau ada warga bayar 2x (dicicil), dijumlahkan.
            df_pivot = df_wajib.pivot_table(index="Nama Warga", columns="Bulan", values="Nominal", aggfunc='sum')
            
            # 3. Urutkan Kolom Bulan (Biar gak urut Abjad April duluan)
            urutan_bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            # Hanya ambil bulan yang ada datanya saja, tapi diurutkan sesuai kalender
            cols_ada = [b for b in urutan_bulan if b in df_pivot.columns]
            df_pivot = df_pivot[cols_ada]
            
            # 4. Ganti NaN (Kosong) dengan tanda "-" atau 0 biar rapi
            df_pivot = df_pivot.fillna(0)
            
            # 5. Tampilkan dengan Format Highlight
            # Kita pakai style pandas untuk mewarnai background
            st.dataframe(
                df_pivot.style.format("Rp {:,.0f}").background_gradient(cmap="Greens", vmin=1, vmax=100000),
                use_container_width=True
            )
            st.info("💡 **Tips:** Warna HIJAU artinya sudah bayar. Jika kolom bulan belum muncul, berarti belum ada warga yang bayar di bulan tersebut.")
        else:
            st.warning("Belum ada data transaksi 'Iuran Wajib' yang terekam.")

    # --- FITUR HAPUS (ADMIN ONLY) ---
    if is_admin:
        st.markdown("---")
        with st.expander("⚠️ Admin: Hapus Data"):
            del_id = st.number_input("ID Hapus", min_value=0)
            if st.button("Hapus Permanen"):
                if delete_data(del_id):
                    st.success("Dihapus!")
                    st.rerun()
                else:
                    st.error("Gagal hapus.")
else:
    st.info("Database kosong. Klik tombol inisialisasi di bawah (Mode Admin).")
    if is_admin:
        if st.button("Inisialisasi Header"):
            sh = connect_to_gsheet()
            sh.append_row(["ID", "Tanggal", "Nama Warga", "Blok", "Jenis Iuran", "Bulan", "Nominal", "Keterangan", "Bukti Bayar"])
            st.rerun()
