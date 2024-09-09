import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd
from litellm import embedding
from strif import abbreviate_list

from kmd.config.logger import get_logger
from kmd.model.model_settings import DEFAULT_EMBEDDING_MODEL

log = get_logger(__name__)


BATCH_SIZE = 1024


@dataclass
class Embeddings:
    """
    Embedded string values. Each string value has a unique key (e.g. its id or title or for
    small texts, the text itself).
    """

    data: Dict[str, Tuple[str, List[float]]]

    def as_iterable(self) -> Iterable[Tuple[str, str, List[float]]]:
        return ((key, text, emb) for key, (text, emb) in self.data.items())

    def as_df(self) -> pd.DataFrame:
        keys, texts, embeddings = zip(*[(key, text, emb) for key, (text, emb) in self.data.items()])
        return pd.DataFrame(
            {
                "key": keys,
                "text": texts,
                "embedding": embeddings,
            }
        )

    def to_csv(self, path: Path) -> None:
        self.as_df().to_csv(path, index=False)

    def __getitem__(self, key: str) -> Tuple[str, List[float]]:
        if key in self.data:
            return self.data[key]
        else:
            raise KeyError(f"Key '{key}' not found in embeddings")

    @classmethod
    def embed(cls, keyvals: List[Tuple[str, str]], model=DEFAULT_EMBEDDING_MODEL) -> "Embeddings":
        data = {}
        log.message(
            "Embedding %d texts (model %s, batch size %s)…", len(keyvals), model.value, BATCH_SIZE
        )
        for batch_start in range(0, len(keyvals), BATCH_SIZE):
            batch_end = batch_start + BATCH_SIZE
            batch = keyvals[batch_start:batch_end]
            keys = [kv[0] for kv in batch]
            texts = [kv[1] for kv in batch]

            # TODO: Add an embedding cache.

            response = embedding(model=model.value, input=texts)
            if not response.data:
                raise ValueError("No embedding response data")

            batch_embeddings = [e["embedding"] for e in response.data]
            data.update({key: (text, emb) for key, text, emb in zip(keys, texts, batch_embeddings)})

            log.message(
                "Embedded batch %d-%d: %s",
                batch_start,
                batch_end,
                abbreviate_list(texts),
            )

        return cls(data=data)

    @classmethod
    def read_from_csv(cls, path: Path) -> "Embeddings":
        df = pd.read_csv(path)
        df["embedding"] = df["embedding"].apply(ast.literal_eval)
        data = {row["key"]: (row["text"], row["embedding"]) for _, row in df.iterrows()}
        return cls(data=data)
