# Version-1.0-Automated-Data-Pipeline-Analytics

# 📊 Personal Finance Data Pipeline (Version 1.0)

Sebuah sistem *End-to-End Data Pipeline* otomatis yang dirancang untuk menyederhanakan pencatatan dan analisis keuangan pribadi. Proyek ini menghilangkan hambatan pengisian data manual dengan memanfaatkan antarmuka bot Telegram yang interaktif, melakukan proses ETL (Extract, Transform, Load) di *cloud*, dan menyimpannya ke arsitektur *Data Warehouse* berbasis Google Sheets untuk divisualisasikan.

## 🛠️ Arsitektur Sistem & Tech Stack

Alur kerja data pada sistem ini dirancang dengan prinsip pemisahan tugas (*separation of concerns*):
1. **Frontend / Data Entry:** Telegram Bot API (Antarmuka interaktif dengan *State Management*).
2. **Backend / ETL:** Python 3.10+ (Berjalan 24/7 di PythonAnywhere).
3. **Data Warehouse:** Google Sheets (Diatur dalam format *Tidy Data*).
4. **Data Visualization (On-Demand):** Matplotlib (In-memory processing) & Looker Studio.

**Libraries Utama:**
`python-telegram-bot` (v20+ Async), `gspread`, `google-auth`, `matplotlib`, `pytz`.

## ✨ Fitur Utama (Core Features)

* **Interactive State Management:** Pengalaman pengguna (UX) yang mulus dengan navigasi tombol *InlineKeyboardMarkup* (termasuk fitur "Kembali" dan "Batal") untuk meminimalisir *human error* saat *data entry*.
* **Bulletproof Data Load:** Skrip dirancang untuk mendeteksi baris kosong sesungguhnya di Google Sheets, menghindari anomali data bertumpuk akibat format sel yang tertinggal.
* **Timezone Standardization:** Integrasi `pytz` (`Asia/Jakarta`) untuk memastikan *timestamp* transaksi selalu akurat terlepas dari lokasi fisik *server cloud*.
* **On-Demand Micro-Analytics:** Fitur laporan dinamis per bulan/tahun yang langsung di-render (*in-memory*) menjadi *Horizontal Bar Chart* detail (level Sub-Kategori) di dalam chat Telegram tanpa membebani penyimpanan *server*.

## 📸 Dokumentasi Visual (Screenshots)

*(Tambahkan gambar dengan format: `![Deskripsi Gambar](link_gambar)` di sini)*

1. **Antarmuka Bot (Data Entry):** <img width="396" height="173" alt="Screen Shot 2026-11-11 at 15 20 11" src="https://github.com/user-attachments/assets/03b31865-5066-4ba0-b5c1-322192b8a82c" />
2. **Visualisasi In-App (Matplotlib):** <img width="1189" height="1273" alt="photo_6307699691327525974_y" src="https://github.com/user-attachments/assets/cb2bacb4-c500-414d-bda0-e08c9d46d660" />
3. **Skema Database (Google Sheets):** <img width="791" height="305" alt="Screen Shot 2026-11-11 at 16 51 01" src="https://github.com/user-attachments/assets/7e8e3334-1064-451e-ac6e-b4d9c62e5be3" />

## 🚀 Roadmap Pengembangan (Fase Selanjutnya)

Proyek ini masih terus berkembang. Peta jalan pengembangan selanjutnya meliputi:
- [ ] **Fase 3 (AI/NLP Integration):** Mengganti sistem tombol statis dengan pemrosesan bahasa alami (NLP). Pengguna cukup mengetik "Beli kopi susu 25 ribu", dan model Machine Learning akan otomatis mengklasifikasikan `Category` dan `Sub_Category` yang tepat berdasarkan histori dataset. Menunggu pengumpulan data historis yang valid selama 3-4 bulan.

---
*Dibuat oleh Hadi Nurjaman - Terhubung dengan saya di www.linkedin.com/in/hadi-nurjaman*
