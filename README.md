# ANONYMOUS — Sistema anonimizador de datos de pacientes

Proyecto final de la asignatura **Bioinformática y Medicina** del **Grado en Inteligencia Artificial** de la **Universidade da Coruña (UDC)**.

- **Zenodo DOI:** 10.5281/zenodo.20284534
- **Presentación:** [URL](https://udcgal-my.sharepoint.com/:p:/g/personal/david_vaamonde_estevez_udc_es/IQCr3YiFSky8RLfabQIe_V15AThpFxijCT_0jd7PjEud72Q?e=uN2T4s)

## Autores

Proyecto desarrollado por:

- Martín Barros Iglesias
- Donato José Cotardo Valcárcel
- David Vaamonde Estévez

---

## Descripción

Aplicación de escritorio en Python que detecta y anonimiza información sanitaria protegida (PHI) en textos clínicos en lenguaje libre. Utiliza un modelo de lenguaje local ejecutado a través de **Ollama**, sin enviar ningún dato a APIs externas.

Las entidades identificadas se sustituyen por etiquetas:

`[NOMBRE]` `[DIRECCIÓN]` `[TELÉFONO]` `[EMAIL]` `[FECHA]` `[DNI]`

El resto del contenido clínico (diagnósticos, síntomas, tratamientos) no se modifica.

### Arquitectura

El sistema combina dos capas de detección:

- **LLM local (Ollama):** detecta entidades en contexto natural, abreviaciones y texto libre ambiguo.
- **Regex determinista:** refuerza la detección de patrones estructurados (emails, fechas, DNI español, teléfonos) donde el LLM puede ser menos fiable.

---

## Requisitos del sistema

### 1. Ollama

Ollama es el motor que ejecuta los modelos de lenguaje localmente.

- Descarga e instala desde [ollama.com](https://ollama.com)
- Una vez instalado, descarga el modelo por defecto:

```bash
ollama pull qwen2.5:7b-instruct
```

### 2. Tesseract OCR *(opcional — solo para PDFs escaneados)*

Necesario únicamente si se quiere procesar PDFs que no contienen texto seleccionable (documentos escaneados).

**Windows** — instalador oficial (recomendado, incluye los idiomas automáticamente):

Descarga y ejecuta el instalador desde [github.com/UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki). Durante la instalación, marca **"Additional language data > English"**(O el idioma que desees). Instala en la ruta por defecto (`C:\Program Files\Tesseract-OCR\`), que la aplicación detecta automáticamente.

**Windows** — si ya tienes Tesseract instalado via Scoop:

Scoop no incluye los archivos de idioma. Ejecuta este comando en PowerShell para descargarlos:

```powershell
Invoke-WebRequest -Uri "https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata" -OutFile "$env:USERPROFILE\scoop\persist\tesseract\tessdata\eng.traineddata"
```

**Linux:**

```bash
sudo apt install tesseract-ocr tesseract-ocr-eng
```

**macOS:**

```bash
brew install tesseract
```

### 3. Python 3.9 o superior

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/<usuario>/TrabajoFinal.git
cd TrabajoFinal

# 2. Crear entorno virtual
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

# 3. Instalar dependencias Python
pip install -r requirements.txt
```

---

## Ejecución

Asegúrate de que Ollama está en ejecución antes de lanzar la aplicación:

```bash
ollama serve   # si no está ya corriendo como servicio
```

Luego, desde la raíz del repositorio:

```bash
python app.py
```

---

## Uso de la aplicación

1. Selecciona el modelo Ollama en el desplegable superior (por defecto `qwen2.5:7b-instruct`).
2. Carga un texto clínico de alguna de estas formas:
   - **Example** — carga un ejemplo de demostración.
   - **Open TXT** — abre un archivo de texto plano.
   - **Open PDF** — extrae el texto de un PDF (activa *Force OCR* para documentos escaneados).
   - O pega el texto directamente en el panel izquierdo.
3. Pulsa **Anonymize** (o `Ctrl+Enter`).
4. El panel derecho muestra el texto anonimizado con las etiquetas PHI resaltadas en color.
5. Usa **Save** o **Copy** para exportar el resultado.

---

## Evaluación

El proyecto incluye un pipeline de evaluación con un dataset sintético generado con la librería [Faker](https://faker.readthedocs.io/en/master/). Los resultados sobre 35 ejemplos y 175 entidades esperadas:

| Métrica | Resultado |
|---|---|
| Precision | 97.22 % |
| Recall | 100.00 % |
| F1-score | 98.59 % |

Para reproducir la evaluación:

```bash
# Generar el dataset sintético
python scripts/generate_evaluation_dataset.py

# Ejecutar la evaluación con Ollama
python scripts/evaluate_ollama.py

# Analizar y exportar los resultados
python scripts/analyze_evaluation_results.py
```

---

## Estructura del repositorio

```
TrabajoFinal/
├── app.py                          # Interfaz gráfica (tkinter)
├── requirements.txt
├── deidentifier/
│   ├── llm_detector.py             # Detección con LLM local (Ollama)
│   ├── regex_detector.py           # Detección determinista con expresiones regulares
│   ├── hybrid_detector.py          # Pipeline híbrido LLM + regex
│   ├── anonymizer.py               # Sustitución de entidades por etiquetas
│   └── pdf_reader.py               # Extracción de texto de PDFs (pypdf + OCR)
├── scripts/
│   ├── generate_evaluation_dataset.py
│   ├── evaluate_ollama.py
│   └── analyze_evaluation_results.py
└── results/
    └── evaluation/                 # Métricas y reportes generados
```

---
