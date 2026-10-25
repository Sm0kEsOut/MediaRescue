import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from media_rescue import process_media
import subprocess
import threading
import queue
import sys
import os

class MediaRescueGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MediaRescue")
        self.root.geometry("700x510")
        self.root.minsize(600, 450)

        self.source = tk.StringVar()
        self.output = tk.StringVar()
        self.status = tk.StringVar(value="Ready")
        self.messages = queue.Queue()
        self.running = False

        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame, text="MediaRescue",
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")

        ttk.Label(
            frame,
            text="Photo & Video Reconstruction Utility"
        ).pack(anchor="w", pady=(0, 20))

        self.folder_row(frame, "Source folder",
                        self.source)

        self.folder_row(frame, "Output folder",
                        self.output)

        warning = (
            "Security notice: This tool reconstructs media "
            "but does not detect Pegasus or guarantee "
            "that files are malware-free."
        )

        ttk.Label(
            frame, text=warning,
            wraplength=600,
            foreground="#a06000"
        ).pack(anchor="w", pady=12)

        self.start_button = ttk.Button(
            frame,
            text="Start Reconstruction",
            command=self.start
        )
        self.start_button.pack(fill="x", pady=10)

        self.progress = ttk.Progressbar(
            frame, mode="indeterminate"
        )
        self.progress.pack(fill="x")

        ttk.Label(
            frame, textvariable=self.status
        ).pack(anchor="w", pady=8)

        log_frame = ttk.Frame(frame)
        log_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")

        self.log = tk.Text(
            log_frame,
            height=10,
            state="disabled",
            wrap="word",
            yscrollcommand=scrollbar.set
        )
        self.log.pack(side="left", fill="both", expand=True)

        scrollbar.config(command=self.log.yview)

        ttk.Button(
            frame,
            text="Open Output Folder",
            command=self.open_output
        ).pack(fill="x", pady=(10, 0))

        self.root.after(100, self.check_messages)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def folder_row(self, parent, title, variable):
        ttk.Label(parent, text=title).pack(anchor="w")

        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(4, 12))

        ttk.Entry(
            row, textvariable=variable
        ).pack(side="left", fill="x", expand=True)

        ttk.Button(
            row,
            text="Browse",
            command=lambda: self.browse(variable)
        ).pack(side="left", padx=(8, 0))

    def browse(self, variable):
        folder = filedialog.askdirectory()
        if folder:
            variable.set(folder)

    def write_log(self, message):
        self.log.config(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def start(self):
        if self.running:
            return

        src = Path(self.source.get()).expanduser()
        dst = Path(self.output.get()).expanduser()

        if not src.is_dir():
            messagebox.showerror(
                "Invalid source", "Select an existing source folder."
            )
            return

        src = src.resolve()
        dst = dst.resolve()

        if src == dst or src in dst.parents or dst in src.parents:
            messagebox.showerror(
                "Invalid folders",
                "Source and output must be separate, "
                "non-nested folders."
            )
            return

        if not messagebox.askyesno(
            "Start reconstruction?",
            "Files will be decoded and reconstructed. "
            "Untrusted media may exploit decoder vulnerabilities. "
            "Use an isolated environment for high-risk files. "
            "Continue?"
        ):
            return

        self.running = True
        self.start_button.config(state="disabled")
        self.progress.start(12)
        self.status.set("Processing media...")
        self.write_log("Starting reconstruction...")

        threading.Thread(
            target=self.worker,
            args=(str(src), str(dst)),
            daemon=True
        ).start()

    def worker(self, src, dst):
        try:
            def update_progress(current, total, filename):
                self.messages.put((
                    "log",
                    f"[{current}/{total}] {filename}"
                ))

            process_media(
                src,
                dst,
                progress_callback=update_progress
            )

            self.messages.put(("done", 0))

        except Exception as error:
            self.messages.put(("error", str(error)))

    def check_messages(self):
        try:
            while True:
                kind, data = self.messages.get_nowait()

                if kind == "log":
                    self.write_log(data)

                elif kind == "done":
                    self.finish(data == 0)

                elif kind == "error":
                    self.write_log("ERROR: " + data)
                    self.finish(False)

        except queue.Empty:
            pass

        self.root.after(100, self.check_messages)

    def finish(self, success):
        self.running = False
        self.progress.stop()
        self.start_button.config(state="normal")

        if success:
            self.status.set("Reconstruction finished")
            messagebox.showinfo(
                "Completed",
                "Processing finished. Review report.csv "
                "for rejected and skipped files. "
                "Rebuilt files are not certified malware-free."
            )
        else:
            self.status.set("Processing failed")
            messagebox.showerror(
                "Error",
                "Processing failed. Review the log."
            )

    def open_output(self):
        folder = Path(self.output.get())
        if folder.is_dir():
            os.startfile(str(folder))
        else:
            messagebox.showwarning(
                "Folder missing",
                "The output folder does not exist yet."
            )

    def close(self):
        if self.running:
            messagebox.showwarning(
                "Processing active",
                "Reconstruction is still running. "
                "Finish processing before closing."
            )
            return

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    MediaRescueGUI(root)
    root.mainloop()