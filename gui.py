import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from threading import Thread, Event
from queue import Queue, Empty
import os

from media_rescue import process_media
from defender_scan import scan_folder, DefenderScanError, DefenderScanCancelled


class MediaRescueGUI:
    def __init__(self, root):
        self.root = root
        self.root.title('MediaRescue')
        self.root.geometry('730x560')
        self.source = tk.StringVar()
        self.output = tk.StringVar()
        self.status = tk.StringVar(value='Ready')
        self.use_defender = tk.BooleanVar(value=False)
        self.progress_value = tk.DoubleVar(value=0)
        self.events = Queue()
        self.cancel_event = Event()
        self.running = False
        self.completed = 0
        self.total = 0

        frame = ttk.Frame(root, padding=18)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='MediaRescue', font=('Segoe UI', 22, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Photo & video reconstruction — not malware detection').pack(anchor='w', pady=(0, 14))
        self.folder_row(frame, 'Source folder', self.source)
        self.folder_row(frame, 'Output folder', self.output)
        ttk.Checkbutton(frame, text='Optional: scan originals and output with Microsoft Defender',
                        variable=self.use_defender).pack(anchor='w', pady=(0, 8))
        ttk.Label(frame, text='Only reconstructed files should be considered for transfer. '
                  'Processing untrusted files can expose decoder vulnerabilities.', wraplength=670).pack(anchor='w', pady=(5, 12))
        actions = ttk.Frame(frame)
        actions.pack(fill='x')
        self.start_button = ttk.Button(actions, text='Start Reconstruction', command=self.start)
        self.start_button.pack(side='left', fill='x', expand=True, padx=(0, 5))
        self.cancel_button = ttk.Button(actions, text='Cancel', command=self.cancel, state='disabled')
        self.cancel_button.pack(side='left', fill='x', expand=True, padx=(5, 0))
        self.progress = ttk.Progressbar(frame, variable=self.progress_value, maximum=100, mode='determinate')
        self.progress.pack(fill='x', pady=(15, 4))
        ttk.Label(frame, textvariable=self.status).pack(anchor='w', pady=(0, 10))
        logframe = ttk.Frame(frame)
        logframe.pack(fill='both', expand=True)
        scroll = ttk.Scrollbar(logframe)
        scroll.pack(side='right', fill='y')
        self.log = tk.Text(logframe, state='disabled', wrap='word', yscrollcommand=scroll.set, height=12)
        self.log.pack(side='left', fill='both', expand=True)
        scroll.configure(command=self.log.yview)
        ttk.Button(frame, text='Open Output Folder', command=self.open_output).pack(fill='x', pady=(10, 0))
        self.root.after(100, self.poll_events)
        self.root.protocol('WM_DELETE_WINDOW', self.close)

    def folder_row(self, frame, label, variable):
        ttk.Label(frame, text=label).pack(anchor='w')
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=(3, 12))
        ttk.Entry(row, textvariable=variable).pack(side='left', fill='x', expand=True)
        ttk.Button(row, text='Browse', command=lambda: self.browse(variable)).pack(side='left', padx=(8, 0))

    def browse(self, variable):
        selected = filedialog.askdirectory()
        if selected:
            variable.set(selected)

    def append_log(self, msg):
        self.log.configure(state='normal')
        self.log.insert('end', msg + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def start(self):
        if self.running:
            return
        raw_source = self.source.get().strip()
        raw_target = self.output.get().strip()
        if not raw_source or not raw_target:
            messagebox.showerror('Missing folders', 'Select both source and output folders.')
            return
        src, dst = Path(raw_source).resolve(), Path(raw_target).resolve()
        if not src.is_dir():
            messagebox.showerror('Invalid source', 'Select an existing source folder.')
            return
        if src == dst or src in dst.parents or dst in src.parents:
            messagebox.showerror('Invalid folders', 'Choose separate, non-nested folders.')
            return
        if not messagebox.askyesno('Start reconstruction?', 'Media will be decoded and re-encoded. '
                                   'For high-risk files, use an isolated virtual machine. Continue?'):
            return
        self.cancel_event.clear()
        self.progress_value.set(0)
        self.completed, self.total = 0, 0
        self.running = True
        self.start_button.configure(state='disabled')
        self.cancel_button.configure(state='normal')
        self.status.set('Preparing file list...')
        self.append_log('Starting reconstruction...')
        Thread(target=self.worker, args=(str(src), str(dst), self.use_defender.get()), daemon=True).start()

    def worker(self, src, dst, use_defender):
        try:
            def report(done, total, filename, status):
                self.events.put(('progress', (done, total, filename, status)))
            def scan_log(message):
                self.events.put(('log', message))
            if use_defender:
                self.events.put(('phase', 'Scanning originals with Defender...'))
                scan_folder(src, self.cancel_event, scan_log)
            if self.cancel_event.is_set():
                self.events.put(('cancelled', None))
                return
            self.events.put(('phase', 'Reconstructing media...'))
            result = process_media(src, dst, progress_callback=report,
                                   cancel_event=self.cancel_event)
            if use_defender and not result['cancelled'] and result['counts']['REBUILT']:
                self.events.put(('phase', 'Scanning reconstructed files with Defender...'))
                scan_folder(dst, self.cancel_event, scan_log)
            if self.cancel_event.is_set():
                result['cancelled'] = True
            self.events.put(('done', result))
        except DefenderScanCancelled:
            self.events.put(('cancelled', None))
        except Exception as error:
            self.events.put(('error', str(error)))

    def cancel(self):
        if self.running:
            self.cancel_event.set()
            self.cancel_button.configure(state='disabled')
            self.status.set('Cancelling...')
            self.append_log('Cancellation requested; completing cleanup...')

    def poll_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'phase':
                    self.status.set(value)
                    self.append_log(value)
                elif kind == 'log':
                    self.append_log(value)
                elif kind == 'cancelled':
                    self.running = False
                    self.start_button.configure(state='normal')
                    self.cancel_button.configure(state='disabled')
                    self.status.set('Cancelled — no safe-scan status assigned')
                elif kind == 'progress':
                    done, total, filename, status = value
                    self.completed, self.total = done, total
                    self.progress_value.set(100 * done / total if total else 100)
                    if not self.cancel_event.is_set():
                        self.status.set(f'{done}/{total} files processed ({self.progress_value.get():.0f}%)')
                    self.append_log(f'[{done}/{total}] {status}: {filename}')
                elif kind == 'done':
                    self.finish(value)
                elif kind == 'error':
                    self.append_log('ERROR: ' + value)
                    self.finish(None)
        except Empty:
            pass
        self.root.after(100, self.poll_events)

    def finish(self, summary):
        self.running = False
        self.start_button.configure(state='normal')
        self.cancel_button.configure(state='disabled')
        if summary is None:
            self.status.set('Processing failed. See log.')
            messagebox.showerror('Failed / scan not cleared', 'Processing or Defender scanning failed. Do not treat output as cleared. Review the log and Windows Security.')
        else:
            counts = summary['counts']
            label = 'Cancelled' if summary['cancelled'] else 'Finished'
            self.status.set(f"{label}: {summary['processed']}/{summary['total']} files handled")
            self.append_log(f"{label}. Rebuilt: {counts['REBUILT']}, rejected: {counts['REJECTED']}, skipped: {counts['SKIPPED']}")
            self.append_log('Report: ' + summary['report'])
            messagebox.showinfo(label, 'Review report.csv. Rebuilt does not mean malware-free.')

    def open_output(self):
        folder = Path(self.output.get().strip()) if self.output.get().strip() else None
        if folder and folder.is_dir():
            os.startfile(str(folder))
        else:
            messagebox.showwarning('Missing folder', 'Output folder does not exist yet.')

    def close(self):
        if self.running:
            messagebox.showwarning('Still processing', 'Click Cancel and wait for cleanup to finish before closing.')
        else:
            self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    MediaRescueGUI(root)
    root.mainloop()
