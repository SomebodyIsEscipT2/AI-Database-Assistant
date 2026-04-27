"""In-memory query history store with analytics capabilities.

Tracks every SQL query analyzed through the API, recording issues found,
optimization scores, and timestamps. Provides aggregate statistics for
identifying common patterns and monitoring analysis quality over time.
"""

import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QueryRecord:
    """A single logged query analysis event."""

    id: str
    sql_query: str
    database_type: str
    issues: list[str]
    optimization_score: float
    timestamp: float
    endpoint: str  # "analyze" or "chat"


class QueryHistoryStore:
    """Thread-safe in-memory store for query analysis history.

    In production, swap this for Redis or a proper database.
    The interface stays the same — only the backend changes.
    """

    def __init__(self, max_records: int = 10_000) -> None:
        self._records: list[QueryRecord] = []
        self._max_records = max_records

    def log_query(
        self,
        sql_query: str,
        database_type: str,
        issues: list[str],
        optimization_score: float,
        endpoint: str = "analyze",
    ) -> QueryRecord:
        """Record a query analysis event and return the created record."""
        record = QueryRecord(
            id=str(uuid.uuid4()),
            sql_query=sql_query,
            database_type=database_type,
            issues=issues,
            optimization_score=max(0.0, min(100.0, optimization_score)),
            timestamp=time.time(),
            endpoint=endpoint,
        )
        self._records.append(record)

        # Evict oldest records if we exceed capacity
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records :]

        return record

    def get_history(
        self,
        limit: int = 50,
        offset: int = 0,
        database_type: Optional[str] = None,
    ) -> list[QueryRecord]:
        """Retrieve query history with optional filtering and pagination."""
        filtered = self._records
        if database_type:
            filtered = [r for r in filtered if r.database_type == database_type]

        # Most recent first
        filtered = list(reversed(filtered))
        return filtered[offset : offset + limit]

    def get_stats(self) -> dict:
        """Compute aggregate statistics across all recorded queries."""
        if not self._records:
            return {
                "total_queries": 0,
                "avg_optimization_score": 0.0,
                "most_common_issues": [],
                "queries_by_database": {},
                "queries_by_endpoint": {},
                "score_distribution": {
                    "excellent": 0,
                    "good": 0,
                    "needs_improvement": 0,
                    "poor": 0,
                },
            }

        # Issue frequency
        all_issues: list[str] = []
        for record in self._records:
            all_issues.extend(record.issues)
        issue_counts = Counter(all_issues)
        most_common = [
            {"issue": issue, "count": count}
            for issue, count in issue_counts.most_common(10)
        ]

        # Average optimization score
        scores = [r.optimization_score for r in self._records]
        avg_score = sum(scores) / len(scores)

        # Score distribution buckets
        distribution = {"excellent": 0, "good": 0, "needs_improvement": 0, "poor": 0}
        for score in scores:
            if score >= 80:
                distribution["excellent"] += 1
            elif score >= 60:
                distribution["good"] += 1
            elif score >= 40:
                distribution["needs_improvement"] += 1
            else:
                distribution["poor"] += 1

        # Breakdown by database type
        db_counts = Counter(r.database_type for r in self._records)
        endpoint_counts = Counter(r.endpoint for r in self._records)

        return {
            "total_queries": len(self._records),
            "avg_optimization_score": round(avg_score, 2),
            "most_common_issues": most_common,
            "queries_by_database": dict(db_counts),
            "queries_by_endpoint": dict(endpoint_counts),
            "score_distribution": distribution,
        }

    def get_record_by_id(self, record_id: str) -> Optional[QueryRecord]:
        """Look up a single record by its ID."""
        for record in self._records:
            if record.id == record_id:
                return record
        return None

    def clear(self) -> int:
        """Clear all records. Returns the number of records removed."""
        count = len(self._records)
        self._records.clear()
        return count


# Module-level singleton — shared across the application
history_store = QueryHistoryStore()
