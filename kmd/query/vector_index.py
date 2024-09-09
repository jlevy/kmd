import os
from pathlib import Path
from typing import Iterable

from kmd.config.logger import get_logger
from kmd.model.items_model import Item
from kmd.query.index_utils import drop_non_atomic, flatten_dict, tiktoken_tokenizer
from kmd.util.type_utils import not_none


log = get_logger(__name__)


class WsVectorIndex:
    def __init__(self, index_dir: Path):
        self.index_dir = index_dir

        self.db_path = str(index_dir / "chroma.db")
        self._setup_done = False

    def _setup(self, collection_name="workspace"):
        """
        Idempotent (and slow) initialization of the database and index.
        """
        if self._setup_done:
            return

        log.message("Setting up vector index: %s", self.index_dir)

        import chromadb
        from chromadb.config import Settings
        from llama_index.core import get_response_synthesizer, VectorStoreIndex
        from llama_index.core.node_parser import SentenceSplitter
        from llama_index.core.postprocessor import SimilarityPostprocessor
        from llama_index.core.query_engine import RetrieverQueryEngine
        from llama_index.core.retrievers import VectorIndexRetriever
        from llama_index.core.storage import StorageContext
        from llama_index.vector_stores.chroma import ChromaVectorStore

        # DB setup:
        os.makedirs(self.index_dir, exist_ok=True)

        self.db = chromadb.PersistentClient(
            path=self.db_path, settings=Settings(anonymized_telemetry=False)
        )
        self.chroma_collection = self.db.get_or_create_collection(collection_name)
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

        self.vector_index = VectorStoreIndex.from_documents(
            [],
            storage_context=self.storage_context,
            transformations=[],
            show_progress=False,
        )

        # Retrieval and query setup:
        # TODO: Consider using our own secion- and paragraph-based splitting.
        self.text_splitter = SentenceSplitter(
            chunk_size=1024,  # LlamaIndex default values are chunk_size=1024, chunk_overlap=20 (in tokens).
            chunk_overlap=20,
            tokenizer=tiktoken_tokenizer(),
        )
        self.retriever = VectorIndexRetriever(
            index=self.vector_index,
            similarity_top_k=10,
        )
        self.response_synthesizer = get_response_synthesizer()
        self.query_engine = RetrieverQueryEngine(
            retriever=self.retriever,
            response_synthesizer=self.response_synthesizer,
            node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=0.7)],
        )
        # query_engine = self.index.as_query_engine()

        self._setup_done = True

    def index_items(self, items: Iterable[Item]):
        self._setup()

        from llama_index.core import Document
        from llama_index.core.ingestion import run_transformations

        documents = []
        for item in items:
            if item.body:
                # LlamaIndex requires extra_info to be a flat dict with only basic atomic types.
                item_meta = drop_non_atomic(flatten_dict(item.metadata(datetime_as_str=True)))

                document = Document(text=item.body, extra_info=item_meta)
                document.id_ = not_none(item.doc_id())
                documents.append(document)

                log.message("Adding doc: %s", document.id_)

        nodes = run_transformations(documents, [self.text_splitter], show_progress=False)

        log.message("Adding to index: %s docs split into %s nodes", len(documents), len(nodes))
        self.vector_index.insert_nodes(nodes)

    def unindex_items(self, items: Iterable[Item]):
        self._setup()

        for item in items:
            self.vector_index.delete_ref_doc(item.doc_id())

    def retrieve(self, query: str):
        self._setup()

        response = self.retriever.retrieve(query)
        return response

    def query(self, query_str: str):
        self._setup()

        response = self.query_engine.query(query_str)
        return response

    def __str__(self):
        return f"LlamaIndex Query Engine ({self.index_dir})"
