import tkinter as tk
from app import RFIDScannerApp

if __name__ == "__main__":
    root = tk.Tk()
    app = RFIDScannerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()