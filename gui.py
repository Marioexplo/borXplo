from tkinter import ttk
_action: ttk.Label
_message: ttk.Label
_borg: ttk.Label

def main() -> None:
    import tkinter as tk
    global _action, _message, _borg

    root = tk.Tk(className="borXplo")
    root.resizable(False, False)

    frame = ttk.Frame(root)
    frame.pack()

    def section(header: str, font: tuple[str, int], propagate: bool) -> ttk.Label:
        """Set section header's text and label's font and wether tkinter can automatically change its size."""
        new_frame = ttk.Frame(frame, padding=20)
        new_frame.pack()
        ttk.Label(new_frame, text=header, font=("Adwaita Sans, Bold", 14)).pack(anchor="nw")
        label = ttk.Label(new_frame, background="#cccccc", font=font, width=25)
        label.pack(side="bottom")
        label.pack_propagate(propagate)
        return label

    _action = section("Current action:", ("Adwaita Sans", 14), False)
    _message = section("borXplo message:", ("Adwaita Sans", 14), False)
    _borg = section("Borg message:", ("Adwaita Mono", 10), True)

    root.mainloop()

def _set_text(label: ttk.Label, text: str) -> None:
    label.config(text=text)

def set_action(text: str) -> None:
    _set_text(_action, text)

def set_message(text: str) -> None:
    _set_text(_message, text)

def set_borg(text: str) -> None:
    _set_text(_borg, text)
