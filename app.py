import base64, io, json, pathlib, re, shutil, uuid
import httpx
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps

OLLAMA = "http://localhost:11434"
SORTED = pathlib.Path("sorted")  # sorted/<batch>/<category>/ holds originals + JSON
CATEGORIES = ["receipt", "invoice", "business_card", "letter", "form", "other"]
app = FastAPI()

SYSTEM = (
    "You read photos and scans of documents and return structured data as JSON. "
    "Copy values exactly as printed. If a field is not visible, use null. Never guess."
)
AUTO_PROMPT = (
    "Extract every useful field from this document as JSON. Use snake_case keys and "
    "include a document_type field. Use ISO dates (YYYY-MM-DD) and plain numbers for amounts."
)
CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {"category": {"type": "string", "enum": CATEGORIES}},
    "required": ["category"],
}


def prep(raw: bytes) -> str:
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    img.thumbnail((1600, 1600))  # keeps text readable, keeps inference fast
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()


async def ask(client, model, image, prompt, fmt):
    payload = {
        "model": model,
        "stream": False,
        "think": False,
        "format": fmt,
        "options": {"temperature": 0, "num_ctx": 8192},
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt, "images": [image]},
        ],
    }
    try:
        r = await client.post(f"{OLLAMA}/api/chat", json=payload)
        r.raise_for_status()
    except httpx.ConnectError:
        raise HTTPException(503, "Ollama is not running. Start it, then try again.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(502, f"Ollama error: {e.response.text[:200]}")
    try:
        return json.loads(r.json()["message"]["content"])
    except Exception:
        raise HTTPException(422, "The model returned invalid JSON. Try again or use a larger model.")


def safe(name: str) -> str:
    return re.sub(r"\W", "", name) or "default"


@app.post("/api/extract")
async def extract(
    file: UploadFile = File(...),
    model: str = Form("gemma4:e4b"),
    schema: str = Form(""),
    sort: str = Form(""),
    schemas: str = Form(""),
    batch: str = Form(""),
):
    raw = await file.read()
    try:
        image = prep(raw)
    except Exception:
        raise HTTPException(400, "Could not read this file as an image.")

    async with httpx.AsyncClient(timeout=600) as client:
        category = None
        if sort:  # Decide what the document is
            found = await ask(client, model, image, "What kind of document is this? Pick the best category.", CLASSIFY_SCHEMA)
            category = found.get("category", "other")
            schema_obj = json.loads(schemas or "{}").get(category)
        else:
            schema_obj = json.loads(schema) if schema else None
        # Identify and pull out the fields (known types use their schema, others use auto mode)
        prompt = "Extract the data from this document." if schema_obj else AUTO_PROMPT
        data = await ask(client, model, image, prompt, schema_obj or "json")

    if category:  # Sort and file it away
        folder = SORTED / safe(batch) / category
        folder.mkdir(parents=True, exist_ok=True)
        base = pathlib.Path(file.filename or "scan")
        stem = f"{safe(base.stem)}-{uuid.uuid4().hex[:6]}"
        (folder / f"{stem}{base.suffix or '.jpg'}").write_bytes(raw)
        (folder / f"{stem}.json").write_text(json.dumps(data, indent=2))
    return {"category": category, "data": data}


@app.get("/api/zip/{batch}")
def zip_batch(batch: str):
    folder = SORTED / safe(batch)
    if not folder.exists():
        raise HTTPException(404, "Nothing sorted yet.")
    archive = shutil.make_archive(str(SORTED / f"{folder.name}-export"), "zip", folder)
    return FileResponse(archive, filename="scribe-sorted.zip")


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")
