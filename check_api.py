import urllib.request
import urllib.error

urls = [
    'http://127.0.0.1:5000/api/motors',
    'http://127.0.0.1:5000/api/booking/cek?no_hp=08123456789',
    'http://127.0.0.1:5000/api/admin/dashboard/stats',
]

for url in urls:
    print('REQUEST:', url)
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            print('STATUS', r.status)
            print(r.read(500).decode('utf-8', errors='replace'))
    except urllib.error.HTTPError as e:
        print('HTTP', e.code)
        print(e.read(500).decode('utf-8', errors='replace'))
    except Exception as e:
        print('ERR', e)
    print('---')
