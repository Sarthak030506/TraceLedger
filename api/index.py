import sys
import os

# Add repo root to python path so backend, sidecar, integrity modules can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
