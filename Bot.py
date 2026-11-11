import os
import html
import logging
import time
from collections import defaultdict
from datetime import datetime
import pytz

import gspread
from requests.exceptions import ConnectionError as RequestsConnectionError
from urllib3.exceptions import ProtocolError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# ==============================
# KONFIGURASI
# ==============================
TOKEN = os.getenv('TELEGRAM_TOKEN')  # Diambil dari environment variable
SPREADSHEET_NAME = 'Home Workout & Habbit'  # Ganti dengan nama file spreadsheet asli
WORKSHEET_NAME = 'Raw_Data'
CREDENTIALS_FILE = 'credentials.json'

# Pilihan data (mudah diubah sesuai kebutuhan)
CATEGORY_OPTIONS = {
    'Expense': ['Food_Beverage', 'Transportation', 'Utilities','Entertainment','Investment','Personal_Care','Maintenance_Repair','Social_Donation'],
    'Income': ['Active_Income', 'Passive_Income','Other_Income'],
}
SUB_CATEGORY_OPTIONS = {
    'Food_Beverage': ['Dine_In', 'Take_Away','Coffee_Snacks','Delivery', 'Groceries'],
    'Transportation': ['Fuel','Parking','Service', 'Public_Transport'],
    'Utilities': ['Internet'],
    'Entertainment': ['Game','Date','Liburan'],
    'Investment': ['RDPU','Trading'],
    'Personal_Care': ['Skincare_Cosmetics','Toiletries','Grooming','Medical_Health'],
    'Maintenance_Repair': ['Electronics','Household','Personal_Items'],
    'Social_Donation': ['Charity_Religion','Family_Support','Gifts_Events'],
    'Active_Income': ['Salary', 'Freelance', 'Bonus'],
    'Passive_Income': ['Investment_Yield', 'Bank_Interest', 'CashBack'],
    'Other_Income': ['Gift', 'Refund'],
}
WALLET_OPTIONS = ['Cash','E-Wallet']
NEEDS_WANTS_OPTIONS = ['Needs', 'Wants', 'N/A']

# Nama state ConversationHandler
TYPE, CATEGORY, SUB_CATEGORY, AMOUNT, WALLET, NOTES, NEEDS_WANTS = range(7)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ==============================
# KONEKSI GOOGLE SHEETS
# ==============================
try:
    gc = gspread.service_account(filename=CREDENTIALS_FILE)
    worksheet = gc.open(SPREADSHEET_NAME).worksheet(WORKSHEET_NAME)
except Exception as e:
    raise SystemExit(f'Gagal terhubung ke Google Sheets: {e}')

CONNECTION_ERRORS = (RequestsConnectionError, ProtocolError, ConnectionError)


def reconnect_worksheet() -> None:
    """Membuat ulang koneksi ke Google Sheets dan memperbarui variabel worksheet global."""
    global worksheet
    gc = gspread.service_account(filename=CREDENTIALS_FILE)
    worksheet = gc.open(SPREADSHEET_NAME).worksheet(WORKSHEET_NAME)
    logger.info('Koneksi Google Sheets dibuat ulang.')


def retry_on_connection_error(func, retries: int = 3):
    """Menjalankan func; jika koneksi terputus, reconnect lalu coba lagi."""
    for attempt in range(1, retries + 1):
        try:
            return func()
        except CONNECTION_ERRORS as e:
            logger.warning('Koneksi terputus (percobaan %d/%d): %s', attempt, retries, e)
            if attempt == retries:
                raise
            time.sleep(attempt)  # jeda makin lama di tiap percobaan
            reconnect_worksheet()


# ==============================
# HELPER
# ==============================
def build_keyboard(options: list[str], prefix: str) -> InlineKeyboardMarkup:
    """Membuat InlineKeyboardMarkup dari daftar opsi, dengan callback_data berprefiks."""
    buttons = [
        [InlineKeyboardButton(opt.replace('_', ' '), callback_data=f'{prefix}:{opt}')]
        for opt in options
    ]
    return InlineKeyboardMarkup(buttons)


def load_to_sheet(data_list: list[str]) -> None:
    """Menulis data ke baris kosong berikutnya secara absolut dari kolom A sampai I."""
    def _write():
        col_a = worksheet.col_values(1)
        next_row = len(col_a) + 1
        cell_range = f'A{next_row}:I{next_row}'
        worksheet.update(
            values=[data_list],
            range_name=cell_range,
            value_input_option='USER_ENTERED',
        )

    retry_on_connection_error(_write)


# ==============================
# HANDLER PERCAKAPAN /tambah
# ==============================
async def tambah_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: /tambah. Menampilkan pilihan Type."""
    context.user_data.clear()
    keyboard = build_keyboard(['Income', 'Expense'], 'type')
    await update.message.reply_text('Pilih tipe transaksi:', reply_markup=keyboard)
    return TYPE


async def select_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """State TYPE: menyimpan pilihan Type lalu menampilkan Category."""
    query = update.callback_query
    await query.answer()
    selected = query.data.split(':', 1)[1]
    context.user_data['type'] = selected

    keyboard = build_keyboard(CATEGORY_OPTIONS[selected], 'category')
    await query.edit_message_text(f'Tipe: {selected}\n\nPilih kategori:', reply_markup=keyboard)
    return CATEGORY


async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """State CATEGORY: menyimpan Category lalu menampilkan Sub-Kategori."""
    query = update.callback_query
    await query.answer()
    selected = query.data.split(':', 1)[1]
    context.user_data['category'] = selected

    keyboard = build_keyboard(SUB_CATEGORY_OPTIONS[selected], 'subcat')
    await query.edit_message_text(f'Kategori: {selected}\n\nPilih sub-kategori:', reply_markup=keyboard)
    return SUB_CATEGORY


async def select_sub_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """State SUB_CATEGORY: menyimpan Sub-Kategori lalu meminta nominal."""
    query = update.callback_query
    await query.answer()
    selected = query.data.split(':', 1)[1]
    context.user_data['sub_category'] = selected

    await query.edit_message_text(f'Sub-kategori: {selected}\n\nKetik nominal (angka saja):')
    return AMOUNT


async def input_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """State AMOUNT: validasi angka lalu menampilkan pilihan Wallet."""
    text = update.message.text.strip().replace('.', '').replace(',', '')
    if not text.isdigit():
        await update.message.reply_text('❌ Nominal harus berupa angka. Silakan ketik ulang:')
        return AMOUNT

    context.user_data['amount'] = int(text)
    keyboard = build_keyboard(WALLET_OPTIONS, 'wallet')
    await update.message.reply_text('Pilih dompet:', reply_markup=keyboard)
    return WALLET


async def select_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """State WALLET: menyimpan Wallet lalu meminta catatan."""
    query = update.callback_query
    await query.answer()
    selected = query.data.split(':', 1)[1]
    context.user_data['wallet'] = selected

    await query.edit_message_text(f'Dompet: {selected}\n\nKetik catatan singkat (ketik - jika kosong):')
    return NOTES


async def input_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """State NOTES: menyimpan catatan lalu menampilkan pilihan Needs/Wants."""
    notes = update.message.text.strip()
    context.user_data['notes'] = '' if notes == '-' else notes

    keyboard = build_keyboard(NEEDS_WANTS_OPTIONS, 'needs')
    await update.message.reply_text('Pilih Needs / Wants:', reply_markup=keyboard)
    return NEEDS_WANTS


async def select_needs_wants(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """State NEEDS_WANTS: menyimpan pilihan terakhir, lalu ETL dan load ke Google Sheets."""
    query = update.callback_query
    await query.answer()
    context.user_data['needs_wants'] = query.data.split(':', 1)[1]

    try:
        # Transform: susun data_list sesuai urutan kolom
        now = datetime.now()
        data_list = [
            now.strftime('%d/%m/%Y'),                  # Date
            now.strftime('%H:%M:%S'),                  # Time
            context.user_data['type'],                 # Type
            context.user_data['category'],             # Category
            context.user_data['sub_category'],         # Sub_Category
            context.user_data['amount'],               # Amount
            context.user_data['wallet'],               # Wallet
            context.user_data['notes'],                # Notes
            context.user_data['needs_wants'],          # Needs_Wants
        ]

        # Load
        load_to_sheet(data_list)

        await query.edit_message_text('✅ Data berhasil dimasukkan ke Database!')

    except gspread.exceptions.APIError as e:
        logger.error('APIError saat load: %s', e)
        await query.edit_message_text(
            '❌ Gagal menyimpan ke Google Sheets. Periksa izin akses atau kuota API.\nKetik /tambah untuk mencoba lagi.'
        )
    except KeyError as e:
        logger.error('Data state hilang: %s', e)
        await query.edit_message_text('❌ Data tidak lengkap. Ketik /tambah untuk mengulang.')
    except Exception as e:
        logger.exception('Error tak terduga: %s', e)
        await query.edit_message_text('❌ Terjadi kesalahan internal. Ketik /tambah untuk mengulang.')

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Membatalkan percakapan kapan saja dengan /batal."""
    context.user_data.clear()
    await update.message.reply_text('Input dibatalkan. Ketik /tambah untuk memulai lagi.')
    return ConversationHandler.END


async def fallback_text_in_button_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mengingatkan user agar memakai tombol jika mengetik teks pada state berbasis tombol."""
    await update.message.reply_text('Silakan pilih menggunakan tombol di atas, atau ketik /batal.')
    return None


# ==============================
# LAPORAN (ConversationHandler)
# ==============================
BULAN_SINGKAT = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun',
                 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
BULAN_PENUH = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
               'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

# State laporan (dibuat berbeda dari state /tambah agar mudah dibaca)
SELECT_MONTH, SELECT_YEAR = range(7, 9)


def parse_date(value) -> datetime | None:
    """Mengubah string DD/MM/YYYY menjadi datetime. Mengembalikan None jika gagal."""
    try:
        return datetime.strptime(str(value).strip(), '%d/%m/%Y')
    except ValueError:
        return None


def to_number(value) -> float:
    """Mengubah nilai sel menjadi angka. Mengembalikan 0 jika tidak valid."""
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace('.', '').replace(',', '').strip() or 0)
    except ValueError:
        return 0.0


def build_month_keyboard() -> InlineKeyboardMarkup:
    """Membuat 12 tombol bulan (4 tombol per baris)."""
    buttons, row = [], []
    for i, nama in enumerate(BULAN_SINGKAT, start=1):
        row.append(InlineKeyboardButton(nama, callback_data=f'lm:{i:02d}'))
        if len(row) == 4:
            buttons.append(row)
            row = []
    return InlineKeyboardMarkup(buttons)


def build_year_keyboard() -> InlineKeyboardMarkup:
    """Membuat tombol tahun: tahun lalu, tahun ini, tahun depan."""
    tahun_ini = datetime.now().year
    years = [tahun_ini - 1, tahun_ini, tahun_ini + 1]
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(str(y), callback_data=f'ly:{y}') for y in years]]
    )


def fetch_monthly_report(month: int, year: int) -> str | None:
    """Mengambil data, memfilter per bulan & tahun, dan mengembalikan teks laporan.
    Mengembalikan None jika tidak ada transaksi pada bulan tersebut."""
    records = retry_on_connection_error(lambda: worksheet.get_all_records())

    filtered = []
    for row in records:
        date_obj = parse_date(row.get('Date', ''))
        if date_obj and date_obj.month == month and date_obj.year == year:
            filtered.append(row)

    if not filtered:
        return None

    total_income = 0.0
    total_expense = 0.0
    expense_by_category = defaultdict(float)

    for row in filtered:
        tipe = str(row.get('Type', '')).strip()
        amount = to_number(row.get('Amount', 0))

        if tipe == 'Income':
            total_income += amount
        elif tipe == 'Expense':
            total_expense += amount
            category = str(row.get('Category', 'Lainnya')).strip() or 'Lainnya'
            expense_by_category[category] += amount

    sisa_saldo = total_income - total_expense
    judul = f'{BULAN_PENUH[month - 1]} {year}'

    lines = [
        f'📊 <b>Laporan Keuangan {html.escape(judul)}</b>',
        '',
        f'💰 Total Income: Rp {total_income:,.0f}',
        f'💸 Total Expense: Rp {total_expense:,.0f}',
        f'🏦 Sisa Saldo: Rp {sisa_saldo:,.0f}',
        '',
        '📂 <b>Rincian Expense per Kategori:</b>',
    ]

    if expense_by_category:
        for category, total in sorted(expense_by_category.items(), key=lambda x: -x[1]):
            lines.append(f'• {html.escape(category)}: Rp {total:,.0f}')
    else:
        lines.append('• Tidak ada data expense.')

    return '\n'.join(lines)


async def laporan_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: /laporan. Menampilkan pilihan bulan."""
    context.user_data.clear()
    await update.message.reply_text(
        'Pilih bulan laporan:', reply_markup=build_month_keyboard()
    )
    return SELECT_MONTH


async def select_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """State SELECT_MONTH: menyimpan bulan lalu menampilkan pilihan tahun."""
    query = update.callback_query
    await query.answer()
    month = int(query.data.split(':', 1)[1])
    context.user_data['laporan_month'] = month

    await query.edit_message_text(
        f'Bulan: {BULAN_PENUH[month - 1]}\n\nPilih tahun:',
        reply_markup=build_year_keyboard(),
    )
    return SELECT_YEAR


async def select_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """State SELECT_YEAR: membuat laporan lalu mengakhiri percakapan."""
    query = update.callback_query
    await query.answer()
    year = int(query.data.split(':', 1)[1])
    month = context.user_data.pop('laporan_month', None)
    context.user_data.clear()

    if month is None:
        await query.edit_message_text('❌ Sesi tidak valid. Ketik /laporan untuk mengulang.')
        return ConversationHandler.END

    await query.edit_message_text('⏳ Mengambil data dari Google Sheets...')

    try:
        report = fetch_monthly_report(month, year)
        if report is None:
            report = f'Belum ada transaksi pada bulan {BULAN_PENUH[month - 1]}-{year}.'
            await query.edit_message_text(report)
        else:
            await query.edit_message_text(report, parse_mode='HTML')

    except CONNECTION_ERRORS as e:
        logger.error('Koneksi ke Google Sheets gagal saat laporan: %s', e)
        await query.edit_message_text(
            '❌ Koneksi ke Google Sheets terputus. Ketik /laporan untuk mencoba lagi.'
        )
    except gspread.exceptions.APIError as e:
        logger.error('APIError saat laporan: %s', e)
        await query.edit_message_text(
            '❌ Gagal mengambil data dari Google Sheets. Ketik /laporan untuk mencoba lagi.'
        )
    except Exception as e:
        logger.exception('Error tak terduga saat laporan: %s', e)
        await query.edit_message_text(
            '❌ Terjadi kesalahan saat membuat laporan. Ketik /laporan untuk mengulang.'
        )

    return ConversationHandler.END


async def cancel_laporan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Membatalkan laporan dengan /batal."""
    context.user_data.clear()
    await update.message.reply_text('Laporan dibatalkan. Ketik /laporan untuk memulai lagi.')
    return ConversationHandler.END


async def fallback_text_laporan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mengingatkan user agar memakai tombol pada state laporan."""
    await update.message.reply_text('Silakan pilih menggunakan tombol di atas, atau ketik /batal.')
    return None


# ==============================
# MAIN
# ==============================
def main() -> None:
    """Menjalankan bot."""
    if not TOKEN:
        raise SystemExit('Environment variable TELEGRAM_TOKEN belum di-set.')

    application: Application = ApplicationBuilder().token(TOKEN).build()

    # ConversationHandler untuk /tambah
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('tambah', tambah_start)],
        states={
            TYPE: [CallbackQueryHandler(select_type, pattern=r'^type:')],
            CATEGORY: [CallbackQueryHandler(select_category, pattern=r'^category:')],
            SUB_CATEGORY: [CallbackQueryHandler(select_sub_category, pattern=r'^subcat:')],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_amount)],
            WALLET: [CallbackQueryHandler(select_wallet, pattern=r'^wallet:')],
            NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_notes)],
            NEEDS_WANTS: [CallbackQueryHandler(select_needs_wants, pattern=r'^needs:')],
        },
        fallbacks=[
            CommandHandler('batal', cancel),
            MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text_in_button_state),
        ],
    )

    # ConversationHandler untuk /laporan
    laporan_conv = ConversationHandler(
        entry_points=[CommandHandler('laporan', laporan_start)],
        states={
            SELECT_MONTH: [CallbackQueryHandler(select_month, pattern=r'^lm:')],
            SELECT_YEAR: [CallbackQueryHandler(select_year, pattern=r'^ly:')],
        },
        fallbacks=[
            CommandHandler('batal', cancel_laporan),
            MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text_laporan),
        ],
    )

    application.add_handler(conv_handler)
    application.add_handler(laporan_conv)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()