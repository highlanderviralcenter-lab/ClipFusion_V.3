#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_gui import ClipFusionApp

if __name__ == "__main__":
    app = ClipFusionApp()
    app.run()
