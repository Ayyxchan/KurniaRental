// Toggle sidebar (off-canvas menu) di layar kecil (tablet/HP)
document.addEventListener('DOMContentLoaded', function () {
  var sidebar = document.querySelector('.sidebar');
  var overlay = document.querySelector('.sidebar-overlay');
  var openBtn = document.querySelector('.menu-toggle');
  var closeBtn = document.querySelector('.sidebar-close');

  if (!sidebar || !overlay) return;

  function openSidebar() {
    sidebar.classList.add('is-open');
    overlay.classList.add('show');
  }

  function closeSidebar() {
    sidebar.classList.remove('is-open');
    overlay.classList.remove('show');
  }

  if (openBtn) openBtn.addEventListener('click', openSidebar);
  if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
  overlay.addEventListener('click', closeSidebar);

  // Tutup otomatis saat salah satu menu diklik (biar tidak nutupin isi
  // halaman baru begitu pindah halaman/scroll di HP)
  document.querySelectorAll('.nav-item').forEach(function (link) {
    link.addEventListener('click', closeSidebar);
  });

  // Kalau layar di-resize ke ukuran besar (misal rotasi tablet ke landscape
  // atau balik ke laptop), pastikan sidebar tidak "nyangkut" dalam kondisi
  // terbuka dengan overlay gelap yang tidak perlu.
  window.addEventListener('resize', function () {
    if (window.innerWidth > 900) closeSidebar();
  });
});
