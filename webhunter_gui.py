#!/usr/bin/python
# -*- coding: utf-8 -*-
"""WebHunter GUI — Windows 11 desktop app that wraps webhunter.py."""

import sys
import os
import threading
import queue

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from webhunter import GoogleSE, BingSE, BasePlugin, all_plugins

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class _Redirect:
    """Capture print() output from worker thread into a queue."""
    def __init__(self, q):
        self._q = q

    def write(self, text):
        if text and text.strip():
            self._q.put(("output", text))

    def flush(self):
        pass


class WebHunterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WebHunter")
        self.geometry("1000x680")
        self.minsize(740, 520)
        self._q = queue.Queue()
        self._thread = None
        self._build_ui()

    # ──────────────────────── UI ────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Domain row
        top = ctk.CTkFrame(self, corner_radius=8)
        top.grid(row=0, column=0, padx=16, pady=(16, 6), sticky="ew")
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top, text="Domain:", width=70, anchor="w").grid(
            row=0, column=0, padx=(12, 4), pady=10)
        self.domain_entry = ctk.CTkEntry(top, placeholder_text="example.com")
        self.domain_entry.grid(row=0, column=1, padx=4, pady=10, sticky="ew")
        self.domain_entry.bind("<Return>", lambda _: self._toggle())
        self.start_btn = ctk.CTkButton(top, text="Hunt", width=90, command=self._toggle)
        self.start_btn.grid(row=0, column=2, padx=(4, 12), pady=10)

        # Options row
        opts = ctk.CTkFrame(self, corner_radius=8)
        opts.grid(row=1, column=0, padx=16, pady=6, sticky="ew")

        ctk.CTkLabel(opts, text="Targets:", width=70, anchor="w").grid(
            row=0, column=0, padx=(12, 4), pady=8)
        self.url_var = tk.BooleanVar(value=True)
        self.sub_var = tk.BooleanVar(value=True)
        self.email_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(opts, text="URLs", variable=self.url_var).grid(row=0, column=1, padx=8)
        ctk.CTkCheckBox(opts, text="Subdomains", variable=self.sub_var).grid(row=0, column=2, padx=8)
        ctk.CTkCheckBox(opts, text="Emails", variable=self.email_var).grid(row=0, column=3, padx=8)

        ctk.CTkLabel(opts, text="Plugins:", width=70, anchor="w").grid(
            row=0, column=4, padx=(28, 4))
        self.plugin_var = tk.StringVar(value="all")
        for col, (val, label) in enumerate(
                [("all", "All"), ("google", "Google"), ("bing", "Bing")], start=5):
            ctk.CTkRadioButton(opts, text=label, variable=self.plugin_var,
                               value=val).grid(row=0, column=col, padx=8)

        # Progress bar
        self.progress = ctk.CTkProgressBar(self)
        self.progress.grid(row=2, column=0, padx=16, pady=(4, 0), sticky="ew")
        self.progress.set(0)

        # Output frame
        out_frame = ctk.CTkFrame(self, corner_radius=8)
        out_frame.grid(row=3, column=0, padx=16, pady=(8, 4), sticky="nsew")
        out_frame.grid_columnconfigure(0, weight=1)
        out_frame.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(out_frame, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        toolbar.grid_columnconfigure(0, weight=1)
        self.result_label = ctk.CTkLabel(toolbar, text="Results", anchor="w")
        self.result_label.grid(row=0, column=0, sticky="w")
        ctk.CTkButton(toolbar, text="Clear", width=70,
                      fg_color="transparent", border_width=1,
                      command=self._clear).grid(row=0, column=1, padx=(0, 6))
        ctk.CTkButton(toolbar, text="Export…", width=80,
                      command=self._export).grid(row=0, column=2)

        self.output = ctk.CTkTextbox(out_frame, wrap="none", font=("Consolas", 12))
        self.output.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 8))

        # Status bar
        self.status = ctk.CTkLabel(self, text="Ready", anchor="w",
                                   text_color="gray", font=("", 11))
        self.status.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="w")

    # ──────────────────────── hunt control ────────────────────────

    def _toggle(self):
        if self._thread and self._thread.is_alive():
            return
        domain = self.domain_entry.get().strip()
        if not domain:
            messagebox.showwarning("WebHunter", "Enter a domain first.")
            return
        if not any([self.url_var.get(), self.sub_var.get(), self.email_var.get()]):
            messagebox.showwarning("WebHunter", "Select at least one target.")
            return

        self.output.delete("1.0", "end")
        self.result_label.configure(text="Results")
        self.status.configure(text="Hunting…", text_color="gray")
        self.start_btn.configure(state="disabled")
        self.progress.configure(mode="indeterminate")
        self.progress.start()

        self._thread = threading.Thread(
            target=self._worker,
            args=(domain, self.url_var.get(), self.sub_var.get(),
                  self.email_var.get(), self.plugin_var.get()),
            daemon=True,
        )
        self._thread.start()
        self.after(100, self._poll)

    def _worker(self, domain, hunt_url, hunt_sub, hunt_email, plugin_choice):
        old_out = sys.stdout
        sys.stdout = _Redirect(self._q)
        try:
            chosen = {k: v for k, v in all_plugins.items()
                      if plugin_choice == "all" or k == plugin_choice}

            plugins = []
            for pid, klass in chosen.items():
                p = klass(domain, {}, hunt_url=hunt_url,
                          hunt_subdomain=hunt_sub, hunt_email=hunt_email)
                p.start()
                plugins.append(p)

            for p in plugins:
                p.join()

            all_rr = {}
            for p in plugins:
                for k, v in p.rr.items():
                    all_rr.setdefault(k, []).extend(v)

            for k, v in all_rr.items():
                getattr(BasePlugin, "pprint_%s" % k)(v)

            total = sum(len(v) for v in all_rr.values())
            self._q.put(("done", f"Done — {total} result(s) found."))
        except Exception as exc:
            self._q.put(("error", str(exc)))
        finally:
            sys.stdout = old_out

    def _poll(self):
        try:
            while True:
                kind, payload = self._q.get_nowait()
                if kind == "output":
                    self.output.insert("end", payload + "\n")
                    self.output.see("end")
                elif kind == "done":
                    self._finish(payload, error=False)
                    return
                elif kind == "error":
                    self._finish(payload, error=True)
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _finish(self, msg, error=False):
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress.set(0 if error else 1)
        self.status.configure(text=msg, text_color="red" if error else "gray")
        self.start_btn.configure(state="normal")

    # ──────────────────────── toolbar actions ────────────────────────

    def _clear(self):
        self.output.delete("1.0", "end")
        self.progress.set(0)
        self.status.configure(text="Ready", text_color="gray")

    def _export(self):
        content = self.output.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("WebHunter", "Nothing to export yet.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Export results",
        )
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            self.status.configure(text=f"Exported → {path}", text_color="gray")


if __name__ == "__main__":
    app = WebHunterApp()
    app.mainloop()
