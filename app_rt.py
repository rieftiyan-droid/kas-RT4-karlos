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
            
            # Paksa Nominal jadi Angka
            if 'Nominal' in df.columns:
                df['Nominal'] = pd.to_numeric(df['Nominal'], errors='coerce').fillna(0)
            
            # Ekstrak Tahun dari Tanggal (Format YYYY-MM-DD)
            if 'Tanggal' in df.columns:
                df['Tahun'] = pd.to_datetime(df['Tanggal']).dt.year
                
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
        sheet.append_row([
            data["ID"], data["Tanggal"], data["Nama Warga"], 
            data["Blok"], data["Jenis Iuran"], data["Bulan"], 
            int(data["Nominal"]), data["Keterangan"], data["Bukti Bayar"]
        ])

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
st.title("🏡 Portal Keuangan & Kas RT")
st.markdown("---")

# --- SIDEBAR: LOGIN ADMIN ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1909/1909672.png", width=100)
st.sidebar.title("Menu Admin")

input_pass = st.sidebar.text_input("🔑 Password Admin", type="password", placeholder="Masuk untuk input...")
is_admin = (input_pass == PASSWORD_RAHASIA)

if is_admin:
    st.sidebar.success("✅ Mode Admin Aktif")
    st.sidebar.markdown("---")
    st.sidebar.header("📝 Input Transaksi")
    
    # PILIHAN: MASUK ATAU KELUAR
    tipe_transaksi = st.sidebar.radio("Tipe Transaksi", ["Pemasukan 💰", "Pengeluaran 💸"])
    
    with st.sidebar.form("form_tambah"):
        if tipe_transaksi == "Pemasukan 💰":
            st.subheader("Input Pemasukan")
            nama = st.text_input("Nama Warga")
            blok = st.text_input("Blok / No Rumah")
            jenis = st.selectbox("Jenis Pemasukan", ["Iuran Wajib", "Kematian", "Agustusan", "Sumbangan", "Lainnya"])
            bulan = st.selectbox("Untuk Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember", "-"])
            nominal_input = st.number_input("Nominal (Rp)", min_value=0, step=5000)
            
        else: # PENGELUARAN
            st.subheader("Input Pengeluaran")
            nama = st.text_input("Keperluan / Uraian (Misal: Beli Lampu)")
            blok = "-" # Tidak pakai blok
            jenis = st.selectbox("Kategori Pengeluaran", ["Perbaikan Fasilitas", "Konsumsi Rapat", "Honor Keamanan/Sampah", "Sosial", "Lainnya"])
            bulan = "-"
            nominal_input = st.number_input("Nominal Keluar (Rp)", min_value=0, step=5000)
            
        ket = st.text_area("Keterangan Tambahan")
        st.markdown("**Upload Bukti/Struk**")
        uploaded_file = st.file_uploader("Upload Foto", type=['jpg', 'png'])
        
        if st.form_submit_button("Simpan Transaksi"):
            if nama and nominal_input > 0:
                with st.spinner("Menyimpan..."):
                    img_name = save_uploaded_file(uploaded_file)
                    
                    # LOGIKA PENTING: Jika Pengeluaran, jadikan NEGATIF
                    final_nominal = nominal_input if tipe_transaksi == "Pemasukan 💰" else -nominal_input
                    
                    new_data = {
                        "ID": int(datetime.now().timestamp()),
                        "Tanggal": datetime.now().strftime("%Y-%m-%d"),
                        "Nama Warga": nama, 
                        "Blok": blok, 
                        "Jenis Iuran": jenis,
                        "Bulan": bulan, 
                        "Nominal": final_nominal, 
                        "Keterangan": ket,
                        "Bukti Bayar": img_name
                    }
                    save_new_data(new_data)
                    st.success("Tersimpan!")
                    st.rerun()
else:
    st.sidebar.info("👋 Halo Warga! Lihat transparansi dana di layar utama.")

# --- DASHBOARD UTAMA ---
df = load_data()

if not df.empty:
    # --- FITUR BARU: FILTER TAHUN ---
    col_judul, col_filter = st.columns([3, 1])
    with col_judul:
        st.subheader("Laporan Keuangan")
    with col_filter:
        # Ambil daftar tahun unik dari data
        list_tahun = sorted(df['Tahun'].unique(), reverse=True)
        if not list_tahun: list_tahun = [datetime.now().year]
        pilih_tahun = st.selectbox("📅 Pilih Tahun", list_tahun)
    
    # Filter Data Berdasarkan Tahun yang Dipilih
    df_filtered = df[df['Tahun'] == pilih_tahun]
    
    if not df_filtered.empty:
        # Hitung Ringkasan
        total_masuk = df_filtered[df_filtered['Nominal'] > 0]['Nominal'].sum()
        total_keluar = df_filtered[df_filtered['Nominal'] < 0]['Nominal'].sum() # Hasilnya minus
        saldo_akhir = total_masuk + total_keluar # Plus + Minus = Sisa
        
        # Tampilkan Kartu (Metrics)
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Total Pemasukan", f"Rp {total_masuk:,.0f}")
        col2.metric("💸 Total Pengeluaran", f"Rp {abs(total_keluar):,.0f}") # Abs agar tampil positif tapi merah
        col3.metric("in Sisa Saldo Tahun Ini", f"Rp {saldo_akhir:,.0f}", delta_color="normal")
        
        st.markdown("---")

        # TABULASI MENU
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Mutasi Kas", "📅 Laporan Bulanan", "✅ Kartu Iuran Wajib", "💸 Rincian Pengeluaran"])

        # TAB 1: MUTASI KAS (SEMUA TRANSAKSI)
        with tab1:
            st.caption(f"Semua transaksi di tahun {pilih_tahun}")
            # Warna tabel: Merah jika pengeluaran (minus), Standar jika pemasukan
            def highlight_pengeluaran(val):
                color = '#ffcccc' if val < 0 else ''
                return f'background-color: {color}'
            
            st.dataframe(
                df_filtered[["Tanggal", "Nama Warga", "Jenis Iuran", "Nominal", "Keterangan"]]
                .style.format({"Nominal": "Rp {:,.0f}"})
                .map(highlight_pengeluaran, subset=['Nominal']),
                use_container_width=True, hide_index=True
            )

        # TAB 2: LAPORAN PER BULAN
        with tab2:
            bulan_opsi = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            pilih_bulan = st.selectbox("Filter Bulan:", bulan_opsi)
            
            # Filter Data Bulan & Tahun
            df_bulan = df_filtered[df_filtered['Bulan'] == pilih_bulan]
            # Kita juga ambil data berdasarkan tanggal bulan jika kolom 'Bulan' kosong (untuk pengeluaran)
            # Tapi biar simpel, kita pakai filter manual yang ada saja dulu.
            
            if not df_bulan.empty:
                st.dataframe(df_bulan[["Tanggal", "Nama Warga", "Jenis Iuran", "Nominal"]], use_container_width=True)
                sum_bulan = df_bulan['Nominal'].sum()
                st.info(f"Netto (Masuk - Keluar) Bulan {pilih_bulan}: **Rp {sum_bulan:,.0f}**")
            else:
                st.warning(f"Tidak ada catatan Iuran Warga bulan {pilih_bulan} di tahun {pilih_tahun}.")

        # TAB 3: KARTU IURAN WAJIB (Hanya Pemasukan Positif)
        with tab3:
            st.caption("Ceklis pembayaran Warga (Khusus Iuran Wajib)")
            # Filter hanya Iuran Wajib DAN Nominal Positif
            df_wajib = df_filtered[
                (df_filtered['Jenis Iuran'].str.contains("Wajib", case=False, na=False)) & 
                (df_filtered['Nominal'] > 0)
            ]
            
            if not df_wajib.empty:
                df_pivot = df_wajib.pivot_table(index="Nama Warga", columns="Bulan", values="Nominal", aggfunc='sum')
                cols_ada = [b for b in bulan_opsi if b in df_pivot.columns] # Urutkan bulan
                df_pivot = df_pivot[cols_ada].fillna(0)
                st.dataframe(df_pivot.style.format("Rp {:,.0f}").background_gradient(cmap="Greens", vmin=1), use_container_width=True)
            else:
                st.warning("Belum ada data Iuran Wajib tahun ini.")

        # TAB 4: RINCIAN PENGELUARAN (Tab Baru)
        with tab4:
            st.subheader(f"Daftar Pengeluaran Tahun {pilih_tahun}")
            df_keluar = df_filtered[df_filtered['Nominal'] < 0] # Ambil yang minus
            
            if not df_keluar.empty:
                # Bikin grafik pie chart sederhana
                fig = px.pie(df_keluar, values=df_keluar['Nominal'].abs(), names='Jenis Iuran', title='Komposisi Pengeluaran')
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(
                    df_keluar[["Tanggal", "Nama Warga", "Jenis Iuran", "Nominal", "Keterangan"]]
                    .style.format({"Nominal": "Rp {:,.0f}"}), 
                    use_container_width=True
                )
            else:
                st.success("Belum ada pengeluaran tercatat tahun ini. Hemat pangkal kaya! 😉")

    else:
        st.info(f"Belum ada data transaksi di tahun {pilih_tahun}.")

    # --- HAPUS DATA (ADMIN) ---
    if is_admin:
        st.markdown("---")
        with st.expander("⚠️ Hapus Data (Admin)"):
            del_id = st.number_input("ID Hapus", min_value=0)
            if st.button("Hapus Permanen"):
                if delete_data(del_id):
                    st.success("Dihapus!")
                    st.rerun()
                else:
                    st.error("Gagal.")
else:
    st.info("Database kosong.")
    if is_admin:
        if st.button("Inisialisasi Awal"):
            sh = connect_to_gsheet()
            sh.append_row(["ID", "Tanggal", "Nama Warga", "Blok", "Jenis Iuran", "Bulan", "Nominal", "Keterangan", "Bukti Bayar"])
            st.rerun()