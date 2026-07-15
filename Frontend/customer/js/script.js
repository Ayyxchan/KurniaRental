/* ===== KURNIA RENTAL — Customer JS ===== */

let allMotors   = [];
let activeFilter = '';
let searchQuery  = '';
let sseSource    = null;

// ── Load Motors dari server ──
async function loadMotors() {
  try {
    const res  = await fetch('/api/motors');
    const data = await res.json();
    allMotors  = data.data || [];
    renderMotors();
  } catch(e) {
    document.getElementById('motor-grid').innerHTML =
      '<div class="loading-state" style="grid-column:1/-1;"><i class="fa-solid fa-triangle-exclamation"></i><p>Gagal memuat data. Pastikan server berjalan.</p></div>';
  }
}

// ── Notifikasi browser asli (bukan cuma toast di halaman) ──
function requestNotifPermission() {
  if (!('Notification' in window)) return;
  if (Notification.permission === 'default') {
    Notification.requestPermission();
  }
}
function sendBrowserNotification(title, body) {
  if (!('Notification' in window) || Notification.permission !== 'granted') return;
  try {
    const n = new Notification(title, {
      body, tag: 'kurnia-motor-' + Date.now(),
      icon: 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/svgs/solid/motorcycle.svg'
    });
    n.onclick = () => { window.focus(); n.close(); };
  } catch (_) {}
}
requestNotifPermission();

// ── SSE: subscribe ke channel customer ──
function connectSSE() {
  if (sseSource) sseSource.close();
  sseSource = new EventSource('/api/sse/customer');

  // Event: admin ubah status motor → update langsung di UI tanpa full reload
  sseSource.addEventListener('motor_update', e => {
    const d = JSON.parse(e.data);
    // Update data di memori lokal
    const motor = allMotors.find(m => m.id === d.motor_id);
    if (motor) {
      motor.status = d.status;
      renderMotors();   // re-render kartu motor
      showStatusToast(d);
      if (d.status === 'tersedia') {
        sendBrowserNotification('Motor tersedia lagi', `${d.nama_motor} sekarang bisa dipesan.`);
      }
    } else {
      // Motor baru atau tidak ada di list → fetch ulang
      loadMotors();
    }
  });

  // Saat koneksi terbuka
  sseSource.onopen = () => {
    sseConnectedOnce = true;
  };

  sseSource.onerror = (err) => {
    // Di sebagian platform hosting (mis. Vercel), SSE memang tidak didukung
    // dan akan selalu gagal — diamkan saja supaya tidak spam toast error
    // berulang-ulang, cukup andalkan polling cadangan di bawah.
    setTimeout(connectSSE, 5000);
  };
}

// ── Polling cadangan ──
// Jaring pengaman kalau SSE di atas tidak jalan (mis. di platform serverless
// seperti Vercel yang memutus koneksi setelah beberapa detik). Data motor
// tetap ter-update otomatis walau tanpa real-time push.
let sseConnectedOnce = false;
function startMotorPollingFallback() {
  setInterval(async () => {
    try {
      const res = await fetch('/api/motors');
      if (!res.ok) return;
      const data = await res.json();
      if (!data.success) return;
      const fresh = data.data || [];
      // Cek kalau ada status yang berubah dibanding data yang lagi ditampilkan
      let changed = false;
      fresh.forEach(fm => {
        const existing = allMotors.find(m => m.id === fm.id);
        if (existing && existing.status !== fm.status) changed = true;
      });
      allMotors = fresh;
      if (changed) renderMotors();
    } catch (err) {
      console.error('Polling motor gagal:', err);
    }
  }, 15000); // cek tiap 15 detik
}
startMotorPollingFallback();

function showStatusToast(d) {
  const statusLabel = {
    tersedia:    '✅ Tersedia kembali',
    disewa:      '🔵 Sedang disewa',
    maintenance: '🔧 Maintenance',
  };
  const label = statusLabel[d.status] || d.status;
  showToast(`${d.nama_motor}: ${label}`, d.status === 'tersedia' ? 'success' : 'info');
}

// ── Render daftar motor ──
function renderMotors() {
  let list = allMotors;
  if (activeFilter) list = list.filter(m => m.status === activeFilter);
  if (searchQuery)  list = list.filter(m =>
    m.nama_motor.toLowerCase().includes(searchQuery) ||
    m.merk.toLowerCase().includes(searchQuery)
  );

  const grid = document.getElementById('motor-grid');
  if (!list.length) {
    grid.innerHTML = '<div class="loading-state" style="grid-column:1/-1;"><i class="fa-solid fa-circle-info"></i><p>Tidak ada motor yang cocok.</p></div>';
    return;
  }

  grid.innerHTML = list.map(m => `
    <div class="motor-card" id="card-motor-${m.id}">
      <div class="motor-img">
        ${m.gambar_url
          ? `<img src="${m.gambar_url}" alt="${m.nama_motor}"
               onerror="this.parentElement.innerHTML='<i class=\\'fa-solid fa-motorcycle\\'></i>'">`
          : `<i class="fa-solid fa-motorcycle"></i>`}
      </div>
      <div class="motor-info">
        <h3>${m.nama_motor}</h3>
        <div class="motor-meta">
          <span class="motor-tag"><i class="fa-solid fa-tag"></i> ${m.merk}</span>
          ${m.tahun ? `<span class="motor-tag">${m.tahun}</span>` : ''}
        </div>
        ${m.deskripsi ? `<p style="font-size:.8rem;color:var(--text-muted);margin-bottom:.6rem;">${m.deskripsi}</p>` : ''}
        <div class="motor-footer">
          <span class="badge-status badge-${m.status}">
            ${{tersedia:'Tersedia', disewa:'Sedang Disewa', maintenance:'Maintenance'}[m.status] || m.status}
          </span>
          <button class="btn-pesan"
            ${m.status !== 'tersedia' ? 'disabled' : ''}
            onclick="openBooking(${m.id}, '${m.nama_motor.replace(/'/g,"\\'")}', ${m.harga_per_hari})">
            ${m.status === 'tersedia'
              ? '<i class="fa-solid fa-calendar-plus"></i> Pesan'
              : m.status === 'disewa' ? 'Sedang Disewa' : 'Tidak Tersedia'}
          </button>
        </div>
      </div>
    </div>
  `).join('');
}

function setFilter(btn, filter) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  activeFilter = filter;
  renderMotors();
}

function filterBySearch() {
  searchQuery = document.getElementById('search-input').value.toLowerCase().trim();
  renderMotors();
}

// ── Modal Booking ──
// Titik "anchor" (harga paket khusus) — di ANTARA anchor naik Rp5.000/jam
// dari anchor terdekat di bawahnya. Harus selalu sama dengan Backend/customer/customer.py
const JAM_ANCHORS = [
  { jam: 1,  harga: 10000 },
  { jam: 6,  harga: 25000 },
  { jam: 12, harga: 35000 },
  { jam: 24, harga: 50000 },
  { jam: 72, harga: 140000 },
];
const KENAIKAN_PER_JAM = 5000;
let currentJenisSewa = 'harian';

function hitungHargaHarian(totalHari) {
  const tiers = { 1: 50000, 2: 100000, 3: 140000 };
  if (tiers[totalHari]) return tiers[totalHari];
  return totalHari * 50000;
}

function hitungHargaJam(totalJam) {
  const last = JAM_ANCHORS[JAM_ANCHORS.length - 1];
  if (totalJam > last.jam) {
    const hari = Math.ceil(totalJam / 24);
    return hitungHargaHarian(hari);
  }
  let lower = JAM_ANCHORS[0];
  for (const anchor of JAM_ANCHORS) {
    if (totalJam === anchor.jam) return anchor.harga;
    if (totalJam < anchor.jam) break;
    lower = anchor;
  }
  return lower.harga + (totalJam - lower.jam) * KENAIKAN_PER_JAM;
}

function openBooking(motorId, motorName, harga) {
  if (typeof requireLogin === 'function' && !requireLogin('Login dulu untuk memesan motor ini')) {
    return;
  }

  document.getElementById('booking-motor-id').value    = motorId;
  document.getElementById('booking-motor-name').textContent  = motorName;

  const customerData = JSON.parse(localStorage.getItem('kurnia_customer_data') || 'null');
  const customerEmail = localStorage.getItem('kurnia_customer_email') || '';
  document.getElementById('b-nama').value  = customerData?.nama || '';
  document.getElementById('b-hp').value    = customerData?.hp || '';
  document.getElementById('b-email').value = customerEmail;
  document.getElementById('booking-customer-text').textContent =
    `${customerData?.nama || '-'} · ${customerData?.hp || '-'}`;

  document.getElementById('b-mulai').value = '';
  document.getElementById('b-selesai').value = '';
  document.getElementById('b-harian-jam-mulai').value = '';
  document.getElementById('b-harian-jam-selesai').value = '';
  document.getElementById('b-paket-tanggal').value = '';
  document.getElementById('b-paket-jam').value = '';
  document.getElementById('b-paket-jam-selesai').value = '';
  document.getElementById('b-catatan').value = '';
  document.getElementById('summary-box').style.display = 'none';

  const today = new Date().toISOString().split('T')[0];
  document.getElementById('b-mulai').min   = today;
  document.getElementById('b-selesai').min = today;
  document.getElementById('b-paket-tanggal').min = today;

  setJenisSewa('harian');

  document.getElementById('modal-booking').classList.add('show');
}

function closeBooking() { document.getElementById('modal-booking').classList.remove('show'); }

function setJenisSewa(jenis) {
  currentJenisSewa = jenis;
  document.getElementById('tab-harian').classList.toggle('active', jenis === 'harian');
  document.getElementById('tab-paket').classList.toggle('active', jenis === 'paket');
  document.getElementById('panel-harian').style.display = jenis === 'harian' ? 'block' : 'none';
  document.getElementById('panel-paket').style.display  = jenis === 'paket'  ? 'block' : 'none';
  document.getElementById('summary-box').style.display  = 'none';
}

function hitungHarga() {
  const box = document.getElementById('summary-box');

  if (currentJenisSewa === 'paket') {
    const tanggal      = document.getElementById('b-paket-tanggal').value;
    const jamMulai     = document.getElementById('b-paket-jam').value;
    const jamSelesai   = document.getElementById('b-paket-jam-selesai').value;
    if (!tanggal || !jamMulai || !jamSelesai) { box.style.display = 'none'; return; }

    const mulaiDt = new Date(`${tanggal}T${jamMulai}:00`);
    let selesaiTanggal = tanggal;
    if (jamSelesai <= jamMulai) {
      const next = new Date(tanggal); next.setDate(next.getDate() + 1);
      selesaiTanggal = next.toISOString().split('T')[0];
    }
    const selesaiDt = new Date(`${selesaiTanggal}T${jamSelesai}:00`);
    const totalJam = Math.ceil((selesaiDt - mulaiDt) / 3600000);
    if (totalJam <= 0) { box.style.display = 'none'; return; }

    const harga = hitungHargaJam(totalJam);
    document.getElementById('row-durasi').style.display = 'flex';
    document.getElementById('row-harga-hari').style.display = 'none';
    document.getElementById('s-hari').textContent  = `${totalJam} jam`;
    document.getElementById('s-total').textContent = 'Rp ' + harga.toLocaleString('id-ID');
    box.style.display = 'block';
    return;
  }

  document.getElementById('row-harga-hari').style.display = 'none';
  const mulai   = document.getElementById('b-mulai').value;
  const selesai = document.getElementById('b-selesai').value;
  if (!mulai || !selesai) { box.style.display = 'none'; return; }
  // Inklusif: mulai tanggal 6 s/d tanggal 8 = 3 hari
  const totalHari = Math.round((new Date(selesai) - new Date(mulai)) / 86400000) + 1;
  if (totalHari <= 0) { box.style.display = 'none'; return; }
  const harga = hitungHargaHarian(totalHari);
  document.getElementById('s-hari').textContent  = `${totalHari} hari`;
  document.getElementById('s-total').textContent = 'Rp ' + harga.toLocaleString('id-ID');
  box.style.display = 'block';
}

async function submitBooking() {
  const payload = {
    motor_id:  document.getElementById('booking-motor-id').value,
    nama:      document.getElementById('b-nama').value.trim(),
    no_hp:     document.getElementById('b-hp').value.trim(),
    email:     document.getElementById('b-email').value.trim(),
    catatan:   document.getElementById('b-catatan').value.trim(),
    jenis_sewa: currentJenisSewa,
  };

  if (currentJenisSewa === 'paket') {
    payload.tanggal_mulai = document.getElementById('b-paket-tanggal').value;
    payload.jam_mulai     = document.getElementById('b-paket-jam').value;
    payload.jam_selesai   = document.getElementById('b-paket-jam-selesai').value;
    if (!payload.tanggal_mulai || !payload.jam_mulai || !payload.jam_selesai) {
      showToast('Tanggal, jam mulai, dan jam selesai wajib diisi!', 'error'); return;
    }
  } else {
    payload.tanggal_mulai   = document.getElementById('b-mulai').value;
    payload.tanggal_selesai = document.getElementById('b-selesai').value;
    const jamMulai   = document.getElementById('b-harian-jam-mulai').value;
    const jamSelesai = document.getElementById('b-harian-jam-selesai').value;
    if (jamMulai)   payload.jam_mulai   = jamMulai;
    if (jamSelesai) payload.jam_selesai = jamSelesai;
    if (!payload.tanggal_mulai || !payload.tanggal_selesai) {
      showToast('Tanggal sewa wajib diisi!', 'error'); return;
    }
  }

  if (!payload.nama || !payload.no_hp) {
    showToast('Profil kamu belum lengkap. Silakan lengkapi data diri dulu.', 'error'); return;
  }

  const btn = document.getElementById('btn-submit-booking');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Mengirim...';
  try {
    const res  = await fetch('/api/booking', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      closeBooking();
      showToast(data.message, 'success');
      loadMotors();
    } else {
      showToast(data.message, 'error');
    }
  } catch(e) {
    console.error('Gagal mengirim booking:', e);
    showToast('Gagal mengirim booking. Coba lagi.', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Kirim Booking';
  }
}

// ── Cek Booking ──
function openCekBooking() {
  document.getElementById('cek-hp').value = '';
  document.getElementById('booking-results').innerHTML = '';
  document.getElementById('modal-cek').classList.add('show');
}
function closeCekBooking() { document.getElementById('modal-cek').classList.remove('show'); }

async function cekBooking() {
  const hp = document.getElementById('cek-hp').value.trim();
  if (!hp) { showToast('Masukkan nomor HP', 'error'); return; }
  const el = document.getElementById('booking-results');
  el.innerHTML = '<div style="text-align:center;padding:1rem;color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Mencari...</div>';
  try {
    const res  = await fetch(`/api/booking/cek?no_hp=${encodeURIComponent(hp)}`);
    const data = await res.json();
    if (!data.data?.length) {
      el.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:1rem;">Tidak ada booking ditemukan untuk nomor ini.</p>';
      return;
    }
    const statusInfo = {
      pending:      { badge:'badge-amber', label:'Menunggu Konfirmasi', icon:'fa-clock' },
      dikonfirmasi: { badge:'badge-blue',  label:'Dikonfirmasi ✓',      icon:'fa-circle-check' },
      selesai:      { badge:'badge-green', label:'Selesai',             icon:'fa-flag-checkered' },
      dibatalkan:   { badge:'badge-red',   label:'Dibatalkan',          icon:'fa-ban' },
    };
    el.innerHTML = data.data.map(b => {
      const s = statusInfo[b.status] || { badge:'badge-gray', label:b.status, icon:'fa-circle' };
      return `
        <div class="booking-history-item">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <h4>${b.nama_motor} <small style="font-weight:400;color:var(--text-muted);">${b.merk}</small></h4>
            <span class="badge-status ${s.badge}" style="font-size:.72rem;padding:.2rem .6rem;border-radius:99px;font-weight:600;">
              <i class="fa-solid ${s.icon}"></i> ${s.label}
            </span>
          </div>
          <p><i class="fa-solid fa-calendar" style="width:16px;"></i> ${b.tanggal_mulai} s/d ${b.tanggal_selesai} (${b.total_hari} hari)</p>
          <p><i class="fa-solid fa-money-bill" style="width:16px;"></i> Total: <strong>Rp ${Number(b.total_harga).toLocaleString('id-ID')}</strong></p>
          <p style="margin-top:.5rem;font-size:.75rem;color:#94a3b8;">
            Dipesan: ${new Date(b.created_at).toLocaleDateString('id-ID',{day:'2-digit',month:'long',year:'numeric'})}
          </p>
        </div>
      `;
    }).join('');
  } catch(e) {
    el.innerHTML = '<p style="color:var(--danger);">Gagal mengambil data. Coba lagi.</p>';
  }
}

// ── Toast ──
function showToast(msg, type='success') {
  const el = document.getElementById('toast');
  el.textContent = msg; el.className = `show ${type}`;
  setTimeout(() => el.className = '', 3500);
}

// ── Init ──
loadMotors();
connectSSE();   // connect SSE untuk update real-time dari admin
