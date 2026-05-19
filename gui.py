from argparse import Namespace

def main(args: Namespace) -> None:
    import tkinter as tk
    from tkinter import ttk
    import backup

    root = tk.Tk(className="borXplo")

    frame = ttk.Frame(root)
    frame.pack()

    ttk.Label(frame, text="It's time to back up your data!", font=("Adwaita Sans", 14, "bold"), padding=10).pack()

    btn_frame = ttk.Frame(frame)
    btn_frame.pack(pady=10)

    def start() -> None:
        root.destroy()
        backup.main(args)
    ttk.Button(btn_frame, text="Start", command=start).pack(anchor="center", side="left", padx=10)
    ttk.Button(btn_frame, text="Cancel", command=root.destroy).pack(anchor="center", side="right", padx=10)

    root.mainloop()
