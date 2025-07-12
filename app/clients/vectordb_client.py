import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from llama_index.core import Document
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from pinecone import Pinecone, PineconeAsyncio, Vector
from pinecone.db_data import Index as PineconeIndex
from pinecone.db_data import IndexAsyncio as PineconeIndexAsyncio
from pydantic import BaseModel

from app.clients.k8s_client import KubernetesOperator
from app.db.factory import Database
from app.db.models.choices import IntegrationType
from app.db.models.integration import UpsertedVector
from app.processors.constants import SUPPORTED_INPUT_FORMATS
from app.settings import Settings

# Logging
logging.basicConfig()
logger = logging.getLogger(__name__)


# Constants
EMBED_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
UPSERT_BATCH_SIZE = 200


# Database — we don't use the Singleton here, because this channel processor is run
# *outside* the FastAPI context. Therefore, the container resources are never
# initialized.
db = Database(db_url=Settings.get_db_uri())


class VectorMetadata(BaseModel):
    id: str
    source: IntegrationType
    integration_id: str
    display_name: str


class VectorDb(KubernetesOperator):
    """
    Vector database class that:
        - Uses Docling to OCR and chunk PDFs, Microsoft Office docs, etc.
        - Converts documents into embeddings and upserts to Pinecone
    """

    pc: Pinecone
    async_pc: PineconeAsyncio
    index: PineconeIndex
    async_index: PineconeIndexAsyncio

    def __init__(self, pc: Pinecone, async_pc: PineconeAsyncio):
        super().__init__()
        self.pc = pc
        self.async_pc = async_pc
        self.index = self.pc.Index(host=Settings.PINECONE.INDEX_HOST)
        self.async_index = self.async_pc.IndexAsyncio(host=Settings.PINECONE.INDEX_HOST)

    def upsert_chunk_vectors(
        self, chunks: list[str], metadata: dict[str, Any], parent_group_id: str
    ) -> list[Vector]:
        vectors: list[Vector] = []
        for idx, chunk in enumerate(chunks):
            embeddings = self.pc.inference.embed(
                model=Settings.PINECONE.INDEX_MODEL,
                inputs=[chunk],
                parameters={"input_type": "passage", "truncate": "END"},
            )
            vectors.append(
                Vector(
                    id=f"{metadata["id"]}-chunk{idx}",
                    values=embeddings.data[0]["values"],
                    metadata=metadata,
                )
            )

            # Try adding the upserted vector to our database. Note that if it
            # already exists (`vector_id` already exists), this will fail.
            try:
                db.add(
                    db_object=UpsertedVector(
                        vector_id=f"{metadata["id"]}-chunk{idx}",
                        parent_group_id=str(parent_group_id),
                    )
                )
            except Exception as e:
                logger.error(
                    f"Failed to add vector to database with error {e}. Skipping..."
                )
                pass
        return vectors

    def process_text(
        self, namespace: str, text: str, metadata: dict[str, Any], parent_group_id: str
    ):
        """Process text using a LlamaIndex's SentenceSplitter and upsert to our vector
        database."""
        splitter = SentenceSplitter(
            chunk_size=1024,
            chunk_overlap=20,
        )
        chunks = splitter.split_text(text)
        vectors = self.upsert_chunk_vectors(chunks, metadata, parent_group_id)
        self.index.upsert(
            vectors,
            namespace=namespace,
            batch_size=UPSERT_BATCH_SIZE,
        )

    def process_markdown_text(
        self,
        namespace: str,
        text_md: str,
        metadata: dict[str, str],
        parent_group_id: str,
    ):
        """Process Markdown using a LlamaIndex's SentenceSplitter and upsert to our
        vector database."""
        splitter = MarkdownNodeParser(include_metadata=True)
        nodes = splitter.get_nodes_from_documents(documents=[Document(text=text_md)])
        vectors: list[Vector] = []

        # If there are no nodes but there is content, then the text does not have a
        # markdown structure.
        if not nodes and text_md:
            self.process_text(namespace, text_md, metadata, parent_group_id)
        else:
            nodes_txt = [node.get_content() for node in nodes]
            vectors = self.upsert_chunk_vectors(nodes_txt, metadata, parent_group_id)
            self.index.upsert(
                vectors,
                namespace=namespace,
                batch_size=UPSERT_BATCH_SIZE,
            )

    def process_documents(
        self,
        namespace: str,
        local_file_paths: list[Path],
        file_metadatas: list[VectorMetadata],
        parent_group_id: str,
    ):
        """Process all documents using Docling. Then, pass each document to Docling's
        HybridChunker for computing embeddings.
        """
        # Place imports in a function, since they are pretty expensive.
        from docling.chunking import HybridChunker  # type: ignore
        from docling.document_converter import DocumentConverter  # type: ignore
        from docling.exceptions import ConversionError  # type: ignore
        from transformers import AutoTokenizer  # type: ignore

        # From the docs:
        #   For each document format, the document converter knows which format-specific
        #   backend to employ for parsing the document and which pipeline to use for
        #   orchestrating the execution, along with any relevant options.
        # We'll start with the standard / simple pipelines for each of the allowed
        # formats
        converter = DocumentConverter(
            allowed_formats=SUPPORTED_INPUT_FORMATS,
        )
        tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL_ID)

        for path, metadata in zip(local_file_paths, file_metadatas):
            try:
                res = converter.convert(path)
                doc = res.document
                chunker = HybridChunker(tokenizer=tokenizer)
                chunk_iter = chunker.chunk(dl_doc=doc)
                chunks = list(chunk_iter)

                # Upsert vectors
                vectors = self.upsert_chunk_vectors(
                    chunks, metadata.model_dump(), parent_group_id
                )
                self.index.upsert(
                    vectors,
                    namespace=namespace,
                    batch_size=UPSERT_BATCH_SIZE,
                )
            except ConversionError:
                logger.error(f"Conversion failed for document: {json.dumps(metadata)}")
            except Exception as e:
                error_metadata = {
                    "file_metadata": metadata,
                    "exception_class": e.__class__.__name__,
                    "exception_details": str(e),
                }
                logger.error(
                    f"Failed to process document: {json.dumps(error_metadata)}"
                )

    @staticmethod
    def get_record_count(parent_group_id: str) -> int:
        res = db.all_objects(
            db_type=UpsertedVector,
            where_conditions={"parent_group_id": parent_group_id},
        )
        return len(res)

    async def delete_integration(self, namespace: str, integration_id: str):
        await self.async_index.delete(
            filter={"integration_id": str(integration_id)},
            namespace=namespace,
        )
        await asyncio.sleep(1)
