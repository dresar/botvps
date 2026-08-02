# Panduan Kontribusi — Serverinka Guardian

Terima kasih telah berminat untuk berkontribusi pada proyek open source **Serverinka Guardian**!

---

## 📜 Standard & Rules Aturan Kode Ketat

Sebelum menulis kode, Anda **WAJIB** membaca dan mematuhi dokumen aturan pengembangan kami di [`docs/10_DEVELOPMENT_RULES.md`](docs/10_DEVELOPMENT_RULES.md). Ringkasannya:

1. **Struktur File:** Tidak ada file Python yang melebihi **500 baris kode**.
2. **Type Hinting:** Semua fungsi, atribut, dan variabel publik WAJIB memiliki type hint yang ketat (`mypy --strict`).
3. **Asynchronous First:** Semua operasi I/O (Database, Network, Subprocess, Filesystem) WAJIB berbasis `async/await`.
4. **Keamanan Sandbox:** Dilarang keras menggunakan `shell=True` atau string concatenation untuk eksekusi subprocess. Wajib menggunakan `guardian.utils.sandbox.run_command`.
5. **Format HTML:** Semua respon Telegram bot WAJIB di-escape menggunakan `guardian.utils.formatters.escape_html`.

---

## 🛠️ Alur Pengembangan

### 1. Fork & Clone Repository

```bash
git clone https://github.com/your-username/serverinka-guardian.git
cd serverinka-guardian
```

### 2. Persiapan Environment

Gunakan `uv` untuk mengelola environment:

```bash
uv sync --extra dev
```

### 3. Mengembangkan Fitur atau Fix Bug

Buat branch baru dari `main`:

```bash
git checkout -b feature/nama-fitur
# atau
git checkout -b fix/deskripsi-bug
```

### 4. Validasi Sebelum Commit

Sebelum membuka Pull Request, pastikan 3 perintah berikut lolos tanpa error:

```bash
# 1. Linting & Formatting
uv run ruff check .

# 2. Type Checking
uv run mypy guardian

# 3. Unit & Integration Testing
uv run pytest
```

---

## 🔌 Mengembangkan Plugin Baru

Jika Anda ingin menambahkan modul/plugin baru:
1. Buat folder baru di bawah `guardian/plugins/<nama_plugin>/`.
2. Pastikan terdapat `plugin.py` yang mewarisi class `guardian.interfaces.base_plugin.BasePlugin`.
3. Daftarkan semua handler menggunakan namespace unik.
4. Sertakan unit test di `tests/unit/plugins/test_<nama_plugin>.py`.

---

## 📬 Mengajukan Pull Request (PR)

- Berikan judul PR yang jelas (misal: `feat(docker): Tambahkan opsi restart container with timeout`).
- Jelaskan perubahan yang Anda buat serta cara pengujiannya pada deskripsi PR.
- Pastikan semua pipeline di GitHub Actions berjalan dengan hijau (pass).
