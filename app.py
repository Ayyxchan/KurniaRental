import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(ROOT, 'KurniaRental', 'KurniaRental')
APP_PATH = os.path.join(PROJECT_DIR, 'app.py')

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

spec = importlib.util.spec_from_file_location('kurniarental_app', APP_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

app = module.create_app()

if __name__ == '__main__':
    app.run(debug=app.config.get('DEBUG', False), host='0.0.0.0', port=5000, threaded=True)
