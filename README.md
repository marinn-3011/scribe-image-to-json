# Scribe

Turn photos of receipts, invoices and business cards into clean, sorted JSON. Runs locally with [Gemma 4](https://ai.google.dev/gemma) through [Ollama](https://ollama.com), so your documents never leave your machine.

Built for the Hacktoberfest 2026 Open-Source AI Challenge (Side Hustle).

## Features

- **Batch scanning:** drop in many images and get one combined JSON file.
- **Custom schemas:** use a preset (receipt, invoice, business card), write your own `name: type` fields, or paste a full JSON Schema.
- **Auto-sort:** Scribe detects each document's type and files it into folders, with the original image next to its JSON. Download everything as a `.zip`.
- **Auto mode:** no schema needed, the model chooses the fields.
- **Exports:** copy the result, or save it as JSON or CSV.
- **No guessing:** fields the model can't see come back as `null`.

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com)
- Enough memory for your chosen model (roughly 12 GB free for `gemma4:e4b`)

## Setup

```bash
# 1. Get a model
ollama pull gemma4:e4b

# 2. Install dependencies
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Run
uvicorn app:app --reload
```

Open http://localhost:8000.

## Usage

1. Drop in photos or scans (JPG or PNG work best).
2. Choose a tab:
   - **Receipt, Invoice, Business card:** extract a fixed set of fields.
   - **Auto:** the model decides which fields matter.
   - **Auto-sort:** detect the type, extract, and file into folders.
   - **Custom:** define your own fields.
3. Pick a model and click **Extract**.
4. Copy or download the result.

### Custom schema example

```
vendor: string
date: date
total: number
items: list
```

Supported types: `string`, `number`, `integer`, `boolean`, `date`, `list`. You can also paste a complete JSON Schema.

### Sorted output

Auto-sort saves files next to `app.py`:

```
sorted/<batch>/receipt/lunch-a1b2c3.jpg
sorted/<batch>/receipt/lunch-a1b2c3.json
sorted/<batch>/invoice/...
sorted/<batch>/business_card/...
```

Each page load starts a new batch folder.

## Models

| Tag | Best for |
|---|---|
| `gemma4:e4b` | Fast default, runs on modest hardware |
| `gemma4:26b` | Better accuracy on messy documents |
| `gemma4:31b` | Highest quality, needs a strong machine |

To add a model, add an `<option>` to the model dropdown in `static/index.html`.

## How it works

For each image, `app.py`:

1. Resizes the image and fixes its orientation.
2. (Auto-sort only) asks Gemma 4 for a category, limited to a fixed list.
3. Asks Gemma 4 to extract the fields. The JSON Schema goes in Ollama's `format` field, so the output follows it.
4. (Auto-sort only) saves the original and its JSON into the category folder.

Requests use temperature 0 and an 8192-token context window.

## Customizing

- **New category:** add its name to `CATEGORIES` in `app.py`. To give it a schema, add an entry to the `schemas` object in the Auto-sort branch of `static/index.html`.
- **New preset:** add a schema to `PRESETS` in `static/index.html`.
- **Look and feel:** edit the CSS variables at the top of `static/index.html`.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Ollama is not running" | Start the Ollama app or run `ollama serve` |
| Model not found | Run `ollama list` and match the tag in the dropdown |
| Slow or crashing | Use a smaller model or close other heavy apps |
| Bad or empty fields | Use a sharper photo, or try a larger model |
| Upload fails on a phone photo | HEIC isn't supported, export as JPG or PNG |
| Port in use | `uvicorn app:app --port 8001` |

## Limitations

- Images only for now (no PDFs).
- Extraction is not perfect. Review important numbers before relying on them.
- Files are processed one at a time.
