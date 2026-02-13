"""Metrics collection and reporting."""

from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque


class MetricType(Enum):
    """Metric types."""
    COUNTER = "counter"      # Monotonically increasing
    GAUGE = "gauge"          # Current value
    HISTOGRAM = "histogram"  # Distribution
    TIMER = "timer"          # Duration


@dataclass
class Metric:
    """Single metric measurement."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)


class MetricCollector:
    """Collects and stores metrics."""
    
    def __init__(self, max_history: int = 1000):
        self.metrics: Dict[str, deque] = {}
        self.max_history = max_history
    
    def record(self, metric: Metric) -> None:
        """Record a metric."""
        if metric.name not in self.metrics:
            self.metrics[metric.name] = deque(maxlen=self.max_history)
        
        self.metrics[metric.name].append(metric)
    
    def counter(self, name: str, value: float = 1.0, labels: Optional[Dict] = None) -> None:
        """Record counter metric."""
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.COUNTER,
            labels=labels or {}
        )
        self.record(metric)
    
    def gauge(self, name: str, value: float, labels: Optional[Dict] = None) -> None:
        """Record gauge metric."""
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            labels=labels or {}
        )
        self.record(metric)
    
    def histogram(self, name: str, value: float, labels: Optional[Dict] = None) -> None:
        """Record histogram metric."""
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.HISTOGRAM,
            labels=labels or {}
        )
        self.record(metric)
    
    def timer(self, name: str, duration_ms: float, labels: Optional[Dict] = None) -> None:
        """Record timer metric."""
        metric = Metric(
            name=name,
            value=duration_ms,
            metric_type=MetricType.TIMER,
            labels=labels or {}
        )
        self.record(metric)
    
    def get_metrics(self, name: Optional[str] = None) -> Dict[str, List[Metric]]:
        """Get recorded metrics."""
        if name:
            return {name: list(self.metrics.get(name, []))}
        return {n: list(m) for n, m in self.metrics.items()}
    
    def get_latest(self, name: str) -> Optional[Metric]:
        """Get latest metric value."""
        metrics_list = self.metrics.get(name)
        if metrics_list:
            return metrics_list[-1]
        return None
    
    def get_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for metric."""
        metrics_list = list(self.metrics.get(name, []))
        if not metrics_list:
            return None
        
        values = [m.value for m in metrics_list]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1],
            "metric_type": metrics_list[-1].metric_type.value
        }
    
    def clear(self, name: Optional[str] = None) -> None:
        """Clear metrics."""
        if name:
            if name in self.metrics:
                del self.metrics[name]
        else:
            self.metrics.clear()


class Metrics:
    """Global metrics registry."""
    
    def __init__(self):
        self.collectors: Dict[str, MetricCollector] = {}
    
    def get_collector(self, name: str) -> MetricCollector:
        """Get or create collector."""
        if name not in self.collectors:
            self.collectors[name] = MetricCollector()
        return self.collectors[name]
    
    def record_metric(self, collector_name: str, metric: Metric) -> None:
        """Record metric in collector."""
        self.get_collector(collector_name).record(metric)
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get all statistics."""
        stats = {}
        for collector_name, collector in self.collectors.items():
            stats[collector_name] = {}
            for metric_name in collector.metrics.keys():
                metric_stats = collector.get_stats(metric_name)
                if metric_stats:
                    stats[collector_name][metric_name] = metric_stats
        
        return stats
