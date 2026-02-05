"""
Real MCP Server Implementation: Industrial Sensor Array.
Uses the official MCP Python SDK to expose tools over Stdio.
"""
from typing import Any
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("Industrial Sensor Array")

# Internal State (Simulating hardware registers)
_REGISTERS = {
    "core_temp": 350.0,
    "pressure_psi": 800.0,
    "status": "NORMAL"
}

@mcp.tool()
def read_sensor(sensor_id: str) -> float:
    """
    Reads a value from a specific hardware sensor.
    Args:
        sensor_id: 'core_temp' or 'pressure_psi'
    """
    return _REGISTERS.get(sensor_id, -1.0)

@mcp.tool()
def set_actuator(target_id: str, value: float) -> str:
    """
    Sets a target value for a hardware actuator.
    Args:
        target_id: 'core_temp' or 'pressure_psi'
        value: The target value to set.
    """
    if target_id in _REGISTERS:
        _REGISTERS[target_id] = value
        return f"SUCCESS: {target_id} set to {value}"
    return f"ERROR: Unknown target {target_id}"

if __name__ == "__main__":
    # Runs the MCP server over Stdio
    mcp.run()