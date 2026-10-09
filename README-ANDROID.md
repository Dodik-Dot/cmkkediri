# cmkagent Android — Panduan operator dan developer

Agen Android Java native untuk mengeluarkan data berformat Checkmk. Package `com.bcp.checkmkagent`; versi sumber dalam revisi audit ini `1.3.6` (`versionCode 10`), belum rilis produksi terverifikasi. Baseline repo memakai `1.3.5`, walaupun README lama menyebut `1.3.3` dan artifact workflow menyebut `1.3.4`.

Minimum Android 8/API 26, compile SDK 35, target SDK 33, Java 17, Gradle 8.9, Android Gradle Plugin 8.5.2. Target SDK lama tidak menjamin kompatibilitas Android 14–16. Perubahan target harus disertai uji boot, foreground service, izin, dan kebijakan distribusi.

## Transport dan batas fitur

| Jalur | Implementasi | Batas |
| --- | --- | --- |
| PULL | Listener TCP `0.0.0.0:6556`, port dapat diubah; Checkmk membaca output saat koneksi | Plaintext, tanpa mTLS, allowlist IP opsional; default kosong menerima semua IP |
| PUSH | POST berkala ke URL receiver, Bearer token opsional; interval 60–86400 detik, default 300 | Receiver lab menyimpan `.agent` dan `.json`; belum terhubung ke Checkmk |
| Hybrid | PULL berjalan bersamaan dengan PUSH terjadwal | PUSH bukan failover otomatis; pemilihan sumber harus dibangun di server |

PUSH berlangsung walau PULL berhasil, sehingga berfungsi sebagai warm cache. Scheduler pertama berjalan sekitar 8 detik setelah service mulai, kemudian fixed delay. HTTP/HTTPS didukung untuk lab/kompatibilitas; produksi sebaiknya HTTPS dengan trust sertifikat normal. Redirect POST dimatikan dalam revisi ini.

## Memulai

1. Build/install APK debug untuk pilot atau APK release yang ditandatangani secara aman untuk armada produksi.
2. Isi hostname **unik** dan sama dengan nama host di Checkmk. Default berbasis model dapat sama pada banyak perangkat.
3. Isi `Allowed Checkmk Server IP` dengan IP server. Kosong atau `*` menerima semua sumber dan harus dibatasi firewall/VPN.
4. Pilih port PULL, default 6556. Pastikan server bisa menjangkau IP perangkat.
5. Isi design capacity hanya dari spesifikasi baterai yang terverifikasi. Nilai 0 mencoba Android power profile; jika tidak tersedia, estimasi kesehatan UNKNOWN.
6. Berikan izin lokasi/Wi-Fi/notifikasi sesuai OS. SSID/RSSI bergantung izin dan layanan lokasi perangkat.
7. Tekan **SAVE & START AGENT**; periksa notifikasi foreground dan **AGENT OUTPUT**.
8. Jika PUSH diperlukan, isi URL/token receiver dan tekan **TEST PUSH NOW**.
9. Konfigurasi host Android di Checkmk untuk PULL plaintext/legacy TCP dengan port yang sama; discovery dan activate changes.

Contoh receiver lab tersedia di [server-test](server-test/README.md). Endpoint kustom `/api/v1/agent` tidak sama dengan Agent Receiver resmi port 8000. Jangan mengirim output aplikasi ini langsung ke port tersebut dan mengharapkan registrasi Agent Controller.

## Metrik dan cache

| Service | Data | Refresh |
| --- | --- | --- |
| `Agent_Status` | Version, koneksi diterima/ditolak, last client, allowlist | Tiap output |
| `Battery_Level` | SOC dan status charging | Tiap output |
| `Health_Battery` | Estimasi kapasitas penuh/health, cycles hardware bila tersedia | Tiap output |
| `Battery_Voltage`, `Battery_Current` | Tegangan dan arus BatteryManager | Tiap output |
| `WiFi_Status` | SSID, RSSI, link speed, frekuensi, IP | Tiap output |
| `Android_Info` | Manufacturer/model, SDK/OS, uptime | Tiap output |
| `RAM_Usage` | Total/free/used | 30 menit |
| `Storage_Usage` | Kapasitas filesystem data internal | 24 jam |
| `Battery_Temperature` | Suhu baterai | 30 menit |
| `Transport_Status` | Status PUSH terakhir dan counters | Tiap output |
| Inventory | Sistem, kapasitas RAM, CPU model, OS/kernel, packages | Scan pertama, hari Minggu saat ada request, atau maksimal umur 7 hari |

Cache baru menggunakan prefix `cached(timestamp,ttl)` pada **baris** local check. Jadwal inventory mengikuti waktu lokal perangkat dan bukan background job tersendiri. Tombol scan UI memperbarui tampilan; belum ada invalidasi eksplisit cache output inventory dari tombol tersebut.

Threshold Android saat ini:

| Metrik | WARNING | CRITICAL |
| --- | --- | --- |
| SOC | <30% | <15% |
| Estimasi health | <80% atau cycles ≥500 | <65% atau cycles ≥800 |
| Suhu baterai | ≥42°C | ≥48°C |
| RAM/storage | ≥85% | ≥95% |
| RSSI | ≤−68 dBm | ≤−75 dBm |

Jika input health tidak tersedia, service menjadi UNKNOWN. Beberapa sensor lain masih N/A dengan state OK; standardisasi UNKNOWN lintas metrik masih backlog. Cache suhu 30 menit tidak cocok untuk deteksi overheat cepat; ubah kebijakan interval setelah uji overhead.

## Arti estimasi baterai

Rumus: `full capacity ≈ charge counter (mAh) / (SOC / 100)`; `estimated health ≈ full capacity / verified design capacity × 100`.

Rumus ini adalah estimasi fuel gauge, bukan pengukuran laboratorium SOH. Perubahan SOC, kalibrasi OEM, dan battery replacement dapat memengaruhi hasil. Input harus finite/positif, SOC 15–100%, dan hasil >120% ditolak. Kapasitas default generik 5000 mAh, baseline MT93 2946 mAh, serta fallback 100% sehat telah dihapus. Tidak ada deteksi baterai kembung dari rumus ini.

Cycle count dibaca dari `BatteryManager.EXTRA_CYCLE_COUNT` pada API 34+ atau node sysfs yang dapat diakses. Data yang tidak didukung ditampilkan N/A; estimasi cycles sejak aplikasi dipasang tidak disamakan dengan cycles lifetime hardware. File `BatteryHistory.java` lama tetap ada tetapi tidak dipakai sebagai sumber health/cycles dalam jalur pengumpulan baru.

Inventory menghapus angka CPU clock/cache/flags dan jenis/kecepatan RAM yang sebelumnya diisi statis. Kapasitas filesystem tidak lagi disajikan sebagai disk fisik palsu. Beberapa metadata struktur inventory masih asumsi representasi; kompatibilitas tree Checkmk wajib diuji.

## Build

### GitHub Actions

Workflow **Build cmkagent APK** menjalankan assembleDebug dan mengunggah artifact `cmkagent-debug`. Artifact berisi APK saja; keystore tidak diunggah. Build debug memakai signing debug bawaan Android, yang tidak menjamin identitas signing stabil antar runner.

### Lokal

```bash
cd android
gradle --no-daemon :app:assembleDebug
```

APK: `app/build/outputs/apk/debug/app-debug.apk`. Release belum dikonfigurasi dengan signing produksi; jangan distribusikan hasil unsigned sebagai paket upgrade. Gunakan keystore khusus yang disimpan di secret manager/CI secrets dan konfigurasi signing pada tahap release. Jangan commit atau membagikan private key.

Jika aplikasi lama ditandatangani key berbeda, upgrade APK akan ditolak. Jangan uninstall massal sebelum menyimpan konfigurasi yang diperlukan; uninstall menghapus data aplikasi. Bila keystore lama pernah dapat diakses pihak lain, evaluasi penggantian key/package dan rencana migrasi terpisah.

## Performa, keamanan, dan pengujian perangkat

Revisi ini membatasi worker PULL menjadi 2 dengan antrean 8 dan menutup koneksi aktif saat service dihentikan. Ini membatasi pertumbuhan thread, tetapi timeout baca socket tidak membatasi write yang macet; deadline write dan rate limit masih backlog.

Service masih memegang wake lock dan Wi-Fi high-performance lock sepanjang aktif. Uji konsumsi daya 24 jam terhadap baseline tanpa agen sebelum rollout. Jangan mengklaim low-power tanpa pengukuran. Validasi juga Wi-Fi roaming, screen-off, reboot, force-stop, network unavailable, battery replacement, serta start/stop berulang.

Token PUSH tersimpan dalam private SharedPreferences; perlindungan Keystore/token rotation belum diimplementasikan. Daftar aplikasi memakai izin `QUERY_ALL_PACKAGES`; evaluasi kebutuhan inventory dan kebijakan distribusi yang dipilih.

Tes portable: lihat [README utama](README.md). Di lingkungan audit, rumus estimasi dan receiver telah diuji; full Android APK build dan integrasi perangkat/server belum dijalankan.

Referensi: [BatteryManager](https://developer.android.com/reference/android/os/BatteryManager), [local checks Checkmk](https://docs.checkmk.com/latest/en/localchecks.html).
