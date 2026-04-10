#!/usr/bin/env python3
import traceback

from db_V3 import init_db
from gui.main_gui import ClipFusionApp


def main():
    init_db()
    app = ClipFusionApp()
    app.run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(traceback.format_exc())
        raise
