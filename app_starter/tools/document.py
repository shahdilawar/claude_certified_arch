import os
from markitdown import MarkItDown, StreamInfo
from io import BytesIO
from pydantic import Field


def binary_document_to_markdown(binary_data: bytes, file_type: str) -> str:
    """Converts binary document data to markdown-formatted text."""
    md = MarkItDown()
    file_obj = BytesIO(binary_data)
    stream_info = StreamInfo(extension=file_type)
    result = md.convert(file_obj, stream_info=stream_info)
    return result.text_content


def document_path_to_markdown(
    path: str = Field(
        description="Absolute or relative path to a PDF or DOCX file to convert to markdown."
    ),
) -> str:
    """Reads a document file from disk and converts its contents to markdown.

    Given the path to a PDF or DOCX file, reads the file's binary contents
    and converts them to markdown-formatted text. The document type is
    inferred from the path's file extension.

    When to use:
    - When you have a path to a document on disk and need its content as
      markdown for reading, analysis, or summarization.

    When not to use:
    - When you already have the document as in-memory binary data — use
      `binary_document_to_markdown` directly instead.

    Examples:
    >>> document_path_to_markdown("/path/to/report.pdf")
    '# Report Title\\n\\nBody text...'
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"No such file: {path}")
    if os.path.isdir(path):
        raise IsADirectoryError(f"Path is a directory, not a file: {path}")

    extension = os.path.splitext(path)[1].lstrip(".").lower()
    if not extension:
        raise ValueError(f"Could not determine file type from path: {path}")

    with open(path, "rb") as f:
        binary_data = f.read()

    return binary_document_to_markdown(binary_data, extension)
