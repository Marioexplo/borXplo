from tkinter import ttk
_action: ttk.Label
_message: ttk.Label
_borg: ttk.Label

def main() -> None:
    global _action, _message, _borg, can_close
    import tkinter as tk
    import typing
    import main
    import backup
    import gui
    from threading import Thread
    from sys import exit

    def _error(text: str) -> typing.Never:
        gui.set_message(text)
        exit()
    main.error = _error

    root = tk.Tk(className="borXplo")
    root.minsize(480, 960)

    frame = ttk.Frame(root)
    frame.pack(fill="both", expand=True)

    def section(header: str, font: tuple[str, int], fill: typing.Literal["both", "y"]) -> ttk.Label:
        """Set section header's text and label's font and wether tkinter can automatically change its size."""
        new_frame = ttk.Frame(frame, padding=20)
        new_frame.pack(fill="both", expand=True)
        ttk.Label(new_frame, text=header, font=("Adwaita Sans, Bold", 14)).pack(anchor="n")
        label = ttk.Label(new_frame, background="#cccccc", font=font)
        label.pack(side="bottom", fill=fill, expand=True)
        return label

    _action = section("Current action:", ("Adwaita Sans", 14), "y")
    _message = section("borXplo message:", ("Adwaita Sans", 14), "y")
    _borg = section("Borg message:", ("Adwaita Mono", 10), "both")

    backupper = Thread(target=backup.main, args=[True])

    def quit() -> None | typing.Never:
        dial = tk.Toplevel()
        dial.grab_set()

        frame = ttk.Frame(dial, padding=10)
        frame.pack()

        ttk.Label(frame, text="Are you sure you want to stop the backup process?", font=("Adwaita Sans, Bold", 14)).pack()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack()

        def exit() -> None:
            import backup
            backup.must_exit = True

            root.config(cursor="watch")
            dial.destroy()
            backupper.join()
            root.config(cursor="arrow")
            root.destroy()

        ttk.Button(btn_frame, text="Yes", command=exit).pack(anchor="center", side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dial.destroy).pack(anchor="center", side="right", padx=5)

        dial.wait_window()

    button = ttk.Button(frame, padding=20, text="Quit", command=quit)
    button.pack()

    root.protocol("WM_DELETE_WINDOW", quit)
    def _can_close() -> None:
        button.config(text="Close", command=root.destroy)
        root.protocol("WM_DELETE_WINDOW", root.destroy)
    can_close = _can_close

    backupper.start()
    root.mainloop()
    exit()

def _set_text(label: ttk.Label, text: str) -> None:
    label.config(text=text)

def set_action(text: str) -> None:
    _set_text(_action, text)

def set_message(text: str) -> None:
    _set_text(_message, text)

def set_borg(text: str) -> None:
    _set_text(_borg, text)
