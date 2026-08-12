from __future__ import annotations

import io
import re
from pathlib import Path

from src.models.schemas import ParsedDocument


class DocumentParseError(ValueError):
    pass


def _clean(text: str) -> str:
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    cleaned: list[str] = []
    for line in lines:
        if line or (cleaned and cleaned[-1]):
            cleaned.append(line)
    return "\n".join(cleaned).strip()


def parse_document(filename: str, content: bytes) -> ParsedDocument:
    suffix = Path(filename).suffix.lower()
    try:
        if suffix in {".txt", ".md", ".markdown"}:
            text = content.decode("utf-8-sig")
        elif suffix == ".docx":
            from docx import Document

            document = Document(io.BytesIO(content))
            text = "\n".join(p.text for p in document.paragraphs)
        elif suffix == ".pdf":
            import fitz

            with fitz.open(stream=content, filetype="pdf") as document:
                text = "\n".join(page.get_text("text") for page in document)
            if len(re.sub(r"\s", "", text)) < 30:
                raise DocumentParseError("PDF 未检测到足够的可复制文本，请改用可复制版 PDF、DOCX 或 TXT。")
        else:
            raise DocumentParseError(f"不支持的文件格式：{suffix or '无扩展名'}")
    except DocumentParseError:
        raise
    except UnicodeDecodeError as exc:
        raise DocumentParseError("文本文件不是 UTF-8 编码，请转换编码后重试。") from exc
    except Exception as exc:
        raise DocumentParseError(f"解析 {filename} 失败：{exc}") from exc

    text = _clean(text)
    if not text:
        raise DocumentParseError("文件中没有可分析的文本。")
    paragraphs = [line for line in text.splitlines() if line]
    return ParsedDocument(filename=filename, text=text, paragraphs=paragraphs, metadata={"format": suffix.lstrip(".")})
