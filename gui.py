def main() -> None:
    import tkinter as tk
    from tkinter import ttk
    import backup

    root = tk.Tk(className="borXplo")

    frame = ttk.Frame(root)
    frame.pack()

    ttk.Label(frame, text="It's time to back up your data!", font=("Adwaita Sans", 14, "Bold"), padding=10).pack()

    def start() -> None:
        root.destroy()
        backup.main()
    ttk.Button(frame, text="Start", command=start, padding=10).pack(anchor="sw")
    ttk.Button(frame, text="Cancel", command=root.destroy, padding=10).pack(anchor="se")

    root.mainloop()
