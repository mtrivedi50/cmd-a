from enum import StrEnum


# SUPPORTED INPUT FORMATS
# https://github.com/docling-project/docling/blob/cc453961a9196c79f6428305b9007402e448f300/docling/datamodel/base_models.py#L34
class InputFormat(StrEnum):
    """A document format supported by document backend parsers."""

    DOCX = "docx"
    PPTX = "pptx"
    HTML = "html"
    IMAGE = "image"
    PDF = "pdf"
    ASCIIDOC = "asciidoc"
    MD = "md"
    CSV = "csv"
    XLSX = "xlsx"
    XML_USPTO = "xml_uspto"
    XML_JATS = "xml_jats"
    JSON_DOCLING = "json_docling"
    AUDIO = "audio"


SUPPORTED_INPUT_FORMATS = [
    InputFormat.PDF,
    InputFormat.IMAGE,
    InputFormat.DOCX,
    InputFormat.HTML,
    InputFormat.PPTX,
    InputFormat.ASCIIDOC,
    InputFormat.CSV,
    InputFormat.MD,
]
