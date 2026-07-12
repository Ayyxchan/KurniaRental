// Toggle sidebar (off-canvas menu) di layar sempit (tablet/HP) untuk
// halaman customer, sama seperti perilaku di panel admin.
document.addEventListener('DOMContentLoaded', function () {
  var sidebar = document.querySelector('.customer-layout .sidebar');
  var overlay = document.querySelector('.customer-layout .sidebar-overlay');
  var openBtn = document.querySelector('.customer-mobile-topbar .menu-toggle');
  var closeBtn = document.querySelector('.customer-layout .sidebar-close');

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

  // Tutup otomatis saat salah satu menu diklik, biar tidak menutupi
  // konten yang baru saja dituju (mis. setelah klik "Home"/"Profil").
  document.querySelectorAll('.customer-layout .nav-item').forEach(function (link) {
    link.addEventListener('click', closeSidebar);
  });

  // Kalau layar di-resize ke ukuran besar (rotasi tablet, atau balik ke
  // laptop), pastikan sidebar tidak "nyangkut" terbuka dengan overlay
  // gelap yang tidak perlu lagi di tampilan desktop.
  window.addEventListener('resize', function () {
    if (window.innerWidth > 1080) closeSidebar();
  });
});
