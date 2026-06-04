"""LangGraph: Prescription Scan — validate image → OCR → normalize."""
from typing import Any, TypedDict

from fastapi import UploadFile
from langgraph.graph import END, START, StateGraph

from ..schemas import VisionPrescriptionResult
from ..nodes.validate_upload import validate_upload
from ..nodes.extract_with_vlm import extract_with_vlm
from ..nodes.normalize_prescription import normalize_prescription


class ScanState(TypedDict, total=False):
    file_name: str
    mime_type: str
    image_bytes: bytes
    image_base64: str
    vision_result: VisionPrescriptionResult
    prescription: dict[str, Any]
    errors: list[str]


def build_scan_graph():
    graph = StateGraph(ScanState)
    graph.add_node("validate_upload", validate_upload)
    graph.add_node("extract_with_vlm", extract_with_vlm)
    graph.add_node("normalize_prescription", normalize_prescription)

    graph.add_edge(START, "validate_upload")
    graph.add_edge("validate_upload", "extract_with_vlm")
    graph.add_edge("extract_with_vlm", "normalize_prescription")
    graph.add_edge("normalize_prescription", END)
    return graph.compile()


scan_graph = build_scan_graph()


async def scan_prescription_upload(file: UploadFile) -> dict[str, Any]:
    """Entry point called by FastAPI — invoke scan_graph and return prescription dict."""
    content = await file.read()
    state = await scan_graph.ainvoke({
        "file_name": file.filename or "upload",
        "mime_type": file.content_type or "",
        "image_bytes": content,
        "errors": [],
    })
    return state["prescription"]
