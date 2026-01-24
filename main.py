import os

from ui.app import MediaConverterApp


def main() -> None:
    try:
        if os.name == "nt":
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = MediaConverterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
