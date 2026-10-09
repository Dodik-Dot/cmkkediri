# Audit configcmk dan catatan perubahan

Tanggal: 9 Oktober 2026. Baseline: `85d29d0ee001f7674ebd0e9a27612467a70d8ab9` — `Improve DeviceMetrics with detailed system info`.
Audit mencakup pembacaan sumber dan tes portable; tidak mengeksekusi installer berhak root pada host produksi, tidak memindai perangkat pengguna, dan tidak melakukan benchmark armada.

## Temuan prioritas

| Prioritas | Bukti baseline | Dampak | Status paket ini |
| --- | --- | --- | --- |
| P0 | `linux/install.sh` menghapus `local/*` dan cache sebelum parse args | Help/typo/gagal unduh dapat menghilangkan checks lain | Wipe global dihapus; unduhan checks/plugin staged per file |
| P0 | `android/app/build.gradle` key/password `android`; workflow upload keystore | Bila key dapat diakses orang lain, signing identity dapat disalahgunakan; key baru tiap runner mematahkan upgrade | Custom key dilepas dari build; artifact APK saja; release signing tetap perlu disiapkan |
| P0 | Windows memakai `curl -k` dan global callback sertifikat true | Mengabaikan trust HTTPS | Bypass dihapus; URL HTTPS eksplisit didukung |
| P0 | `DeviceMetrics.java` baseline MT93 2946 mAh, fallback capacity/health 100% | Sensor tidak tersedia atau degradasi dapat terlihat sehat | Baseline buatan dihapus; estimator terpisah; UNKNOWN bila input hilang |
| P1 | Cycle dibaca `getIntProperty(7)` | Bukan API cycle count resmi; data tidak dapat dipercaya | API 34+ memakai `EXTRA_CYCLE_COUNT`; sysfs fallback; estimasi history tidak dipakai |
| P1 | Inventory menulis LPDDR4/1866, CPU 2000 MHz/1024 KB, flags statis, board sebagai serial | Inventory terlihat faktual padahal asumsi | Field tersebut dan disk fisik dari kapasitas filesystem dihapus; parser/field asumsi lain belum diuji |
| P1 | Local cache Android berada pada repeated section header | Menyimpang dari format local check cache yang didokumentasikan | Diubah menjadi prefix per baris; perlu integrasi server |
| P1 | `newCachedThreadPool()` listener Android | Koneksi dapat memicu pertumbuhan thread | 2 worker, queue 8, rejected socket ditutup; write deadline/rate limit belum ada |
| P1 | Inventory hanya refresh saat ada request hari Minggu | Dapat stale tanpa batas bila Minggu terlewat | TTL maksimum 7 hari dan clock rollback check |
| P1 | Windows alokasi 256 MiB dianggap RAM test passed; Linux missing log juga passed | False assurance integritas hardware | Windows hasil nonvalidated UNKNOWN; Linux missing/incomplete log UNKNOWN |
| P1 | `server-test` tidak terhubung ke Checkmk | PUSH success tidak berarti failover berjalan | Dijelaskan dalam README/PRD; adapter belum dibuat |
| P2 | README Android 1.3.3, workflow 1.3.4, sumber 1.3.5 | Sulit menentukan build | Sumber audit 1.3.6, artifact netral debug, README ditulis ulang |
| P2 | File `gitignore` tanpa titik | Git tidak memakai ignore rules | Diperbaiki ke `.gitignore`, tambah build/key/cache ignores |
| P2 | Compose image seri 2.3, installer default agen seri 2.5, README menyebut server 2.5 | Dokumentasi deployment tidak konsisten | Image/password wajib dari env; versi/operator harus diuji |

## Perubahan tambahan

- Linux membuat direktori temporary privat, berhenti pada kegagalan command utama dengan `set -e`/pipefail, dan tidak menghapus persisted inventory/cache pihak lain.
- Windows mempertahankan file check/plugin lama ketika download gagal dan membuat kegagalan exit code MSI fatal. URL eksplisit mendukung HTTPS; parsing hostname memakai Uri.
- Receiver memakai per-connection timeout, constant-time token comparison, dan menolak body terpotong. Ini tetap receiver lab dengan thread per koneksi, token opsional/global, metadata write belum atomik bersama payload, dan tanpa rate limit.
- PUSH Android tidak mengikuti redirect; output menyembunyikan URL receiver. Status transport kini dihasilkan tiap request. Pesan receiver/SSID dan field lain masih perlu sanitasi penuh agar newline tidak masuk ke agent output.
- Build APK berjalan juga pada pull request. Workflow validasi baru menambahkan tes portable dan parse PowerShell. CI belum dieksekusi pada GitHub dalam sesi ini.

## Kekurangan yang masih terbuka

1. **Supply chain:** script GitHub mengikuti mutable `main`; download MSI/DEB/RPM/tool belum punya manifest checksum/signature. Windows fallback HWiNFO menunjuk `windows/tools/hwi_804.zip` yang tidak ada pada baseline. HDSentinel dan tool tambahan harus diperiksa lisensi/provenance; `.dll` tidak boleh dibuang sebelum penggunaan/provenance diaudit.
2. **Atomic rollout:** staging per file bukan transaksi seluruh install. Kegagalan parsial dapat menghasilkan versi campuran. Script Linux memtester langsung berjalan saat install, memakai minimum 128 MiB, belum punya lock/timeout/resource policy; cron bergantung layanan tersedia.
3. **Transport:** PULL Android bind seluruh IPv4, allowlist kosong menerima semua, tanpa enkripsi. HTTP/token kosong masih diizinkan. Worker terbatas mencegah unbounded growth tetapi slow writer dapat menghabiskan kapasitas worker. Race lifecycle/start-stop perlu perangkat test.
4. **Power:** wake lock dan Wi-Fi high-performance lock aktif terus. UI melakukan pembacaan sensor/inventory di main thread. Belum ada benchmark CPU/RAM/baterai, sehingga tidak ada klaim persen percepatan/penghematan.
5. **Data correctness:** beberapa local checks desktop/default sensor masih fallback 100%/OK; threshold tidak seragam; pembaca RAM Linux belum sepenuhnya mengevaluasi freshness hasil test. Inventory Android masih punya asumsi struktur dan butuh parser integration test. BatteryManager charge counter/SOC bukan SOH laboratorium.
6. **Version/cache:** Namespace cache metrik dinaikkan untuk menghindari output versi lama setelah upgrade ini. Migration cache/config berikutnya masih perlu kebijakan versioned. Tombol scan UI belum menginvalidasi cache payload inventory.
7. **Release:** Gradle wrapper belum ada; build-tools compatibility AGP/compileSdk perlu lint/build. APK debug bukan distribusi produksi; keystore baru tidak bisa update APK dengan signing lama.
8. **Operations:** LICENSE proyek, dependency provenance, secret scanning, rollback guide teruji, receiver production adapter dan aturan retensi inventory belum tersedia.

## Hasil validasi

| Pemeriksaan | Hasil |
| --- | --- |
| Receiver Python | 4 tes lulus: authenticated write/replacement, bad token, validation/path, safe hostname |
| Estimasi baterai Java 17 | 7 kasus lulus: missing sensor/design, SOC nol/rendah, MT93 tidak forced 100%, estimasi parsial, input tidak masuk akal |
| Syntax Linux | 12 file lulus validasi sesuai shebang: Bash parse atau Python AST; disk check berekstensi `.sh` memakai Python |
| `--help`/argumen Linux tidak valid | Diperiksa memakai direktori host sementara; tidak mengubah checks/cache |
| Atomic download Linux | Transfer gagal menjaga file lama; transfer sukses mengganti file, dibuktikan harness isolated |
| XML/Gradle/YAML source inspection | Manifest parsed; Compose dan workflow YAML parsed; konsistensi versi diperiksa |
| Diff whitespace | `git diff --check` lulus |
| Full Android APK/lint | Belum dijalankan: Gradle dan Android SDK tidak tersedia di lingkungan ini |
| Windows runtime / parse lokal | Belum dijalankan: PowerShell tidak tersedia; workflow Windows disiapkan |
| Checkmk discovery/inventory/mTLS | Belum dijalankan: tidak ada server lab yang dikonfigurasi |
| Benchmark hardware/soak/upgrade signing | Belum dijalankan; wajib pilot |

Tidak ada perubahan yang di-push ke GitHub. Paket ini adalah kandidat perubahan untuk ditinjau dan diuji, bukan pernyataan siap produksi.

## Referensi verifikasi

- [Android BatteryManager — EXTRA_CYCLE_COUNT](https://developer.android.com/reference/android/os/BatteryManager#EXTRA_CYCLE_COUNT)
- [Checkmk local checks — cache per baris](https://docs.checkmk.com/latest/en/localchecks.html)
- [Checkmk Linux Agent — port/registrasi](https://docs.checkmk.com/latest/en/agent_linux.html)
