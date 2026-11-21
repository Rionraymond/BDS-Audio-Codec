# BDS Studio 7.0 — Android Studio Project

Starter project Android Studio untuk pengembangan BDS Studio. Antarmuka dibuat dengan Kotlin (Android SDK native), sedangkan primitive DSP/codec eksperimental berada di C++20 dan dipanggil melalui JNI.

## Yang sudah ada di build ini

- Proyek Android Gradle dengan Kotlin, CMake, Android NDK, dan native library C++20.
- Tab Beranda, Koleksi, Repo, dan Telusuri.
- Pemilih file audio dari penyimpanan Android melalui Storage Access Framework.
- Playlist lokal yang dapat dibuat pengguna, disimpan di perangkat, dan diisi dengan menahan sebuah lagu.
- Pemutar lokal dasar memakai `MediaPlayer`: play/pause, previous/next, seek, volume aplikasi, metadata dasar, artwork, dan mini-player.
- Tampilan Now Playing dengan format/MIME yang tersedia dari sumber file.
- Pemilih file `.lrc`, parsing timestamp LRC (termasuk beberapa timestamp pada satu baris), highlight, serta auto-scroll lirik.
- Pembacaan embedded lyrics umum dari ID3v2 `USLT` (MP3) dan FLAC Vorbis comments `LYRICS` / `UNSYNCEDLYRICS`.
- Kustomisasi tema Midnight, Monochrome, Light; warna aksen; font judul (HYWenHei 85W, Serif, Sans-serif); dan artwork (Original, Grayscale, Soft blur background).
- Font `HYWenHei 85W Heavy` dari file font yang diberikan pengguna, berada di `app/src/main/assets/fonts/hywenhei-85w.ttf`.
- Native self-test untuk seluruh 243 nilai Radix-3 lima-simbol, penolakan byte reserved 243–255, dan smoke test finite-state quantizer eksperimental.

## Batas kemampuan yang harus diketahui

Build ini **belum merupakan codec BDS lengkap**. Yang sudah diimplementasikan di native core adalah primitive packing/unpacking Radix-3 serta quantizer error-feedback eksperimental dan diagnostiknya. Yang belum tersedia:

- Container `.bds` final beserta header/versioning/metadata/CRC.
- Encoder WAV stereo PCM16/24 → BDS.
- Decoder BDS → PCM dan integrasi hasil decode ke pemutar.
- Pipeline interpolasi OSR 16×, rekonstruksi FIR dan decimation yang tervalidasi end-to-end.
- Analisis kualitas lengkap seperti sweep 20 Hz–20 kHz, passband ripple, alias rejection, THD+N, dan noise spectrum.
- Pembacaan embedded lyrics untuk semua container (saat ini ID3v2 USLT dan FLAC Vorbis comments).
- Background playback service/notification media controls.

Parameter 48 kHz dan OSR 16× dicantumkan sebagai konfigurasi target proyek, bukan klaim bahwa seluruh pemrosesan audio 16× sudah aktif di player.

## Kebutuhan build

Disarankan Android Studio versi yang mendukung Android Gradle Plugin 8.7.x, dengan komponen berikut terpasang melalui SDK Manager:

- Android SDK Platform 35 (compile SDK).
- Android SDK Build-Tools yang sesuai.
- Android NDK side-by-side `27.2.12479018`.
- CMake `3.22.1`.
- JDK 17 atau lebih baru yang kompatibel dengan Gradle 8.9 (Embedded JDK Android Studio biasanya dapat digunakan).

Gradle project menggunakan Gradle 8.9 dan Android Gradle Plugin 8.7.3. Script `gradlew` / `gradlew.bat` di paket ini adalah bootstrap sederhana yang mengunduh distribusi Gradle resmi 8.9 pada pemakaian pertama. Koneksi internet diperlukan saat pertama kali mengunduh Gradle dan plugin/dependensi Android.

## Cara membuka dan build di Android Studio

1. Ekstrak ZIP ke folder yang mudah ditemukan, misalnya `D:\\Projects\\BDS_Studio_7_0_Android`.
2. Jalankan Android Studio → **Open** → pilih folder `BDS_Studio_7_0_Android` (folder yang berisi `settings.gradle.kts`, bukan folder `app`).
3. Saat diminta, izinkan Gradle Sync. Jika komponen SDK/NDK/CMake belum ada, buka **Tools → SDK Manager → SDK Tools** lalu pasang NDK `27.2.12479018` dan CMake `3.22.1`. Pada tab SDK Platforms pasang Android API 35.
4. Pastikan **Settings → Build, Execution, Deployment → Build Tools → Gradle → Gradle JDK** memakai Embedded JDK 17+.
5. Tunggu Gradle Sync selesai.
6. Untuk compile aplikasi: **Build → Make Project**.
7. Untuk membuat APK debug: **Build → Build Bundle(s) / APK(s) → Build APK(s)**.
8. APK debug biasanya berada di `app/build/outputs/apk/debug/app-debug.apk`.

## Menjalankan di HP Android

- Aktifkan Developer options dan USB debugging pada HP, hubungkan ke laptop, lalu izinkan debugging dari komputer.
- Pilih perangkat HP pada daftar device Android Studio.
- Tekan tombol **Run ▶**.
- Di aplikasi, buka Koleksi → Tambah, lalu pilih file audio. Pemilihan file memakai Android Storage Access Framework; aplikasi tidak meminta akses menyeluruh ke seluruh penyimpanan.

## Menjalankan native self-test

Di aplikasi buka **Beranda → Buka Audio Lab → Jalankan Native Self-Test**.

Hasil yang diharapkan:

```text
Radix-3 exhaustive round-trip: PASS
Reserved byte rejection (243-255): PASS
Experimental quantizer finite-state smoke test: PASS
```

Tes ini memverifikasi primitive native, bukan kualitas audio end-to-end. Untuk tahap berikutnya, pipeline DSP perlu divalidasi dengan sweep frekuensi, pengukuran delay, gain/ripple, THD+N dan noise spectrum sebelum encoder/decoder container dibuat.

## Struktur penting

```text
BDS_Studio_7_0_Android/
├── app/
│   ├── src/main/
│   │   ├── java/com/bds/studio/
│   │   │   ├── MainActivity.kt
│   │   │   ├── NativeBds.kt
│   │   │   └── LyricsRepository.kt
│   │   ├── cpp/
│   │   │   ├── CMakeLists.txt
│   │   │   ├── bds_core.hpp
│   │   │   ├── bds_core.cpp
│   │   │   └── bds_jni.cpp
│   │   └── assets/fonts/hywenhei-85w.ttf
│   └── build.gradle.kts
├── gradle/wrapper/gradle-wrapper.properties
├── settings.gradle.kts
└── build.gradle.kts
```

## Catatan font

File font dimasukkan sebagai aset lokal proyek sesuai file yang diberikan. Sebelum mendistribusikan APK secara publik/komersial, pastikan lisensi font mengizinkan redistribusi di dalam aplikasi.
