# Audit chain

The audit log is append-only and hash-chained, so you can tell afterwards whether a record was changed, removed or reordered.

## Record format

Each record is one JSON object:

```json
{"seq": 6, "ts": "2026-11-27T13:41:14.962Z", "type": "decision", "data": {"...": "..."}, "prev": "<hash of record 5>", "hash": "<sha256>"}
```

`hash` is the sha256 of the canonical JSON (sorted keys, no whitespace) of `seq`, `ts`, `type`, `data` and `prev`. `prev` is the previous record's hash, and `0` repeated 64 times for the first. Record types include `decision`, `result`, `mode`, `kill_switch`, `safe_state`, `audit.gap` and `audit.backend_error`.

By default only a digest of the arguments (`args_sha256`) and the argument names are recorded. Set `include_args = true` to record raw arguments, and think about what that puts on disk.

## Verifying

```bash
aeon audit verify                       # exits 1 and names the first broken link
aeon audit verify --file path.jsonl
aeon audit verify --expect-head <hash>  # also detects removal from the end
```

Verification recomputes every hash and checks `seq` and `prev`. It stops at the first broken link and reports the line and the sequence number. On the committed run it verified about 179,000 records per second (one machine, see [Benchmarks](../evidence/benchmarks.md)).

## What it detects, and what it does not

| Change | Detected |
|---|---|
| a record edited | yes, hash mismatch |
| a record removed from the middle | yes, sequence gap |
| records reordered | yes |
| a corrupted line | yes |
| records removed from the **end** | only with `--expect-head` and a head hash you stored elsewhere |
| the whole chain rebuilt by someone with write access | no |

There is no signing and no external anchor yet. They are on the roadmap, and not built. Until then, copy the head hash somewhere the writer cannot reach if the log matters. Details in [Known limits](../known-limits.md).

## Written off the decision path

`emit` puts the event on a bounded queue (10,000 by default) and returns. One writer thread seals and appends in batches. Consequences:

- If the queue is full, the event is dropped, counted, and an `audit.gap` record is written later. In the committed burst test (20,000 events with no pause) 3,856 were dropped. Paced at 1,000 events/s none were.
- If storage fails, records wait in memory (bounded), the writer retries with backoff, and when storage returns it first writes an `audit.backend_error` record, so the outage is part of the chain.
- JSONL appends are all-or-nothing: if a write or fsync fails, the partial batch is truncated away. A missing trailing newline is repaired when the file is reopened, and new files are created with mode `0600`.
- One writer process per log file. Two processes appending to one file will fork the chain.

## Backends

JSONL (default, `.aeon/audit.jsonl`), SQLite (`sqlite:.aeon/audit.db` or a `.db` path) and an in-memory backend for tests. `aeon audit tail` (`-n 0` prints nothing) and `aeon audit export --format jsonl|csv` read any of them. CSV export neutralises cells that start like spreadsheet formulas. There is no Postgres backend.
