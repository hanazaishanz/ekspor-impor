# Website startup ekspor briket

Implementasi `wireframe-briket-navy.jpeg` memakai HTML5, CSS3, dan JavaScript murni sesuai `brief.md`. Tidak memerlukan Node.js, build, database, PHP, atau instalasi dependensi untuk menjalankan website.

## Menjalankan di XAMPP

1. Salin `index.html`, folder `css`, `js`, dan `assets` ke satu folder di dalam direktori `htdocs` XAMPP, misalnya `htdocs/briket`.
2. Jalankan Apache dari XAMPP Control Panel.
3. Buka `http://localhost/briket/`.

Website juga dapat disajikan dengan server statis atau ekstensi Live Server. Semua jalur aset relatif, sehingga website dapat dipasang pada domain utama maupun subfolder.

Foto produk dan kontainer adalah aset ilustratif yang dibuat dengan **imagegen**, lalu diekspor sebagai WebP responsif. [Prompt pembuatan gambar](preview/asset-sources/generation-prompts.md) dan [daftar aset beserta ukurannya](preview/asset-report.json) tersedia untuk peninjauan; file pengembangan tersebut tidak disertakan di arsip hosting.

## Konfigurasi sebelum digunakan klien

Ubah **`js/config.js`**:

- `name`: nama perusahaan, otomatis dipakai pada header, profil, footer, dan judul halaman.
- `whatsappNumber`: nomor WhatsApp aktif dalam format internasional, hanya angka, tanpa `+` atau awalan `0`. Nomor ini digunakan bersama oleh form dan tombol WhatsApp melayang.
- `email`, `phone`, `address`, `hours`: informasi kontak yang sebenarnya.
- `social`: URL HTTPS akun LinkedIn, Instagram, dan YouTube. Ikon tanpa URL tetap berupa placeholder noninteraktif.

Nomor WhatsApp **sengaja kosong**, karena nomor perusahaan belum diberikan. Form menampilkan pemberitahuan jika nomor belum dikonfigurasi, dan tidak mengarahkan pengunjung ke nomor contoh. Setelah nomor valid diisi, form membuka `wa.me` dengan pesan yang sudah dirangkai dan di-encode. Pengunjung tetap menekan **Send** sendiri di WhatsApp.

Ganti foto ilustratif, contoh format briket, keterangan produk, logo, serta teks visi/misi dengan informasi perusahaan yang sudah dikonfirmasi. Tidak ada sertifikasi, statistik pencapaian, testimonial, lokasi kantor, atau klaim kepemilikan fasilitas yang dibuat-buat. Peta masih berupa placeholder. Setelah domain tersedia, ubah `og:image` pada `index.html` menjadi URL absolut gambar pada domain tersebut; tambahkan canonical URL sesuai alamat final.

## Fitur dan animasi

- Navigasi sticky dengan indikator kemajuan scroll, menu aktif, smooth scroll, dan hamburger mobile yang mendukung Escape serta keyboard.
- Slideshow hero: tiga visual, crossfade, zoom Ken Burns perlahan, pilihan slide, dan tombol jeda.
- Autoplay berhenti ketika slideshow tidak terlihat, tab tidak aktif, pointer berada di atasnya, atau fokus keyboard masuk ke kontrol.
- Reveal kiri/kanan/atas dan zoom ringan pada elemen yang pertama kali masuk viewport; urutan tampil dibuat bertahap.
- Hover foto produk, ikon, tombol, dan tautan; gerakan dibatasi agar tetap cocok untuk company profile minimalis.
- `prefers-reduced-motion` menonaktifkan autoplay, zoom, smooth scroll, dan reveal tersembunyi. Konten tetap terbaca tanpa JavaScript.
- Inquiry produk dan layanan mengisi field terkait tanpa menghapus catatan pengunjung.
- Validasi lima field wajib, pesan error per field, fokus pada error pertama, dan tautan WhatsApp cadangan jika popup tidak terbuka.
- Tidak ada localStorage, sessionStorage, cookie, analytics, atau penyimpanan submission.

Pola gerakan dipelajari dari [Cartenz Cocoa](https://cartenzcocoa.com/), lalu dibuat ulang dengan CSS dan JavaScript murni. Tidak menggunakan WordPress, Elementor, jQuery, Swiper, atau pustaka animasi situs referensi.

## Struktur

```text
index.html
css/style.css
js/config.js
js/script.js
assets/images/     # WebP responsif yang digunakan halaman
assets/fonts/      # Inter dan Manrope lokal beserta lisensi SIL OFL
assets/icons/      # Favicon SVG; ikon antarmuka ada pada sprite di HTML
tests/             # Audit pengembangan; bukan kebutuhan hosting
preview/           # Wireframe, riset, laporan, dan screenshot pengujian
```

## Pengujian pengembangan

Dengan Python 3 dan Chrome atau Edge terpasang, jalankan:

```text
python tests/browser_audit.py
```

Script hanya membutuhkan standard library Python. Pengujian memakai server sementara dan Chrome/Edge headless, lalu menutupnya. Panggilan WhatsApp ditangkap di browser pengujian, sehingga tidak ada pesan atau popup WhatsApp nyata.

Audit meliputi viewport 320, 375, 430, 768, 1024, 1366, dan 1440 px; overflow horizontal; gambar; form; menu mobile; encoding WhatsApp; prefill produk; slideshow; reduced motion; serta fallback tanpa JavaScript. Hasil aktual disimpan di `preview/audit-report.json`. Screenshot desktop dan mobile disimpan di folder `preview`.

Hasil audit terakhir: **34/34 pemeriksaan lulus di Chrome headless**, termasuk seluruh tujuh viewport tersebut. Pemeriksaan statis juga memastikan ID unik, target tautan lokal tersedia, sepuluh field berlabel, dan seluruh gambar memiliki alt text. Pengiriman pesan sungguhan belum diuji karena nomor WhatsApp perusahaan belum diberikan.

## Upload ke cPanel

Gunakan arsip `briquette-website.zip` jika tersedia, atau upload `index.html`, `css`, `js`, dan `assets` ke `public_html` / subfolder yang dituju. Arsip deployment hanya berisi file website dan lisensi aset; tidak menyertakan `preview`, file riset, atau script pengujian. Tidak ada proses build atau server Node yang perlu dijalankan.
