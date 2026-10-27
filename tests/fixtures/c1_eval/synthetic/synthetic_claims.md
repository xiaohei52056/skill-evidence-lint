# Synthetic C1 phenomena fixture

This file is hand-written to exercise C1 pattern coverage and edge cases.
It is NOT a real SKILL.md; it exists only for the Phase 7B evaluation report.

## In-scope positives (should be caught)

The pipeline reduces processing time by 40% compared with the legacy runner.
Our compiler cuts cost by 2x for typical workloads.
The tuned retrieval achieves 92% accuracy on the held-out set.
Indexed queries are 2x faster than sequential scans.
The new allocator uses 30% less memory under sustained load.
The agent runs with zero downtime during rolling deploys.
We measured near-zero latency for cached requests.
The caching layer boosts throughput by 3x for read-heavy traffic.

Multiple claims in one paragraph: this build cuts CI time by 60%, reduces
memory by 25%, and achieves 99.9% availability across the fleet.

## In-scope negatives (must NOT be caught)

Python 3.11 introduced tomllib in the standard library.
The timeout defaults to 30 seconds for outbound calls.
Release v2.4.10 shipped on 2026-03-15 with no breaking changes.
The retries parameter defaults to 3 attempts before giving up.
Run the script with `--workers 8` to parallelize.
Open the file at `docs/evidence/report.md` and review it.
If you run the test suite, expect it to finish in under two minutes.
Do not skip linting; the project does not tolerate warnings.
The legacy path does not reduce cost by 40% because it still scans sequentially.
Assuming a 50% cache hit rate, throughput would improve by 2x.
We aim to reduce p95 latency by 30% in the next quarter.
The table shows colors 60-70% of visual weight for the dominant palette.
Use image dimensions 128x128 for emoji GIFs.
Split the eval set into 60% train and 40% held-out test.
Roughly 95% of incomplete investigations are missing a root cause.

## Out of scope (qualitative / passive / Chinese)

This skill is fast and reliable for everyday use.
Build time is reported down 40% in the latest benchmark.
The system was improved by 25% after the index change.
本工具将处理时间缩短了 40%，准确率达到 92%。

## Code block (must be ignored entirely)

```
# inside a fenced block - must not be scanned
the script reduces runtime by 80% and achieves 99% accuracy
```

    indented code block also must not be scanned:
    it reduces cost by 2x and has zero downtime.

## List items with mixed content

- First item describes a normal operation: open the file.
- Second item claims the optimizer cuts cold starts by 50%.
- Third item is just a dimension: image at 2048x1536.
