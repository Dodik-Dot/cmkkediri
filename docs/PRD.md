# PRD — configcmk Unified Device Monitoring

Versi dokumen 1.0 • 9 Oktober 2026 • Status: usulan untuk review pemilik repo.
Sumber baseline: `85d29d0ee001f7674ebd0e9a27612467a70d8ab9`.
Dokumen membedakan kemampuan baseline, perubahan audit lokal, dan kebutuhan yang belum diimplementasikan. Target angka di bawah merupakan usulan, bukan hasil benchmark.

## 1. Masalah dan tujuan

Tim operasional membutuhkan pemantauan konsisten untuk komputer Linux/Windows dan perangkat Android/PDA, agar gangguan kapasitas, konektivitas, dan baterai diketahui sebelum mengganggu pekerjaan. Saat ini deployment memerlukan installer terpisah, beberapa data sensor diestimasi tanpa penandaan yang memadai, dan PUSH Android belum menjadi sumber data Checkmk.

Tujuan produk: menyediakan data yang dapat dipercaya, deployment yang dapat diulang, transport aman, serta diagnostik yang bisa ditindaklanjuti. Prioritas pertama adalah integritas data dan keselamatan update; penghematan CPU, RAM, baterai, dan ukuran paket harus dibuktikan dengan pengukuran.

## 2. Pengguna dan perjalanan utama

| Pengguna | Kebutuhan | Alur |
| --- | --- | --- |
| Admin monitoring | Onboarding host dan discovery services | Pilih versi server/agen → instal → registrasi/config → discovery → aktivasi |
| Teknisi endpoint | Mengetahui penyebab gangguan | Lihat service/status → periksa sumber/umur data → validasi perangkat → tindakan |
| Pengelola armada PDA | Monitoring tanpa mengganggu penggunaan | Konfigurasi hostname/IP unik → pilot → ukur daya → rollout bertahap |
| Developer/maintainer | Update yang aman dan reviewable | Tes → build/sign → release versioned → pilot → update → rollback |

Skenario operasional Android mencakup jaringan gudang/LAN yang dikelola. Dukungan remote internet langsung tidak menjadi default sebelum transport dan autentikasi produksi siap.

## 3. Ruang lingkup dan status

| Kemampuan | Baseline | Paket audit | Target berikutnya |
| --- | --- | --- | --- |
| Desktop local checks | Ada | Dokumentasi diperbaiki, update file lebih aman | Threshold/config terpusat, UNKNOWN konsisten |
| Desktop deployment | Ada, beberapa operasi destruktif | Linux menghindari wipe global, TLS bypass Windows dihapus | Manifest checksum, transaksi update, rollback |
| Android PULL | TCP plaintext, allowlist opsional | Worker/antrean dibatasi | Deadline/rate limit, transport terenkripsi yang disetujui |
| Android PUSH | Periodik ke receiver lab | Redirect dimatikan, receiver timeout/validasi diperkuat | Receiver produksi dan identitas per host |
| Server fallback | Belum ada | Belum ditambahkan | PULL-first/cache-fallback dengan TTL dan status sumber |
| Battery health | Baseline/statis bisa dianggap sehat | Estimasi dilabeli, input hilang UNKNOWN | Validasi OEM, confidence dan sumber hardware |
| Inventory | Section bergaya Linux dengan data statis | Sejumlah field buatan dihapus, TTL maksimum 7 hari | Schema/parser tervalidasi per versi Checkmk |
| Release APK | Key/password tetap di workflow | Tidak upload key, debug bawaan, release signing dilepas | Signing produksi stabil, provenance, version policy |

Di luar lingkup tahap awal: remote-control perangkat, patch OS otomatis, MDM lengkap, diagnosis fisik baterai kembung, dan jaminan semua vendor/distro tanpa pengujian.

## 4. Kebutuhan fungsional

| ID | Prioritas | Kebutuhan | Acceptance criteria |
| --- | --- | --- | --- |
| FR-01 | P0 | Status mencerminkan ketersediaan data | Sensor tidak ada menghasilkan N/A/UNKNOWN; tanpa nilai kapasitas, cycle, suhu atau health buatan |
| FR-02 | P0 | Instalasi menjaga checks lain | Help/argumen invalid tidak mengubah host; gagal unduh tidak menimpa file lama; tidak menghapus checks pihak lain |
| FR-03 | P0 | Distribusi aman | Tidak ada TLS bypass/private key di artifact; binary dan script diverifikasi checksum/signature sebelum eksekusi |
| FR-04 | P0 | Identitas host unik | Hostname tervalidasi, konflik terdeteksi saat provisioning; token receiver hanya berhak menulis host terkait |
| FR-05 | P1 | PULL monitoring Android | Server dapat discovery services; allowlist diterapkan sebelum pengumpulan; stop menutup socket/worker/lock |
| FR-06 | P1 | PUSH produksi | HTTPS, autentikasi per perangkat, batas payload/concurrency, atomic data+metadata, timestamp server, retensi dan audit akses |
| FR-07 | P1 | Fallback Checkmk | PULL berhasil dipakai; PULL gagal memakai cache hanya bila age ≤TTL; cache stale dilaporkan UNKNOWN dan tidak menyamar sebagai live |
| FR-08 | P1 | Cache konsisten | Timestamp/TTL sesuai format local check; perubahan konfigurasi/versi menginvalidasi cache terkait; inventory refresh meski melewatkan hari Minggu |
| FR-09 | P1 | Operator dapat mendiagnosis | UI/raw output menjelaskan nilai, sumber, umur, status listener sebenarnya, last transport outcome; secret tidak muncul |
| FR-10 | P1 | Release upgrade Android | Key produksi stabil, versionCode naik, upgrade pilot menjaga konfigurasi; tersedia rollback yang kompatibel |
| FR-11 | P2 | Konfigurasi threshold/interval | Config per platform/host dengan validasi; default versioned; warning/critical konsisten dengan perfdata |
| FR-12 | P2 | Inventory terverifikasi | Data fisik tidak dikarang; parser tree diuji dengan fixture pada versi server yang didukung; package inventory opt-in bila tidak diperlukan |

P0 adalah kebutuhan kritis sebelum produksi; bukan klaim seluruh P0 selesai dalam paket ini.

## 5. Desain fallback server yang diusulkan

Data source program menerima hostname dan target PULL dari konfigurasi terpercaya, bukan shell command dari input perangkat. Ia melakukan PULL dengan timeout/batas byte, memvalidasi payload, dan mengembalikan data live jika berhasil. Saat PULL gagal, ia membaca cache host yang identitasnya sudah diotorisasi dan memeriksa `received_at` server.

TTL awal usulan: tiga interval PUSH, maksimum 15 menit; harus bisa dikonfigurasi. Data cache menambahkan service sumber/age yang jelas. Cache di luar TTL tidak menghasilkan ulang data lama sebagai sehat. Jalur live dan cache tidak di-merge sehingga tidak menggandakan services. Receiver produksi dan adapter server ini belum ada; kompatibilitas edisi Checkmk menjadi keputusan desain sebelum implementasi.

## 6. Kebutuhan nonfungsional dan target pengukuran

| ID | Target usulan | Metode verifikasi |
| --- | --- | --- |
| NFR-01 | Android output warm-cache p95 <2 detik pada pilot | 100 request/perangkat, pisahkan cold inventory dan warm output |
| NFR-02 | Tidak ada thread/socket yang terus tumbuh | Flood terkontrol, repeated start/stop, pantau heap/threads/file descriptors |
| NFR-03 | Tambahan drain baterai ≤3 poin persentase/24 jam | Bandingkan workload, konektivitas, brightness dan battery age yang sama; minimal 3 pasangan uji |
| NFR-04 | Tambahan RAM RSS ≤50 MiB steady-state | Ukur sebelum/sesudah inventory dan sesudah soak 24 jam |
| NFR-05 | Installer bisa dijalankan ulang tanpa kehilangan konfigurasi lain | VM clean/existing, failure injection tiap fase, rollback drill |
| NFR-06 | Tidak ada secret dalam git/artifact/output/log | Secret scanning, daftar artifact, fixture URL/token sensitif |
| NFR-07 | Ukuran APK tidak naik >10% tanpa alasan | Bandingkan APK release yang signed, track dependency dan resource size |

Belum ada baseline perf/baterai/ukuran APK yang terukur. R8/resource shrinking dievaluasi setelah fixture inventory dan akses reflection diuji; jangan mengaktifkan optimasi yang mematahkan pembacaan vendor secara diam-diam.

## 7. Rencana verifikasi

- Portable: receiver auth/payload/path/write, rumus baterai input hilang/invalid/low SOC/MT93, parse Bash dan PowerShell.
- Build: APK debug, lint, kemudian release signed di CI; dependency/toolchain pin dan signing migration.
- Desktop: pilot Debian/Ubuntu dan satu distro RPM, Windows 10/11; installer HTTPS, upgrade, sensor hilang, permission denied.
- Android: MT93 dengan Android versi armada dan satu perangkat generik; API 26/33/34/35/36 sesuai ketersediaan, izin ditolak, screen-off, boot, roaming, force-stop, battery replacement.
- Checkmk: versi server yang dipilih operator; discovery, cached local checks, perfdata, inventory tree, alert routing.
- Fallback: PULL sukses, timeout, cache fresh, stale, host mismatch, disk full, clock skew dan receiver unavailable.

Gate release: seluruh P0 terkait deployment lulus, CI hijau, pilot 24 jam memenuhi target yang disepakati, restore/rollback berhasil. Saat ini hanya tes portable tertentu selesai; lihat audit.

## 8. Roadmap dan dependensi

| Tahap | Hasil | Dependensi |
| --- | --- | --- |
| A — Akurasi dan hardening dasar | Paket audit, README/PRD, regresi | Review perubahan, full build APK, uji VM/perangkat |
| B — Deployment produksi | Checksums/signatures, update transaction, signing APK, version compatibility | Pilihan versi Checkmk dan asal binary/tool vendor |
| C — Hybrid end-to-end | Receiver produksi, adapter fallback, TTL/source service | Model identitas host/token dan edisi server |
| D — Efisiensi terukur | Lock policy, collector cache, background UI, intervals | Baseline workload dan eksperimen power/network |
| E — Operasional armada | Provisioning massal, config migration, inventory consent, observability | Jumlah host, distribusi APK, aturan retensi |

## 9. Risiko dan keputusan pemilik

Belum diketahui: jumlah host/PDA, versi Android MT93, versi/edisi Checkmk produksi, topologi VPN/LAN, metode distribusi APK, kepemilikan key lama, dan kebutuhan penyimpanan inventory. Asumsi awal: jaringan internal dan operator berwenang mengelola endpoint.

Risiko utama: data estimasi menimbulkan false alert, target SDK migration memengaruhi service, wake lock menghabiskan baterai, key berbeda memblokir upgrade, receiver token global memungkinkan spoofing host, dan script/binary pihak ketiga memiliki lisensi/provenance belum jelas. Setiap risiko harus punya uji dan pemilik sebelum rollout.
