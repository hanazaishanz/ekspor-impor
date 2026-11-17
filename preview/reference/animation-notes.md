# Kajian animasi Cartenz Cocoa

Sumber: https://cartenzcocoa.com/ dan stylesheet Elementor halaman utama. HTML dan CSS sumber di folder ini digunakan untuk pemeriksaan lokal; tidak dimasukkan ke paket deployment.

## Pola yang dikonfirmasi dari sumber halaman

- Header diatur sticky pada desktop, tablet, dan mobile.
- Hero menggunakan background slideshow dengan transisi fade 1.000 ms, durasi slide 5.000 ms, loop, dan zoom Ken Burns ke dalam.
- Elemen memakai `slideInLeft`, `slideInRight`, `slideInUp`, dan `zoomIn`.
- Terdapat entrance delay 100/300/500 ms serta 600/900 ms pada elemen hero.
- Kartu dan tombol menggunakan transisi hover sekitar 0,3–0,4 detik; galeri memakai overlay fade-in sekitar 800 ms.

## Adaptasi untuk wireframe navy briket

- Susunan dan palet wireframe dipertahankan; konten hero menonjolkan produk briket.
- Slideshow produk memakai crossfade 1,1 detik, interval 6 detik, serta zoom yang lebih kecil.
- Slide dapat dipilih dan dijeda. Autoplay memperhitungkan visibilitas halaman/hero, pointer, fokus, dan preferensi reduced motion.
- Reveal memakai IntersectionObserver sekali per elemen, perpindahan pendek 18–24 px, serta jeda 0–300 ms agar halaman tetap cepat dan tenang.
- Animasi hover diimplementasikan ulang dengan transform/opacity CSS, tanpa dependensi situs referensi.
- Konten default terlihat jika JavaScript mati. Reduced motion menampilkan seluruh konten tanpa autoplay atau animasi masuk.

Catatan ini mendeskripsikan temuan dari konfigurasi dan CSS sumber, bukan klaim pengujian visual langsung atas seluruh animasi situs referensi.
