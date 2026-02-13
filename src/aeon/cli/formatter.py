"""Output formatting utilities for CLI."""

from typing import List, Dict, Any, Optional
from enum import Enum


class TableFormat(str, Enum):
    """Table formatting styles."""
    
    SIMPLE = "simple"
    GRID = "grid"
    ASCII = "ascii"


def format_cost(cost_usd: float) -> str:
    """Format cost in USD.
    
    Args:
        cost_usd: Cost in USD
        
    Returns:
        Formatted cost string
    """
    if cost_usd == 0:
        return "FREE"
    elif cost_usd < 0.01:
        return f"${cost_usd:.6f}"
    elif cost_usd < 1:
        return f"${cost_usd:.4f}"
    else:
        return f"${cost_usd:.2f}"


def format_tokens(token_count: int) -> str:
    """Format token count with commas.
    
    Args:
        token_count: Number of tokens
        
    Returns:
        Formatted token string
    """
    return f"{token_count:,}"


def format_table(
    data: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    style: TableFormat = TableFormat.SIMPLE,
) -> str:
    """Format data as a table.
    
    Args:
        data: List of dictionaries
        columns: Optional list of column names (defaults to dict keys)
        style: Table formatting style
        
    Returns:
        Formatted table string
    """
    if not data:
        return "(empty)"
    
    # Determine columns
    if columns is None:
        columns = list(data[0].keys())
    
    # Calculate column widths
    widths = {}
    for col in columns:
        widths[col] = max(
            len(str(col)),
            max(len(str(row.get(col, ""))) for row in data) if data else 0
        )
    
    # Format output
    lines = []
    
    if style == TableFormat.SIMPLE:
        # Header
        header = " | ".join(
            str(col).ljust(widths[col]) for col in columns
        )
        lines.append(header)
        lines.append("-" * len(header))
        
        # Rows
        for row in data:
            row_str = " | ".join(
                str(row.get(col, "")).ljust(widths[col]) for col in columns
            )
            lines.append(row_str)
    
    elif style == TableFormat.GRID:
        # Header separator
        separators = ["-" * (widths[col] + 2) for col in columns]
        lines.append("+" + "+".join(separators) + "+")
        
        # Header
        header_cells = [" " + str(col).ljust(widths[col]) + " " for col in columns]
        lines.append("|" + "|".join(header_cells) + "|")
        
        # Header separator
        lines.append("+" + "+".join(separators) + "+")
        
        # Rows
        for row in data:
            row_cells = [" " + str(row.get(col, "")).ljust(widths[col]) + " " for col in columns]
            lines.append("|" + "|".join(row_cells) + "|")
        
        # Footer separator
        lines.append("+" + "+".join(separators) + "+")
    
    elif style == TableFormat.ASCII:
        # ASCII art style
        lines.append("┌─" + "─┬─".join("─" * widths[col] for col in columns) + "─┐")
        
        # Header
        header_cells = [" " + str(col).ljust(widths[col]) + " " for col in columns]
        lines.append("│" + "│".join(header_cells) + "│")
        
        # Header separator
        lines.append("├─" + "─┼─".join("─" * widths[col] for col in columns) + "─┤")
        
        # Rows
        for row in data:
            row_cells = [" " + str(row.get(col, "")).ljust(widths[col]) + " " for col in columns]
            lines.append("│" + "│".join(row_cells) + "│")
        
        # Footer separator
        lines.append("└─" + "─┴─".join("─" * widths[col] for col in columns) + "─┘")
    
    return "\n".join(lines)


def format_duration(milliseconds: float) -> str:
    """Format duration in human-readable format.
    
    Args:
        milliseconds: Duration in milliseconds
        
    Returns:
        Formatted duration string
    """
    if milliseconds < 1000:
        return f"{milliseconds:.0f}ms"
    elif milliseconds < 60000:
        return f"{milliseconds / 1000:.1f}s"
    else:
        minutes = milliseconds / 60000
        return f"{minutes:.1f}m"


def format_percentage(value: float, total: float, decimals: int = 1) -> str:
    """Format value as percentage of total.
    
    Args:
        value: Value
        total: Total
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    if total == 0:
        return "0%"
    percentage = (value / total) * 100
    return f"{percentage:.{decimals}f}%"
