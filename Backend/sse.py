"""
Server-Sent Events (SSE) — real-time push dari server ke browser.

Cara kerja:
- Admin buka halaman bookings.html → browser connect ke /api/sse/admin
- Customer buka index.html         → browser connect ke /api/sse/customer
- Saat ada booking baru  → push event "new_booking"  → notif muncul di admin
- Saat admin ubah status → push event "motor_update"  → halaman customer refresh otomatis
"""

import json
import queue
import threading
from flask import Blueprint, Response, stream_with_context

sse_bp = Blueprint('sse', __name__)

# Satu set queue per channel: "admin" dan "customer"
_subscribers: dict[str, list[queue.Queue]] = {
    'admin':    [],
    'customer': [],
}
_lock = threading.Lock()


def _subscribe(channel: str) -> queue.Queue:
    q: queue.Queue = queue.Queue(maxsize=20)
    with _lock:
        _subscribers[channel].append(q)
    return q


def _unsubscribe(channel: str, q: queue.Queue):
    with _lock:
        try:
            _subscribers[channel].remove(q)
        except ValueError:
            pass


def push_event(channel: str, event: str, data: dict):
    """Kirim event ke semua subscriber di channel tertentu."""
    payload = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    with _lock:
        dead = []
        for q in _subscribers[channel]:
            try:
                q.put_nowait(payload)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _subscribers[channel].remove(q)


def _stream(channel: str):
    q = _subscribe(channel)
    try:
        # Kirim heartbeat pertama supaya koneksi langsung established
        yield ": connected\n\n"
        while True:
            try:
                msg = q.get(timeout=25)   # timeout → kirim heartbeat
                yield msg
            except queue.Empty:
                yield ": heartbeat\n\n"   # cegah proxy timeout
    finally:
        _unsubscribe(channel, q)


@sse_bp.route('/sse/admin')
def sse_admin():
    """Admin subscribe di sini — terima notif booking baru."""
    return Response(
        stream_with_context(_stream('admin')),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':  'no-cache',
            'X-Accel-Buffering': 'no',   # penting untuk Nginx
        }
    )


@sse_bp.route('/sse/customer')
def sse_customer():
    """Customer subscribe di sini — terima update status motor dari admin."""
    return Response(
        stream_with_context(_stream('customer')),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':  'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )
