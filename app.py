import re
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog

try:
    from deidentifier.anonymizer import anonymize_text_with_ollama
except ImportError as exc:
    anonymize_text_with_ollama = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

try:
    from deidentifier.pdf_reader import extract_text_from_pdf
except ImportError as exc:
    extract_text_from_pdf = None
    PDF_IMPORT_ERROR = exc
else:
    PDF_IMPORT_ERROR = None


DEFAULT_MODEL = "qwen2.5:7b-instruct"

SUGGESTED_MODELS = [
    "qwen2.5:7b-instruct",
    "qwen2.5:14b-instruct",
    "llama3.2:3b",
    "llama3.1:8b",
    "mistral:7b-instruct",
    "phi3.5:3.8b",
]

# Foreground and background colours for each PHI label tag
PHI_LABEL_COLOURS = {
    "NOMBRE":    ("#1D4ED8", "#DBEAFE"),
    "FECHA":     ("#065F46", "#D1FAE5"),
    "DIRECCIÓN": ("#92400E", "#FEF3C7"),
    "TELÉFONO":  ("#5B21B6", "#EDE9FE"),
    "EMAIL":     ("#0F766E", "#CCFBF1"),
    "DNI":       ("#991B1B", "#FEE2E2"),
}

PHI_PATTERN = re.compile(
    r"\[(NOMBRE|FECHA|DIRECCI[ÓO]N|TEL[ÉE]FONO|EMAIL|DNI)\]"
)

EXAMPLE_TEXT = """Patient name: John Smith
Date of birth: 03/12/1985
Address: 24 Green Street, Madrid
Phone: +34 612 345 678
Email: john.smith@example.com
Visit date: 04/20/2024
DNI: 12345678A

Clinical note:
The patient presents with abdominal pain, nausea and mild fever.
Past medical history includes Crohn's disease.
"""


class PHIDeidentifierApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PHI De-identification")
        self.root.geometry("1280x820")
        self.root.minsize(960, 640)

        self.is_processing = False
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        self.status_var = tk.StringVar(value="Ready — load or paste a clinical document to get started")
        self.force_ocr_var = tk.BooleanVar(value=False)

        self._configure_style()
        self._build_layout()
        self._bind_shortcuts()

    # ------------------------------------------------------------------ style

    def _configure_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TButton", font=("Segoe UI", 9), padding=(7, 4))
        style.configure("Primary.TButton",
                        font=("Segoe UI", 10, "bold"), padding=(12, 6))
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("Small.TLabel", font=("Segoe UI", 9), foreground="#6B7280")
        style.configure("TLabelframe.Label", font=("Segoe UI", 9, "bold"),
                        foreground="#374151")
        style.configure("TCombobox", font=("Segoe UI", 9))

    # ------------------------------------------------------------------ build

    def _build_layout(self):
        self._build_header()

        body = ttk.Frame(self.root, padding=(14, 8, 14, 6))
        body.pack(fill="both", expand=True)

        self._build_toolbar(body)
        ttk.Separator(body, orient="horizontal").pack(fill="x", pady=(8, 8))
        self._build_panels(body)
        self._build_status_bar(body)
        self._configure_phi_tags()

    def _build_header(self):
        bar = tk.Frame(self.root, bg="#1E3A5F", pady=11, padx=16)
        bar.pack(fill="x")

        tk.Label(
            bar,
            text="PHI De-identification",
            font=("Segoe UI", 16, "bold"),
            fg="white",
            bg="#1E3A5F",
        ).pack(side="left")

        tk.Label(
            bar,
            text="  |  Local LLM  ·  Regex support  ·  PDF / OCR",
            font=("Segoe UI", 10),
            fg="#93C5FD",
            bg="#1E3A5F",
        ).pack(side="left")

    def _build_toolbar(self, parent):
        bar = ttk.Frame(parent)
        bar.pack(fill="x")

        # ── Model ────────────────────────────────────────────────────────────
        model_grp = ttk.LabelFrame(bar, text="Model", padding=(8, 4))
        model_grp.pack(side="left", padx=(0, 10), fill="y")

        self.model_combo = ttk.Combobox(
            model_grp,
            textvariable=self.model_var,
            values=SUGGESTED_MODELS,
            width=27,
            state="normal",
        )
        self.model_combo.pack(side="left")

        # ── Input ────────────────────────────────────────────────────────────
        input_grp = ttk.LabelFrame(bar, text="Input", padding=(8, 4))
        input_grp.pack(side="left", padx=(0, 10), fill="y")

        ttk.Button(input_grp, text="Example",
                   command=self.load_example).pack(side="left", padx=(0, 4))
        ttk.Button(input_grp, text="Open TXT",
                   command=self.load_txt_file).pack(side="left", padx=(0, 4))
        ttk.Button(input_grp, text="Open PDF",
                   command=self.load_pdf_file).pack(side="left", padx=(0, 6))
        ttk.Checkbutton(input_grp, text="Force OCR",
                        variable=self.force_ocr_var).pack(side="left")

        # ── Process ──────────────────────────────────────────────────────────
        process_grp = ttk.LabelFrame(bar, text="Process", padding=(8, 4))
        process_grp.pack(side="left", padx=(0, 10), fill="y")

        self.anonymize_button = ttk.Button(
            process_grp,
            text="Anonymize   Ctrl+Enter",
            style="Primary.TButton",
            command=self.start_anonymization,
        )
        self.anonymize_button.pack(side="left")

        # ── Output ───────────────────────────────────────────────────────────
        output_grp = ttk.LabelFrame(bar, text="Output", padding=(8, 4))
        output_grp.pack(side="left", fill="y")

        ttk.Button(output_grp, text="Save",
                   command=self.save_result).pack(side="left", padx=(0, 4))
        ttk.Button(output_grp, text="Copy",
                   command=self.copy_result).pack(side="left", padx=(0, 4))
        ttk.Button(output_grp, text="Clear",
                   command=self.clear_texts).pack(side="left")

    def _build_panels(self, parent):
        paned = ttk.PanedWindow(parent, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # ── Left: input ───────────────────────────────────────────────────────
        left = ttk.LabelFrame(
            paned,
            text="Clinical text  (original / extracted PDF)",
            padding=4,
        )
        self.input_text = tk.Text(
            left,
            wrap="word",
            font=("Consolas", 10),
            undo=True,
            relief="flat",
            bg="white",
            fg="#111827",
            insertbackground="#1E3A5F",
            selectbackground="#BFDBFE",
            padx=6,
            pady=4,
        )
        input_sb = ttk.Scrollbar(left, orient="vertical",
                                 command=self.input_text.yview)
        self.input_text.configure(yscrollcommand=input_sb.set)
        self.input_text.grid(row=0, column=0, sticky="nsew")
        input_sb.grid(row=0, column=1, sticky="ns")
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        paned.add(left, weight=1)

        # ── Right: output ─────────────────────────────────────────────────────
        right = ttk.LabelFrame(
            paned,
            text="Anonymized text  (read-only — PHI labels are colour-coded)",
            padding=4,
        )
        self.output_text = tk.Text(
            right,
            wrap="word",
            font=("Consolas", 10),
            state="disabled",
            relief="flat",
            bg="#F8FAFC",
            fg="#111827",
            selectbackground="#BFDBFE",
            padx=6,
            pady=4,
        )
        output_sb = ttk.Scrollbar(right, orient="vertical",
                                  command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=output_sb.set)
        self.output_text.grid(row=0, column=0, sticky="nsew")
        output_sb.grid(row=0, column=1, sticky="ns")
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        paned.add(right, weight=1)

    def _configure_phi_tags(self):
        for label, (fg, bg) in PHI_LABEL_COLOURS.items():
            self.output_text.tag_configure(
                f"phi_{label}",
                foreground=fg,
                background=bg,
                font=("Consolas", 10, "bold"),
            )

    def _build_status_bar(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=(6, 0))

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(0, 5))

        inner = ttk.Frame(frame)
        inner.pack(fill="x")

        self.status_label = ttk.Label(
            inner,
            textvariable=self.status_var,
            style="Small.TLabel",
            anchor="w",
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        ttk.Label(inner, text="Local Ollama  ·  no external API",
                  style="Small.TLabel").pack(side="right")

        self.progress_bar = ttk.Progressbar(inner, mode="indeterminate", length=120)

    def _bind_shortcuts(self):
        self.root.bind("<Control-Return>", lambda _e: self.start_anonymization())
        self.root.bind("<Control-o>", lambda _e: self.load_txt_file())
        self.root.bind("<Control-s>", lambda _e: self.save_result())
        self.root.bind("<Control-l>", lambda _e: self.clear_texts())

    # --------------------------------------------------------------- helpers

    def _set_status(self, text: str):
        self.status_var.set(text)

    def _start_progress(self, message: str):
        self._set_status(message)
        self.anonymize_button.configure(state="disabled")
        self.is_processing = True
        self.progress_bar.pack(side="right", padx=(8, 0), before=self.status_label)
        self.progress_bar.start(12)

    def _stop_progress(self):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.anonymize_button.configure(state="normal")
        self.is_processing = False

    def _write_output(self, text: str):
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", text)
        self._apply_phi_highlighting()
        self.output_text.configure(state="disabled")

    def _apply_phi_highlighting(self):
        for label in PHI_LABEL_COLOURS:
            self.output_text.tag_remove(f"phi_{label}", "1.0", tk.END)

        content = self.output_text.get("1.0", tk.END)
        for match in PHI_PATTERN.finditer(content):
            raw_label = match.group(1)
            # Normalise accented variants back to canonical form
            label = raw_label.replace("CION", "CIÓN").replace("EFONO", "ÉFONO")
            tag = f"phi_{label}"
            if tag in [f"phi_{l}" for l in PHI_LABEL_COLOURS]:
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.output_text.tag_add(tag, start, end)

    def _count_phi_entities(self, text: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for match in PHI_PATTERN.finditer(text):
            raw = match.group(1)
            label = raw.replace("CION", "CIÓN").replace("EFONO", "ÉFONO")
            counts[label] = counts.get(label, 0) + 1
        return counts

    # ---------------------------------------------------------------- events

    def load_example(self):
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", EXAMPLE_TEXT)
        self._write_output("")
        self._set_status("Example loaded — press  Ctrl+Enter  to anonymize")

    def load_txt_file(self):
        path = filedialog.askopenfilename(
            title="Open TXT file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            try:
                text = Path(path).read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = Path(path).read_text(encoding="latin-1")
        except Exception as exc:
            messagebox.showerror(
                "TXT loading error",
                f"Could not load the TXT file.\n\nDetails:\n{exc}",
            )
            return

        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", text)
        self._write_output("")
        self._set_status(f"Loaded: {Path(path).name}  ({len(text):,} chars)")

    def load_pdf_file(self):
        if extract_text_from_pdf is None:
            messagebox.showerror(
                "PDF module missing",
                f"Could not import the PDF extraction module:\n\n{PDF_IMPORT_ERROR}",
            )
            return

        if self.is_processing:
            messagebox.showinfo("Busy", "The application is already processing a task.")
            return

        path = filedialog.askopenfilename(
            title="Open PDF file",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not path:
            return

        self._write_output("")
        self._start_progress("Extracting text from PDF…")

        threading.Thread(
            target=self._run_pdf_extraction,
            args=(path, self.force_ocr_var.get()),
            daemon=True,
        ).start()

    def _run_pdf_extraction(self, path: str, force_ocr: bool):
        try:
            result = extract_text_from_pdf(path, force_ocr=force_ocr)
        except Exception as exc:
            self.root.after(0, self._show_pdf_error, exc)
            return
        self.root.after(0, self._show_pdf_text, path, result)

    def _show_pdf_text(self, path: str, result):
        self._stop_progress()
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", result.text)

        chars = len(result.text.strip())
        self._set_status(
            f"PDF loaded: {Path(path).name}  ·  "
            f"method={result.method}  ·  pages={result.pages}  ·  {chars:,} chars"
        )

        if chars < 80:
            messagebox.showwarning(
                "Very little text extracted",
                "Only a few characters were found in this PDF.\n\n"
                "If the document is scanned or image-based, enable 'Force OCR' and reload it.",
            )

    def _show_pdf_error(self, exc: Exception):
        self._stop_progress()
        self._set_status("Error extracting PDF text")
        messagebox.showerror(
            "PDF extraction error",
            "The PDF text could not be extracted.\n\n"
            "For scanned PDFs, make sure Tesseract OCR is installed.\n\n"
            f"Details:\n{exc}",
        )

    def clear_texts(self):
        self.input_text.delete("1.0", tk.END)
        self._write_output("")
        self._set_status("Ready")

    def copy_result(self):
        result = self.output_text.get("1.0", tk.END).strip()
        if not result:
            messagebox.showinfo("Nothing to copy", "There is no anonymized text yet.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(result)
        self._set_status("Anonymized text copied to clipboard")

    def save_result(self):
        result = self.output_text.get("1.0", tk.END).strip()
        if not result:
            messagebox.showinfo("Nothing to save", "There is no anonymized text yet.")
            return

        path = filedialog.asksaveasfilename(
            title="Save anonymized text",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            Path(path).write_text(result, encoding="utf-8")
        except Exception as exc:
            messagebox.showerror("Save error",
                                 f"Could not save the file.\n\nDetails:\n{exc}")
            return

        self._set_status(f"Saved: {Path(path).name}")

    def start_anonymization(self):
        if self.is_processing:
            return

        if anonymize_text_with_ollama is None:
            messagebox.showerror(
                "Import error",
                f"Could not import the anonymization module:\n\n{IMPORT_ERROR}",
            )
            return

        text = self.input_text.get("1.0", tk.END).strip()
        model = self.model_var.get().strip()

        if not text:
            messagebox.showwarning("No text", "Please enter or load a clinical document first.")
            return

        if not model:
            messagebox.showwarning("No model", "Please select or enter an Ollama model name.")
            return

        self._write_output("")
        self._start_progress(f"Running local LLM ({model})…")

        threading.Thread(
            target=self._run_anonymization,
            args=(text, model),
            daemon=True,
        ).start()

    def _run_anonymization(self, text: str, model: str):
        try:
            anonymized = anonymize_text_with_ollama(text, model=model)
        except Exception as exc:
            self.root.after(0, self._show_error, exc)
            return
        self.root.after(0, self._show_result, anonymized)

    def _show_result(self, anonymized: str):
        self._write_output(anonymized)
        self._stop_progress()

        counts = self._count_phi_entities(anonymized)
        total = sum(counts.values())

        if total > 0:
            breakdown = "  ·  ".join(
                f"{label}: {n}" for label, n in sorted(counts.items())
            )
            self._set_status(f"Done — {total} PHI {'entity' if total == 1 else 'entities'} anonymized    {breakdown}")
        else:
            self._set_status("Done — no PHI entities detected in this document")

    def _show_error(self, exc: Exception):
        self._stop_progress()
        self._set_status("Error during anonymization")
        messagebox.showerror(
            "Anonymization error",
            "The text could not be anonymized.\n\n"
            "Check that Ollama is running and the selected model is available.\n\n"
            f"Details:\n{exc}",
        )


def main():
    root = tk.Tk()
    PHIDeidentifierApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
