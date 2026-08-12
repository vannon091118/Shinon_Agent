#!/usr/bin/env python3
"""LIMEN API server — started by dashboard bootstrap."""
import sys
sys.path.insert(0, "/home/vannon/Schreibtisch/projects/PZ/limen-main/src")

from limen.config import load_config
from limen.api import create_app
import uvicorn

config = load_config("/home/vannon/.config/limen/config.toml")
config.server.port = 8001
app = create_app(config)
uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info", workers=1)
