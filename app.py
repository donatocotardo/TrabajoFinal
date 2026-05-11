import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

try:
    from deidentifier.anonymizer import anonymize_text_with_ollama
except ImportError as exc:
    anonymize_text_with_ollama = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


DEFAULT_MODEL = "qwen2.5:7b-instruct"

EXAMPLE_TEXT = """Patient name: John Smith
Date of birth: 03/12/1985
Address: 24 Green Street, Madrid
Phone: +34 612 345 678
Email: john.smith@example.com
Visit date: 04/20/2024

Clinical note:
The patient presents with abdominal pain, nausea and mild fever.
Past medical history includes Crohn's disease.
"""


class PHIDeidentifierApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PHI De-identification App - Local LLM")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)

        self.is_processing = False
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        self.status_var = tk.StringVar(value="Ready")

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
            text="Replace protected health information with standardized labels using a local LLM through Ollama.",
            style="Subheader.TLabel",
        )
        subtitle.pack(anchor="w", pady=(4, 14))

        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill="x", pady=(0, 12))

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

        if PDF_SUPPORT:
            ttk.Button(
                controls_frame,
                text="Load PDF",
                command=self.load_pdf,
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

        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True)
        text_frame.columnconfigure(0, weight=1)
        text_frame.columnconfigure(1, weight=1)
        text_frame.rowconfigure(1, weight=1)

        ttk.Label(text_frame, text="Original clinical text").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 4)
        )
        ttk.Label(text_frame, text="Anonymized text").grid(
            row=0, column=1, sticky="w", padx=(8, 0), pady=(0, 4)
        )

        self.input_text = tk.Text(
            text_frame,
            wrap="word",
            font=("Consolas", 10),
            undo=True,
            height=24,
        )
        self.input_text.grid(row=1, column=0, sticky="nsew", padx=(0, 8))

        self.output_text = tk.Text(
            text_frame,
            wrap="word",
            font=("Consolas", 10),
            undo=True,
            height=24,
        )
        self.output_text.grid(row=1, column=1, sticky="nsew", padx=(8, 0))

        input_scrollbar = ttk.Scrollbar(
            text_frame,
            orient="vertical",
            command=self.input_text.yview,
        )
        input_scrollbar.grid(row=1, column=0, sticky="nse", padx=(0, 8))
        self.input_text.configure(yscrollcommand=input_scrollbar.set)

        output_scrollbar = ttk.Scrollbar(
            text_frame,
            orient="vertical",
            command=self.output_text.yview,
        )
        output_scrollbar.grid(row=1, column=1, sticky="nse")
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

    def load_pdf(self):
        """Open file dialog and load PDF text into input area."""
        if not PDF_SUPPORT:
            messagebox.showerror(
                "PDF support not available",
                "pdfplumber is not installed. Install it with:\npip install pdfplumber"
            )
            return

        file_path = filedialog.askopenfilename(
            title="Select PDF file",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )

        if not file_path:
            return

        try:
            extracted_text = self._extract_text_from_pdf(file_path)
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", extracted_text)
            self.output_text.delete("1.0", tk.END)
            self.status_var.set(f"PDF loaded: {Path(file_path).name}")
        except Exception as exc:
            messagebox.showerror(
                "Error loading PDF",
                f"Could not load PDF file:\n\n{exc}"
            )
            self.status_var.set("Error loading PDF")

    @staticmethod
    def _extract_text_from_pdf(file_path: str) -> str:
        """Extract all text from a PDF file using pdfplumber."""
        extracted_text = []

        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    extracted_text.append(f"--- Page {i} ---\n{text}\n")

        if not extracted_text:
            raise ValueError("No text could be extracted from the PDF.")

        return "\n".join(extracted_text)

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
            messagebox.showwarning("Missing text", "Please enter a clinical text first.")
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
    app = PHIDeidentifierApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
