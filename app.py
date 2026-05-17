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
        self.root.title("PHI De-identification App - Local LLM")
        self.root.geometry("1200x760")
        self.root.minsize(950, 620)

        self.is_processing = False
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        self.status_var = tk.StringVar(value="Ready")
        self.force_ocr_var = tk.BooleanVar(value=False)

        self._configure_style()
        self._build_layout()

    def _configure_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 10), padding=6)
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 17, "bold"))
        style.configure("Subheader.TLabel", font=("Segoe UI", 10))
        style.configure("Status.TLabel", font=("Segoe UI", 9))

    def _build_layout(self):
        main_frame = ttk.Frame(self.root, padding=16)
        main_frame.pack(fill="both", expand=True)

        header = ttk.Label(
            main_frame,
            text="PHI De-identification Desktop Application",
            style="Header.TLabel",
        )
        header.pack(anchor="w")

        subtitle = ttk.Label(
            main_frame,
            text=(
                "Local desktop app for replacing protected health information "
                "using Ollama, regex support and optional PDF/OCR extraction."
            ),
            style="Subheader.TLabel",
        )
        subtitle.pack(anchor="w", pady=(4, 14))

        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(controls_frame, text="Ollama model:").pack(side="left")

        model_entry = ttk.Entry(controls_frame, textvariable=self.model_var, width=30)
        model_entry.pack(side="left", padx=(8, 16))

        self.anonymize_button = ttk.Button(
            controls_frame,
            text="Anonymize text",
            command=self.start_anonymization,
        )
        self.anonymize_button.pack(side="left", padx=(0, 8))

        ttk.Button(
            controls_frame,
            text="Load example",
            command=self.load_example,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            controls_frame,
            text="Load TXT",
            command=self.load_txt_file,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            controls_frame,
            text="Load PDF",
            command=self.load_pdf_file,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            controls_frame,
            text="Save result",
            command=self.save_result,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            controls_frame,
            text="Clear",
            command=self.clear_texts,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            controls_frame,
            text="Copy result",
            command=self.copy_result,
        ).pack(side="left")

        options_frame = ttk.Frame(main_frame)
        options_frame.pack(fill="x", pady=(0, 12))

        ttk.Checkbutton(
            options_frame,
            text="Force OCR for PDF input",
            variable=self.force_ocr_var,
        ).pack(side="left")

        local_note = ttk.Label(
            options_frame,
            text="  LLM execution: local Ollama runtime, no external API",
            style="Status.TLabel",
        )
        local_note.pack(side="left", padx=(12, 0))

        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True)
        text_frame.columnconfigure(0, weight=1)
        text_frame.columnconfigure(1, weight=1)
        text_frame.rowconfigure(1, weight=1)

        ttk.Label(text_frame, text="Original clinical text / extracted PDF text").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 4)
        )
        ttk.Label(text_frame, text="Anonymized text").grid(
            row=0, column=1, sticky="w", padx=(8, 0), pady=(0, 4)
        )

        input_container = ttk.Frame(text_frame)
        input_container.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        input_container.rowconfigure(0, weight=1)
        input_container.columnconfigure(0, weight=1)

        output_container = ttk.Frame(text_frame)
        output_container.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        output_container.rowconfigure(0, weight=1)
        output_container.columnconfigure(0, weight=1)

        self.input_text = tk.Text(
            input_container,
            wrap="word",
            font=("Consolas", 10),
            undo=True,
        )
        self.input_text.grid(row=0, column=0, sticky="nsew")

        input_scrollbar = ttk.Scrollbar(
            input_container,
            orient="vertical",
            command=self.input_text.yview,
        )
        input_scrollbar.grid(row=0, column=1, sticky="ns")
        self.input_text.configure(yscrollcommand=input_scrollbar.set)

        self.output_text = tk.Text(
            output_container,
            wrap="word",
            font=("Consolas", 10),
            undo=True,
        )
        self.output_text.grid(row=0, column=0, sticky="nsew")

        output_scrollbar = ttk.Scrollbar(
            output_container,
            orient="vertical",
            command=self.output_text.yview,
        )
        output_scrollbar.grid(row=0, column=1, sticky="ns")
        self.output_text.configure(yscrollcommand=output_scrollbar.set)

        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            style="Status.TLabel",
            anchor="w",
        )
        status_bar.pack(fill="x", pady=(12, 0))

    def load_example(self):
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", EXAMPLE_TEXT)
        self.output_text.delete("1.0", tk.END)
        self.status_var.set("Example loaded")

    def load_txt_file(self):
        file_path = filedialog.askopenfilename(
            title="Select TXT file",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )

        if not file_path:
            return

        try:
            try:
                text = Path(file_path).read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = Path(file_path).read_text(encoding="latin-1")
        except Exception as exc:
            messagebox.showerror(
                "TXT loading error",
                f"The TXT file could not be loaded.\n\nError details:\n{exc}",
            )
            return

        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", text)
        self.output_text.delete("1.0", tk.END)
        self.status_var.set(f"TXT loaded: {Path(file_path).name}")

    def load_pdf_file(self):
        if extract_text_from_pdf is None:
            messagebox.showerror(
                "PDF import error",
                f"Could not import the PDF extraction module:\n\n{PDF_IMPORT_ERROR}",
            )
            return

        if self.is_processing:
            messagebox.showinfo(
                "Busy",
                "The application is already processing a task.",
            )
            return

        file_path = filedialog.askopenfilename(
            title="Select PDF file",
            filetypes=[
                ("PDF files", "*.pdf"),
                ("All files", "*.*"),
            ],
        )

        if not file_path:
            return

        self.is_processing = True
        self.anonymize_button.configure(state="disabled")
        self.input_text.delete("1.0", tk.END)
        self.output_text.delete("1.0", tk.END)
        self.status_var.set("Extracting text from PDF...")

        worker = threading.Thread(
            target=self._run_pdf_extraction,
            args=(file_path, self.force_ocr_var.get()),
            daemon=True,
        )
        worker.start()

    def _run_pdf_extraction(self, file_path: str, force_ocr: bool):
        try:
            result = extract_text_from_pdf(
                file_path,
                force_ocr=force_ocr,
            )
        except Exception as exc:
            self.root.after(0, self._show_pdf_error, exc)
            return

        self.root.after(0, self._show_pdf_text, file_path, result)

    def _show_pdf_text(self, file_path: str, result):
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", result.text)
        self.output_text.delete("1.0", tk.END)

        text_length = len(result.text.strip())

        self.status_var.set(
            f"PDF loaded: {Path(file_path).name} | "
            f"method={result.method} | pages={result.pages} | chars={text_length}"
        )

        if text_length < 80:
            messagebox.showwarning(
                "Low text extraction",
                "Very little text was extracted from this PDF.\n\n"
                "If the document is scanned or image-based, enable 'Force OCR for PDF input' "
                "and try loading the PDF again.",
            )

        self.anonymize_button.configure(state="normal")
        self.is_processing = False

    def _show_pdf_error(self, exc: Exception):
        self.status_var.set("Error extracting PDF text")
        self.anonymize_button.configure(state="normal")
        self.is_processing = False

        messagebox.showerror(
            "PDF extraction error",
            "The PDF text could not be extracted.\n\n"
            "If this is a scanned PDF, make sure Tesseract OCR is installed.\n\n"
            f"Error details:\n{exc}",
        )

    def clear_texts(self):
        self.input_text.delete("1.0", tk.END)
        self.output_text.delete("1.0", tk.END)
        self.status_var.set("Ready")

    def copy_result(self):
        result = self.output_text.get("1.0", tk.END).strip()
        if not result:
            messagebox.showinfo("Copy result", "There is no anonymized text to copy.")
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(result)
        self.status_var.set("Anonymized text copied to clipboard")

    def save_result(self):
        result = self.output_text.get("1.0", tk.END).strip()

        if not result:
            messagebox.showinfo("Save result", "There is no anonymized text to save.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Save anonymized text",
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )

        if not file_path:
            return

        try:
            Path(file_path).write_text(result, encoding="utf-8")
        except Exception as exc:
            messagebox.showerror(
                "Save error",
                f"The result could not be saved.\n\nError details:\n{exc}",
            )
            return

        self.status_var.set(f"Result saved: {Path(file_path).name}")

    def start_anonymization(self):
        if self.is_processing:
            return

        if anonymize_text_with_ollama is None:
            messagebox.showerror(
                "Import error",
                f"Could not import the anonymization pipeline:\n\n{IMPORT_ERROR}",
            )
            return

        original_text = self.input_text.get("1.0", tk.END).strip()
        model = self.model_var.get().strip()

        if not original_text:
            messagebox.showwarning("Missing text", "Please enter or load clinical text first.")
            return

        if not model:
            messagebox.showwarning("Missing model", "Please enter an Ollama model name.")
            return

        self.is_processing = True
        self.anonymize_button.configure(state="disabled")
        self.output_text.delete("1.0", tk.END)
        self.status_var.set("Processing with local LLM...")

        worker = threading.Thread(
            target=self._run_anonymization,
            args=(original_text, model),
            daemon=True,
        )
        worker.start()

    def _run_anonymization(self, original_text: str, model: str):
        try:
            anonymized_text = anonymize_text_with_ollama(original_text, model=model)
        except Exception as exc:
            self.root.after(0, self._show_error, exc)
            return

        self.root.after(0, self._show_result, anonymized_text)

    def _show_result(self, anonymized_text: str):
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", anonymized_text)
        self.status_var.set("Anonymization completed")
        self.anonymize_button.configure(state="normal")
        self.is_processing = False

    def _show_error(self, exc: Exception):
        self.status_var.set("Error during anonymization")
        self.anonymize_button.configure(state="normal")
        self.is_processing = False

        messagebox.showerror(
            "Anonymization error",
            "The text could not be anonymized.\n\n"
            "Check that Ollama is installed, running, and that the selected model is available.\n\n"
            f"Error details:\n{exc}",
        )


def main():
    root = tk.Tk()
    PHIDeidentifierApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
