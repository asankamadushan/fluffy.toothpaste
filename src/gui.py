"""Main application window."""

from __future__ import annotations

import logging
import tkinter as tk
from importlib.metadata import version as _pkg_version
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk

import prefs
import session
import stitcher
from monitors import Monitor, virtual_size

_log = logging.getLogger(__name__)

_MENU_FONT = ("sans-serif", 10)  # consistent font across all menus
_MENU_ITEM_W = 14                # fixed label width (chars) for all menu items
_MENU_ITEM_H = 28                # fixed height (px) for all menu items

# Canvas dimensions for the monitor diagram
DIAGRAM_W = 700
DIAGRAM_H = 260
DIAGRAM_PAD = 20


class App(tk.Tk):
    def __init__(self, monitors: list[Monitor]) -> None:
        super().__init__()
        self.title("Desktop Background")
        self.resizable(False, False)
        self.configure(bg="#1e1e2e")

        self.monitors = monitors
        self.assignments: dict[str, Path] = session.load(monitors)
        self.prefs: dict = prefs.load()
        self.selected: str | None = None
        self._thumbs: dict[str, ImageTk.PhotoImage] = {}  # prevent GC
        self._label_vars: dict[str, tk.StringVar] = {}

        self._build_ui()
        self._draw_diagram()

    # ── UI Construction ────────────────────────────────────────────────────

    def _build_menubar(self) -> None:
        """Build the menubar."""
        _common = dict(
            tearoff=0, font=_MENU_FONT,
            bg="#1e1e2e", fg="#cdd6f4",
            activebackground="#45475a", activeforeground="#cdd6f4",
            borderwidth=0, relief="flat",
        )

        # 1px-wide transparent image forces all items to _MENU_ITEM_H px tall.
        # Stored on self to prevent GC.
        self._menu_spacer = tk.PhotoImage(width=1, height=_MENU_ITEM_H)

        def _item(label: str) -> str:
            return label.ljust(_MENU_ITEM_W)

        def _cmd(menu: tk.Menu, label: str, command) -> None:  # type: ignore[type-arg]
            menu.add_command(
                label=_item(label),
                image=self._menu_spacer,
                compound="left",
                command=command,
            )

        menubar = tk.Menu(self, **_common)

        file_menu = tk.Menu(menubar, **_common)
        _cmd(file_menu, "Preferences", self._show_prefs)
        file_menu.add_separator()
        _cmd(file_menu, "Exit", self._exit)

        help_menu = tk.Menu(menubar, **_common)
        _cmd(help_menu, "About", self._show_about)

        menubar.add_cascade(label="File", menu=file_menu)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)

    def _build_ui(self) -> None:
        self._build_menubar()
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background="#1e1e2e", foreground="#cdd6f4")
        style.configure("TButton", background="#313244", foreground="#cdd6f4",
                        relief="flat", padding=6)
        style.map("TButton", background=[("active", "#45475a")])
        style.configure("Apply.TButton", background="#89b4fa", foreground="#1e1e2e")
        style.map("Apply.TButton", background=[("active", "#74c7ec")])

        # Monitor diagram
        self.canvas = tk.Canvas(
            self, width=DIAGRAM_W, height=DIAGRAM_H,
            bg="#181825", highlightthickness=0,
        )
        self.canvas.pack(padx=20, pady=(20, 10))
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Double-Button-1>", self._on_canvas_double_click)

        # Per-monitor rows
        self.row_frame = tk.Frame(self, bg="#1e1e2e")
        self.row_frame.pack(fill="x", padx=20, pady=(0, 10))
        self._build_monitor_rows()

        # Status + Apply
        bottom = tk.Frame(self, bg="#1e1e2e")
        bottom.pack(fill="x", padx=20, pady=(0, 20))

        self.status = tk.Label(bottom, text="Select a monitor to begin.",
                               bg="#1e1e2e", fg="#6c7086", anchor="w")
        self.status.pack(side="left", fill="x", expand=True)

        ttk.Button(bottom, text="Apply", style="Apply.TButton",
                   command=self._apply).pack(side="right")

    def _build_monitor_rows(self) -> None:
        for widget in self.row_frame.winfo_children():
            widget.destroy()

        headers = tk.Frame(self.row_frame, bg="#1e1e2e")
        headers.pack(fill="x", pady=(0, 4))
        for col, text, anchor, w in [
            (0, "Monitor", "w", 120),
            (1, "Resolution", "w", 100),
            (2, "Image", "w", 340),
            (3, "", "e", 100),
        ]:
            tk.Label(headers, text=text, bg="#1e1e2e", fg="#6c7086",
                     width=w // 8, anchor=anchor).grid(
                row=0, column=col, sticky="w", padx=(0, 8))

        for monitor in self.monitors:
            self._monitor_row(monitor)

    def _monitor_row(self, monitor: Monitor) -> None:
        """Build a row for a monitor."""
        row = tk.Frame(self.row_frame, bg="#313244")
        row.pack(fill="x", pady=2)

        name_lbl = tk.Label(
            row, text=monitor.name + (" ★" if monitor.primary else ""),
            bg="#313244", fg="#cdd6f4", width=15, anchor="w",
        )
        name_lbl.pack(side="left", padx=(8, 0))

        tk.Label(
            row, text=f"{monitor.width}×{monitor.height}",
            bg="#313244", fg="#a6adc8", width=12, anchor="w",
        ).pack(side="left")

        img_var = tk.StringVar(value="—")
        if monitor.name in self.assignments:
            img_var.set(self.assignments[monitor.name].name)
        self._label_vars[monitor.name] = img_var
        tk.Label(row, textvariable=img_var, bg="#313244", fg="#89dceb",
                 width=42, anchor="w").pack(side="left")

        ttk.Button(
            row, text="Browse",
            command=lambda m=monitor, v=img_var: self._browse(m, v),
        ).pack(side="right", padx=4, pady=3)
        ttk.Button(
            row, text="Clear",
            command=lambda m=monitor, v=img_var: self._clear(m, v),
        ).pack(side="right", padx=(0, 0), pady=3)

    # ── Monitor Diagram ────────────────────────────────────────────────────

    def _scale(self) -> tuple[float, int, int]:
        vw, vh = virtual_size(self.monitors)
        usable_w = DIAGRAM_W - DIAGRAM_PAD * 2
        usable_h = DIAGRAM_H - DIAGRAM_PAD * 2
        scale = min(usable_w / vw, usable_h / vh)
        ox = DIAGRAM_PAD + (usable_w - vw * scale) // 2
        oy = DIAGRAM_PAD + (usable_h - vh * scale) // 2
        return scale, int(ox), int(oy)

    def _monitor_rect(self, m: Monitor) -> tuple[int, int, int, int]:
        scale, ox, oy = self._scale()
        x1 = ox + int(m.x * scale)
        y1 = oy + int(m.y * scale)
        x2 = x1 + int(m.width * scale)
        y2 = y1 + int(m.height * scale)
        return x1, y1, x2, y2

    def _draw_diagram(self) -> None:
        self.canvas.delete("all")
        self._thumbs.clear()

        for m in self.monitors:
            x1, y1, x2, y2 = self._monitor_rect(m)
            selected = m.name == self.selected
            fill = "#313244" if not selected else "#1d3461"
            outline = "#89b4fa" if selected else "#45475a"

            self.canvas.create_rectangle(
                x1, y1, x2, y2, fill=fill, outline=outline, width=2
            )

            # Thumbnail
            if m.name in self.assignments:
                tw, th = x2 - x1 - 4, y2 - y1 - 4
                if tw > 0 and th > 0:
                    try:
                        thumb = stitcher.thumbnail(self.assignments[m.name], tw, th)
                        photo = ImageTk.PhotoImage(thumb)
                        self._thumbs[m.name] = photo
                        self.canvas.create_image(
                            x1 + 2, y1 + 2, anchor="nw", image=photo
                        )
                    except OSError as exc:
                        # File missing, permission denied, or unrecognised format
                        _log.debug("Thumbnail skipped for %s: %s", m.name, exc)
                    except tk.TclError as exc:
                        # Tk failed to create the PhotoImage (e.g. display error)
                        _log.debug("Thumbnail skipped for %s: %s", m.name, exc)

            label = f"{m.name}\n{m.width}×{m.height}"
            if m.primary:
                label += "\n[primary]"
            self.canvas.create_text(
                (x1 + x2) // 2, (y1 + y2) // 2,
                text=label, fill="white", font=("sans-serif", 9),
                justify="center",
            )

    def _on_canvas_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        for m in self.monitors:
            x1, y1, x2, y2 = self._monitor_rect(m)
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.selected = m.name
                self._draw_diagram()
                return

    def _on_canvas_double_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        for m in self.monitors:
            x1, y1, x2, y2 = self._monitor_rect(m)
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self._browse(m, self._label_vars[m.name])
                return

    # ── Actions ────────────────────────────────────────────────────────────

    def _browse(self, monitor: Monitor, label_var: tk.StringVar) -> None:
        """Browse for an image file."""
        path = filedialog.askopenfilename(
            title=f"Image for {monitor.name}",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.bmp *.webp *.tiff *.tif"),
                ("All files", "*"),
            ],
            initialdir=self.prefs["pictures_dir"],
        )
        if path:
            self.assignments[monitor.name] = Path(path)
            label_var.set(Path(path).name)
            self.selected = monitor.name
            self._draw_diagram()
            self._set_status(f"{monitor.name} → {Path(path).name}")

    def _clear(self, monitor: Monitor, label_var: tk.StringVar) -> None:
        self.assignments.pop(monitor.name, None)
        label_var.set("—")
        self._draw_diagram()

    def _apply(self) -> None:
        """Apply the wallpaper to the monitors."""
        if not self.assignments:
            self._set_status("No images assigned.")
            return

        import wallpaper

        self._set_status("Applying…")
        self.update()
        try:
            path = stitcher.build(self.assignments, self.monitors)
            wallpaper.apply(path)
            session.save(self.assignments)
            self._set_status("Applied successfully.")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            self._set_status("Failed — see error dialog.")

    def _show_prefs(self) -> None:
        """Open the Preferences dialog."""
        dlg = tk.Toplevel(self)
        dlg.title("Preferences")
        dlg.resizable(False, False)
        dlg.configure(bg="#1e1e2e")
        dlg.grab_set()

        colors = dict(bg="#1e1e2e", fg="#cdd6f4")

        tk.Label(dlg, text="Default pictures folder", **colors).grid(
            row=0, column=0, sticky="w", padx=12, pady=(16, 4)
        )

        dir_var = tk.StringVar(value=self.prefs["pictures_dir"])
        entry = tk.Entry(dlg, textvariable=dir_var, width=42,
                         bg="#313244", fg="#cdd6f4",
                         insertbackground="#cdd6f4", relief="flat")
        entry.grid(row=1, column=0, padx=12, pady=(0, 4), sticky="ew")

        def _pick() -> None:
            chosen = filedialog.askdirectory(
                title="Default pictures folder",
                initialdir=dir_var.get(),
            )
            if chosen:
                dir_var.set(chosen)

        ttk.Button(dlg, text="Browse…", command=_pick).grid(
            row=1, column=1, padx=(0, 12), pady=(0, 4)
        )

        def _save() -> None:
            self.prefs["pictures_dir"] = dir_var.get()
            prefs.save(self.prefs)
            dlg.destroy()

        btn_frame = tk.Frame(dlg, bg="#1e1e2e")
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(8, 12), padx=12, sticky="e")
        ttk.Button(
            btn_frame, text="Cancel", command=dlg.destroy
        ).pack(side="right", padx=(4, 0))
        ttk.Button(
            btn_frame, text="Save", style="Apply.TButton", command=_save
        ).pack(side="right")

    def _show_about(self) -> None:
        """Show the about dialog."""
        try:
            ver = _pkg_version("fluffy.toothpaste")
        except Exception:
            ver = "unknown"
        messagebox.showinfo(
            "About",
            f"Desktop Background Manager\nVersion {ver}\n\n"
            "Multi-monitor wallpaper manager\nfor Linux and Windows.",
        )

    def _exit(self) -> None:
        """Exit the application."""
        self.destroy()

    def _set_status(self, msg: str) -> None:
        """Set the status message."""
        self.status.configure(text=msg)
