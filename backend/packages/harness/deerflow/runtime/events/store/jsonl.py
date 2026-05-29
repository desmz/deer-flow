"""JSONL file-backed RunEventStore implementation.

Each run's events are stored in a single file:
``.deer-flow/threads/{thread_id}/runs/{run_id}.jsonl``

All categories (message, trace, lifecycle) are in the same file.
This backend is suitable for lightweight single-node deployments.

Known trade-off: ``list_messages()`` must scan all run files for a
thread since messages from multiple runs need unified seq ordering.
``list_events()`` reads only one file -- the fast path.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

from deerflow.runtime.events.store.base import RunEventStore

logger = logging.getLogger(__name__)

# [DL-NOTE] Validates IDs before building filesystem paths — prevents directory traversal
# (e.g. thread_id="../../etc") since thread_id and run_id come from user-controlled API input.
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-]+$")


class JsonlRunEventStore(RunEventStore):
    def __init__(self, base_dir: str | Path | None = None):
        self._base_dir = Path(base_dir) if base_dir else Path(".deer-flow")
        self._seq_counters: dict[str, int] = {}  # thread_id -> current max seq

    @staticmethod
    def _validate_id(value: str, label: str) -> str:
        """Validate that an ID is safe for use in filesystem paths."""
        if not value or not _SAFE_ID_PATTERN.match(value):
            raise ValueError(f"Invalid {label}: must be alphanumeric/dash/underscore, got {value!r}")
        return value

    def _thread_dir(self, thread_id: str) -> Path:
        self._validate_id(thread_id, "thread_id")
        return self._base_dir / "threads" / thread_id / "runs"

    def _run_file(self, thread_id: str, run_id: str) -> Path:
        self._validate_id(run_id, "run_id")
        return self._thread_dir(thread_id) / f"{run_id}.jsonl"

    def _next_seq(self, thread_id: str) -> int:
        self._seq_counters[thread_id] = self._seq_counters.get(thread_id, 0) + 1
        return self._seq_counters[thread_id]

    # [DL-INSIGHT] Unlike MemoryRunEventStore (counter always starts at 0), this store must
    # survive process restarts — so the counter is lazily seeded from existing files on first
    # write per thread. Without this, a restarted process would re-assign seq=1 and collide
    # with events already on disk from the previous process.
    def _ensure_seq_loaded(self, thread_id: str) -> None:
        """Load max seq from existing files if not yet cached."""
        if thread_id in self._seq_counters:
            return
        max_seq = 0
        thread_dir = self._thread_dir(thread_id)
        if thread_dir.exists():
            for f in thread_dir.glob("*.jsonl"):
                for line in f.read_text(encoding="utf-8").strip().splitlines():
                    try:
                        record = json.loads(line)
                        max_seq = max(max_seq, record.get("seq", 0))
                    except json.JSONDecodeError:
                        logger.debug("Skipping malformed JSONL line in %s", f)
                        continue
        self._seq_counters[thread_id] = max_seq

    # [DL-WARN] Blocking file I/O (open + write) inside an async call — will stall the event
    # loop for the duration of the write. Acceptable for the "lightweight single-node" use case
    # but rules this backend out for high-concurrency production deployments.
    def _write_record(self, record: dict) -> None:
        path = self._run_file(record["thread_id"], record["run_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str, ensure_ascii=False) + "\n")

    # [DL-INSIGHT] This is the O(n_runs) slow path — scans EVERY run file for the thread to
    # build the unified seq-ordered view. list_events() reads only ONE file (fast path).
    # list_messages() must use this because messages from multiple runs share a single seq space.
    def _read_thread_events(self, thread_id: str) -> list[dict]:
        """Read all events for a thread, sorted by seq."""
        events = []
        thread_dir = self._thread_dir(thread_id)
        if not thread_dir.exists():
            return events
        for f in sorted(thread_dir.glob("*.jsonl")):
            for line in f.read_text(encoding="utf-8").strip().splitlines():
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.debug("Skipping malformed JSONL line in %s", f)
                    continue
        events.sort(key=lambda e: e.get("seq", 0))
        return events

    def _read_run_events(self, thread_id: str, run_id: str) -> list[dict]:
        """Read events for a specific run file."""
        path = self._run_file(thread_id, run_id)
        if not path.exists():
            return []
        events = []
        for line in path.read_text(encoding="utf-8").strip().splitlines():
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                logger.debug("Skipping malformed JSONL line in %s", path)
                continue
        events.sort(key=lambda e: e.get("seq", 0))
        return events

    async def put(self, *, thread_id, run_id, event_type, category, content="", metadata=None, created_at=None):
        self._ensure_seq_loaded(thread_id)
        seq = self._next_seq(thread_id)
        record = {
            "thread_id": thread_id,
            "run_id": run_id,
            "event_type": event_type,
            "category": category,
            "content": content,
            "metadata": metadata or {},
            "seq": seq,
            "created_at": created_at or datetime.now(UTC).isoformat(),
        }
        self._write_record(record)
        return record

    # [DL-NOTE] Calls await self.put() per event (vs MemoryRunEventStore which calls _put_one directly).
    # _ensure_seq_loaded runs once (first call caches the counter), cheap dict lookup for the rest.
    async def put_batch(self, events):
        if not events:
            return []
        results = []
        for ev in events:
            record = await self.put(**ev)
            results.append(record)
        return results

    async def list_messages(self, thread_id, *, limit=50, before_seq=None, after_seq=None):
        all_events = self._read_thread_events(thread_id)
        messages = [e for e in all_events if e.get("category") == "message"]

        if before_seq is not None:
            messages = [e for e in messages if e["seq"] < before_seq]
            return messages[-limit:]
        elif after_seq is not None:
            messages = [e for e in messages if e["seq"] > after_seq]
            return messages[:limit]
        else:
            return messages[-limit:]

    async def list_events(self, thread_id, run_id, *, event_types=None, limit=500):
        events = self._read_run_events(thread_id, run_id)
        if event_types is not None:
            events = [e for e in events if e.get("event_type") in event_types]
        return events[:limit]

    async def list_messages_by_run(self, thread_id, run_id, *, limit=50, before_seq=None, after_seq=None):
        events = self._read_run_events(thread_id, run_id)
        filtered = [e for e in events if e.get("category") == "message"]
        if before_seq is not None:
            filtered = [e for e in filtered if e.get("seq", 0) < before_seq]
        if after_seq is not None:
            filtered = [e for e in filtered if e.get("seq", 0) > after_seq]
        if after_seq is not None:
            return filtered[:limit]
        else:
            return filtered[-limit:] if len(filtered) > limit else filtered

    async def count_messages(self, thread_id):
        all_events = self._read_thread_events(thread_id)
        return sum(1 for e in all_events if e.get("category") == "message")

    async def delete_by_thread(self, thread_id):
        # [DL-NOTE] Reads all events first just to compute the return count — an O(n) scan
        # before the actual O(files) delete. No cheaper path exists without a separate count cache.
        all_events = self._read_thread_events(thread_id)
        count = len(all_events)
        thread_dir = self._thread_dir(thread_id)
        if thread_dir.exists():
            for f in thread_dir.glob("*.jsonl"):
                f.unlink()
        self._seq_counters.pop(thread_id, None)
        return count

    async def delete_by_run(self, thread_id, run_id):
        events = self._read_run_events(thread_id, run_id)
        count = len(events)
        path = self._run_file(thread_id, run_id)
        if path.exists():
            path.unlink()
        return count
