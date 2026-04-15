"""Entry point."""

from gui import App
from monitors import get_monitors


def main() -> None:
    monitors = get_monitors()
    app = App(monitors)
    app.mainloop()


if __name__ == "__main__":
    main()
