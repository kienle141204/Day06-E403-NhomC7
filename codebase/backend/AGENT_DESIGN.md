# MedChat Backend Agent Design

## Goal

Implement the updated prescription workflow with FastAPI, LangChain, and LangGraph while keeping the current frontend API contract stable.

The first production step is VLM prescription scanning:

1. User uploads an image of a prescription.
2. Backend validates the upload.
3. LangGraph calls an OpenAI vision model through LangChain.
4. The VLM extracts structured medication data.
5. FastAPI returns the same prescription shape the React app already renders.

## Architecture

FastAPI remains the public API layer. It owns request validation, CORS, in-memory demo storage, and HTTP errors.

LangGraph owns workflow orchestration. Each node is small and testable:

- `validate_upload`: checks image MIME type and size.
- `extract_with_vlm`: calls OpenAI vision through LangChain.
- `normalize_prescription`: converts extracted data into the frontend prescription contract.

LangChain owns model access. The first VLM provider is OpenAI `gpt-4o-mini`, configured with:

- `OPENAI_API_KEY`
- `OPENAI_VISION_MODEL`, optional, defaults to `gpt-4o-mini`
- `MAX_SCAN_UPLOAD_BYTES`, optional, defaults to 8 MB

## API Contract

`POST /prescriptions/scan` accepts `multipart/form-data` with field `file`.

Successful response:

```json
{
  "prescriptionId": "rx-...",
  "confidence": 0.86,
  "doctorName": "Unknown doctor",
  "clinic": "Unknown clinic",
  "issuedAt": "2026-06-04",
  "status": "pending",
  "medications": [
    {
      "id": "med-1",
      "name": "Paracetamol",
      "strength": "500mg",
      "dose": "1 tablet",
      "schedule": "Every 6 hours if needed",
      "duration": "3 days",
      "risk": "normal",
      "confidence": 0.9,
      "notes": "Extracted from prescription image. Confirm before use."
    }
  ],
  "warnings": []
}
```

Expected errors:

- `400`: no file was uploaded.
- `413`: file is larger than the configured limit.
- `422`: file is not a supported image or VLM cannot identify medication data.
- `503`: OpenAI API key is not configured.
- `502`: VLM request or JSON parsing failed.

## LangGraph State

The scan graph state contains:

- `file_name`
- `mime_type`
- `image_bytes`
- `image_base64`
- `vision_result`
- `prescription`
- `errors`

The graph returns a normalized prescription dictionary. FastAPI stores it in the existing in-memory `prescriptions` map and returns a deep copy.

## Roadmap

After image scan is stable:

1. Add user confirmation as a LangGraph state transition.
2. Add drug normalization against internal OCR medicine data.
3. Add DailyMed lookup for missing internal data.
4. Add interaction/risk scoring node.
5. Move medication Q&A from direct OpenAI calls into a separate LangGraph flow.
