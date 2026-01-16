from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pymongo import MongoClient

from src.scraper import Scraper, ScraperConfig
from chat_agh.vector_store.mongodb import MongoDBVectorStore


# -----------------------
# CONFIG
# -----------------------
URLS_PATH = Path("/Users/wnowogorski/PycharmProjects/ChatAGH_DataCollecting/src/clusters/")
BASE_OUT_DIR = Path("./runs")  # change if you want

CHUNK_SIZE = 1024
CHUNK_OVERLAP = 0

BATCH_SIZE_URLS = 200          # << how many URLs per batch
SLEEP_BETWEEN_BATCHES_S = 0.0


# -----------------------
# CHECKPOINT
# -----------------------
@dataclass
class Checkpoint:
    cluster_file: str
    cluster_collection: str
    total_urls: int
    batch_size_urls: int
    next_batch_idx: int = 0
    processed_urls: List[str] = None  # store URLs already done

    def __post_init__(self):
        if self.processed_urls is None:
            self.processed_urls = []


def load_checkpoint(path: Path) -> Optional[Checkpoint]:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Checkpoint(**data)


def save_checkpoint(path: Path, ckpt: Checkpoint) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(ckpt), ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_urls(urls: List[str]) -> List[str]:
    out = []
    for u in urls:
        if u.startswith("http://") or u.startswith("https://"):
            out.append(u)
        else:
            out.append("https://" + u)
    return out


def batched(lst: List[str], n: int) -> List[List[str]]:
    return [lst[i : i + n] for i in range(0, len(lst), n)]


# -----------------------
# BATCH PROCESSING
# -----------------------
def process_cluster(cluster_file: str, cluster_collection: str) -> None:
    # Load URLs
    payload = json.loads((URLS_PATH / cluster_file).read_text(encoding="utf-8"))
    unique_urls = normalize_urls(payload["cluster_urls"])
    total_urls = len(unique_urls)

    # Run directory + checkpoint
    run_dir = BASE_OUT_DIR / cluster_collection
    run_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = run_dir / "checkpoint.json"

    ckpt = load_checkpoint(checkpoint_path)
    if ckpt is None:
        ckpt = Checkpoint(
            cluster_file=cluster_file,
            cluster_collection=cluster_collection,
            total_urls=total_urls,
            batch_size_urls=BATCH_SIZE_URLS,
            next_batch_idx=0,
            processed_urls=[],
        )
        save_checkpoint(checkpoint_path, ckpt)

    # If batch size changed, re-batch from scratch but keep processed_urls
    urls_batches = batched(unique_urls, BATCH_SIZE_URLS)

    print(f"[{cluster_collection}] total_urls={total_urls} batches={len(urls_batches)}")
    print(f"[{cluster_collection}] resume at batch={ckpt.next_batch_idx}")

    # Init vector store once
    vector_store = MongoDBVectorStore(collection_name=cluster_collection)

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    for batch_idx in range(ckpt.next_batch_idx, len(urls_batches)):
        batch_urls_all = urls_batches[batch_idx]

        # Skip URLs already processed (resume-safe)
        batch_urls = [u for u in batch_urls_all if u not in set(ckpt.processed_urls)]
        if not batch_urls:
            print(f"[{cluster_collection}] batch {batch_idx}: all URLs already processed, skipping")
            ckpt.next_batch_idx = batch_idx + 1
            save_checkpoint(checkpoint_path, ckpt)
            continue

        batch_out = run_dir / f"batch_{batch_idx:05d}"
        batch_out.mkdir(parents=True, exist_ok=True)

        print(f"\n[{cluster_collection}] batch {batch_idx}/{len(urls_batches)-1} urls={len(batch_urls)}")

        # Scrape this batch only
        scraper = Scraper(
            urls=batch_urls,
            output_path=str(batch_out),
            config=ScraperConfig(
                max_workers=8,
                per_host_concurrency=2,
                min_delay_s=0.9,
                delay_jitter_s=0.4,
                max_retries=3,
            ),
        )
        scraper.scrape()
        scraper.filter_documents()
        scraper.save_result_to_json("docs.json")

        docs_json = json.loads((batch_out / "docs.json").read_text(encoding="utf-8"))
        documents = [Document(page_content=d["page_content"], metadata=d["metadata"]) for d in docs_json]

        # Chunk per-page; set sequence_number per page and ensure url key exists for windowing
        chunks: List[Document] = []
        for doc in documents:
            # best effort: keep a stable page identity in metadata
            # (your scraper likely sets url already; just ensure it's there)
            if "url" not in doc.metadata and "source" in doc.metadata:
                doc.metadata["url"] = doc.metadata["source"]

            page_chunks = splitter.split_documents([doc])
            for i, c in enumerate(page_chunks):
                c.metadata["sequence_number"] = i
                # also keep url on each chunk
                if "url" in doc.metadata and "url" not in c.metadata:
                    c.metadata["url"] = doc.metadata["url"]
            chunks.extend(page_chunks)

        print(f"[{cluster_collection}] batch {batch_idx}: chunks={len(chunks)} -> indexing")
        vector_store.indexing(chunks)

        # Update checkpoint
        ckpt.processed_urls.extend(batch_urls)
        ckpt.next_batch_idx = batch_idx + 1
        save_checkpoint(checkpoint_path, ckpt)

        if SLEEP_BETWEEN_BATCHES_S:
            import time
            time.sleep(SLEEP_BETWEEN_BATCHES_S)

    print(f"\n[{cluster_collection}] DONE. processed_urls={len(set(ckpt.processed_urls))}/{total_urls}")


if __name__ == "__main__":
    load_dotenv("/Users/wnowogorski/PycharmProjects/ChatAGH/DataCollecting/.env")
    assert os.getenv("MONGODB_URI"), "Set MONGODB_URI first."

    mongo = MongoClient(os.environ["MONGODB_URI"])
    mongo.admin.command("ping")

    cluster_files = ["cluster_6.json"]

    for f in cluster_files:
        cluster_num = f.replace("cluster_", "").replace(".json", "")
        collection = f"cluster_{cluster_num}_v3"
        process_cluster(f, collection)
