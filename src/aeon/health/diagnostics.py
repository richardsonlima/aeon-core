"""Diagnostics and reporting."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import sys


@dataclass
class DiagnosticReport:
    """Diagnostic report."""
    generated_at: datetime = field(default_factory=datetime.utcnow)
    system_info: Dict[str, Any] = field(default_factory=dict)
    health_status: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class Diagnostics:
    """System diagnostics and reporting."""
    
    def __init__(self):
        self.health_checker = None
        self.metrics = None
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def set_health_checker(self, health_checker: Any) -> None:
        """Set health checker."""
        self.health_checker = health_checker
    
    def set_metrics(self, metrics: Any) -> None:
        """Set metrics."""
        self.metrics = metrics
    
    def add_error(self, error: str) -> None:
        """Add error to diagnostics."""
        self.errors.append(error)
    
    def add_warning(self, warning: str) -> None:
        """Add warning to diagnostics."""
        self.warnings.append(warning)
    
    async def generate_report(self) -> DiagnosticReport:
        """Generate comprehensive diagnostic report."""
        report = DiagnosticReport()
        
        # System info
        report.system_info = {
            "python_version": sys.version,
            "platform": sys.platform,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Health status
        if self.health_checker:
            health = await self.health_checker.check_all()
            report.health_status = self.health_checker.get_report()
        
        # Metrics
        if self.metrics:
            report.metrics = self.metrics.get_all_stats()
        
        # Errors and warnings
        report.errors = self.errors.copy()
        report.warnings = self.warnings.copy()
        
        return report
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get system summary."""
        return {
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings)
        }
