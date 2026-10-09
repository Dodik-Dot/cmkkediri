# configcmk — Monitoring Checkmk untuk Linux, Windows, dan Android

Kumpulan installer, local checks, plugin inventory, dan aplikasi Android `cmkagent` untuk memantau perangkat operasional melalui Checkmk. Repository ini **bukan implementasi server Checkmk**; server memakai image upstream, sedangkan pemeriksaan tambahan dan agen Android dikembangkan di sini.

Kredit untuk fondasi skrip: [andin1st/scriptcmk](https://github.com/andin1st/scriptcmk/). Status audit: berdasarkan commit `85d29d0ee001f7674ebd0e9a27612467a70d8ab9`, dengan perubahan hardening dalam paket ini. Perubahan perlu pilot sebelum produksi.

## Dokumentasi

- [Panduan Android](README-ANDROID.md): konfigurasi, metrik, izin, transport, dan build.
- [PRD](docs/PRD.md): kebutuhan produk, acceptance criteria, dan roadmap.
- [Audit](docs/AUDIT.md): temuan, perbaikan, risiko tersisa, dan hasil validasi.
- [Receiver PUSH untuk pengujian](server-test/README.md).

## Fitur yang tersedia

| Komponen | Fungsi yang ada | Batasan |
| --- | --- | --- |
| Linux | Installer `.deb`/`.rpm`, 10 local checks, inventory, cron memtester | Sensor dan paket berbeda antar distro/hardware; instalasi membutuhkan root dan internet |
| Windows | Installer MSI, 10 checks yang dipasang installer, inventory dan plugin lisensi, task RAM | WMI/CIM dan tool sensor bergantung perangkat; task alokasi RAM bukan uji integritas hardware |
| Android | Foreground service, TCP PULL, HTTP(S) PUSH berkala, statistik koneksi, battery/Wi-Fi/RAM/storage, inventory aplikasi | PULL plaintext tanpa Agent Controller/mTLS; PUSH baru ke cache receiver; sensor OEM bisa tidak tersedia |
| Server | Compose untuk server Checkmk dengan volume persistent | Versi image dipilih operator; kompatibilitas kombinasi server/agen harus diuji |

Checkmk upstream menyediakan pemantauan host/service, discovery, status, dan pengolahan perfdata. Grafik metrik kustom tersedia bila check mengeluarkan perfdata valid. Ketersediaan dashboard, notifikasi, inventory tree, dan fitur lain bergantung versi, edisi, serta konfigurasi server; repository ini tidak menambahkan semuanya secara otomatis.

## Local checks desktop

| Kelompok | Linux | Windows yang dipasang installer |
| --- | --- | --- |
| Baterai | `battery_health.sh` | `battery_health.ps1` |
| CPU | `cpu_info.sh` | `cpu_info.ps1` |
| Kesehatan disk | `disk_nvme_health.sh` | `disk_nvme_health.ps1` |
| Kipas | `fan_health.sh` | `fan_health.ps1` |
| Jaringan | `info_network.sh` | `info_network.ps1` |
| OS / Office | `info_OS_office.sh` | `info_OS_office.ps1` |
| RAM / slot | `ram_health.sh` | `ram_health.ps1` |
| Pemakaian RAM | `ram_usage.sh` | `ram_usage.ps1` |
| Aplikasi remote | `remote_apps.sh` | `remote_access_id.ps1` |
| Pemakaian storage | `storage_usage.sh` | `storage_usage.ps1` |

`windows/local_checks/remote_apps.ps1` juga ada, tetapi installer menggunakan `remote_access_id.ps1`. Jangan menyalin keduanya tanpa memeriksa nama service yang dihasilkan. `disk_nvme_health.sh` sebenarnya menggunakan Python 3 sesuai shebang meskipun berekstensi `.sh`. Threshold berada di masing-masing skrip, belum dikelola terpusat. Misalnya Linux battery memakai WARNING ≤40% dan CRITICAL ≤20%; tabel threshold README lama tidak sesuai dengan implementasi tersebut.

Output local check: `<state> "<service>" <perfdata atau -> <pesan>`. State: `0` OK, `1` WARNING, `2` CRITICAL, `3` UNKNOWN. Kesamaan nama service tidak menjamin kesamaan kemampuan sensor Linux dan Windows.

## Struktur

```text
configcmk/
├── README.md
├── README-ANDROID.md
├── docker-compose-checkmk.yml
├── .env.example
├── linux/                 # Installer, local_checks, plugins
├── windows/               # Installer, local_checks, plugins, DLL pendukung
├── android/               # Proyek Android Java
├── server-test/           # Receiver cache untuk uji PUSH
├── docs/                  # PRD dan audit
├── tests/                 # Regresi receiver dan estimasi baterai
└── .github/workflows/     # Validasi sumber dan build APK debug
```

## Menyiapkan server Checkmk

1. Salin `.env.example` menjadi `.env`.
2. Isi `CHECKMK_IMAGE` dengan tag image yang dipilih dan sudah diuji. Contoh lama berasal dari seri 2.3; ini bukan rekomendasi versi terbaru. Gunakan patch tag tetap/digest untuk deployment reproducible.
3. Isi `CMK_PASSWORD` dengan password kuat; jangan commit `.env`.
4. Jalankan:

```bash
docker compose -f docker-compose-checkmk.yml config --quiet
docker compose -f docker-compose-checkmk.yml up -d
```

GUI: `http://SERVER:8080/cmk/`. Port `8000` diteruskan untuk Agent Receiver pada contoh site pertama. Buka port hanya untuk jaringan pengelola/agen yang diperlukan. Gunakan HTTPS/reverse proxy untuk akses produksi. Backup volume `checkmk-data` dan uji restore sebelum upgrade.

Installer desktop masih memiliki default agen `2.5.0p14-1`; default tersebut tidak selaras dengan contoh image lama. Ambil versi/nama paket dari halaman agen site Anda dan masukkan eksplisit. Jangan menganggap semua kombinasi server/agen kompatibel.

## Memasang agen Linux

Lebih mudah meninjau skrip dari checkout sebelum menjalankannya dengan hak root:

```bash
git clone https://github.com/Dodik-Dot/configcmk.git
cd configcmk
bash -n linux/install.sh
sudo bash linux/install.sh --help
sudo bash linux/install.sh -s 'https://checkmk.example.org' -d cmk -v 'VERSI_PAKET_DARI_SITE'
```

`-s` menerima URL HTTP(S) atau host:port. Tanpa scheme, installer tetap memakai HTTP untuk kompatibilitas LAN. Nama paket DEB/RPM dibentuk dari `-v`; pastikan paket tersebut benar-benar tersedia di site. HTTPS membutuhkan sertifikat yang dipercayai perangkat.

Installer memasang dependensi, mengambil local checks/plugin, membuat runner memtester dan cron Sabtu 11:00 menurut timezone host. Ia juga langsung menjalankan sampel memtester pertama di background. Lakukan pada waktu maintenance; memtester memakai memori dan CPU. Local checks milik pihak lain dipertahankan. Penggantian file unduhan dilakukan per file setelah unduhan berhasil; ini belum transaksi rollback seluruh instalasi.

Registrasi agen desktop dilakukan terpisah, setelah host dengan nama yang sama dibuat di Setup:

```bash
sudo cmk-agent-ctl register --hostname NAMA_HOST --server checkmk.example.org:8000 --site cmk --user agent_registration
sudo cmk-agent-ctl status
sudo cmk-agent-ctl dump
```

Port receiver dapat berbeda per site. Validasi identitas sertifikat saat registrasi dan gunakan akun registrasi dengan hak yang sesuai. Opsi `--server HOST:PORT` ini menunjuk receiver, bukan port GUI. Agent Controller desktop tidak digunakan oleh agen Android kustom.

## Memasang agen Windows

Buka PowerShell sebagai Administrator dari checkout yang sudah ditinjau:

```powershell
.\windows\install.ps1 -s 'https://checkmk.example.org' -d cmk -v 'VERSI_AGEN_DARI_SITE'
```

Unduhan MSI mengikuti paket yang disediakan site; `-v` dipakai untuk keputusan upgrade, bukan pemilihan nama MSI. Tanpa scheme dan tanpa port, default GUI Windows installer adalah `8080`. Installer mengunduh skrip ke `C:\ProgramData\checkmk\agent\local` dan plugins ke folder `plugins`.

Registrasi:

```powershell
$ctl = 'C:\Program Files (x86)\checkmk\service\cmk-agent-ctl.exe'
if (-not (Test-Path $ctl)) { $ctl = 'C:\Program Files\checkmk\service\cmk-agent-ctl.exe' }
& $ctl register --hostname NAMA_HOST --server checkmk.example.org:8000 --site cmk --user agent_registration
& $ctl status
& $ctl dump
```

Jangan menonaktifkan validasi sertifikat global. Instalasi sensor tambahan pihak ketiga masih perlu evaluasi checksum/signature, lisensi, dan kompatibilitas; lihat audit. Task RAM hanya mengalokasikan objek .NET, sehingga `Health_RAM` sekarang UNKNOWN untuk hasil yang belum memvalidasi integritas hardware.

## Discovery dan verifikasi

1. Tambahkan host/IP di Checkmk Setup dan pilih sumber agen yang sesuai.
2. Untuk Android PULL gunakan legacy plaintext TCP pada port yang dikonfigurasi, di LAN/VPN terbatas.
3. Jalankan service discovery, terima services, kemudian activate changes.
4. Periksa raw agent output, status service, umur cache, dan perfdata. Konfirmasi inventory tree di versi server yang dipakai; Android memakai section bergaya Linux dan belum terbukti cocok untuk semua parser.

Di server, sebagai site user:

```bash
cmk -d NAMA_HOST
cmk -nv --detect-plugins=local NAMA_HOST
```

Koneksi gagal: periksa IP, port, firewall, izin aplikasi, status service, serta konfigurasi TLS. Metrik N/A: periksa dukungan sensor dan tool vendor. PUSH HTTP 200 hanya membuktikan receiver menerima cache, belum membuktikan Checkmk membacanya.

## Pengembangan dan pengujian

```bash
python3 tests/validate_syntax.py
python3 -m unittest discover -s tests -v
mkdir -p /tmp/cmk-java-tests
javac -d /tmp/cmk-java-tests android/app/src/main/java/com/bcp/checkmkagent/BatteryEstimate.java tests/BatteryEstimateTest.java
java -cp /tmp/cmk-java-tests BatteryEstimateTest
```

Java 17 diperlukan untuk tes Java. GitHub Actions memvalidasi Bash, receiver, estimasi baterai, syntax PowerShell, dan membangun APK debug. Build lokal Android memerlukan Gradle 8.9 dan Android SDK 35; wrapper Gradle belum tersedia. CI yang ditambahkan belum dijalankan di GitHub dalam audit ini.

Tidak ada auto-update klien dari commit GitHub. Update terjadi ketika installer dijalankan lagi. Parameter branch/ref dapat dipakai untuk memilih revisi; rollout pin commit lebih aman daripada mengikuti `main` tanpa review.

## Keamanan, privasi, dan lisensi

PULL Android tidak terenkripsi; isi output dapat mencakup hostname, IP, SSID, daftar aplikasi, serta identitas aplikasi remote desktop. Batasi akses dan retensi sesuai kebutuhan operasional. Receiver di `server-test` hanya untuk lab, bukan layanan publik. Repo belum memiliki LICENSE proyek; kredit tidak menggantikan izin redistribusi. Audit provenance dan lisensi skrip/plugin/DLL sebelum distribusi.

## Referensi resmi

- [Checkmk local checks](https://docs.checkmk.com/latest/en/localchecks.html)
- [Checkmk Linux Agent dan registrasi](https://docs.checkmk.com/latest/en/agent_linux.html)
- [Android BatteryManager](https://developer.android.com/reference/android/os/BatteryManager)
