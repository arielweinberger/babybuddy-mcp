from fastmcp import FastMCP

from .auth import BabyBuddyTokenVerifier
from .tools import (
    children,
    diapers,
    feedings,
    measurements,
    medications,
    notes,
    profile,
    pumping,
    sleep,
    timers,
    tummy_times,
)

mcp = FastMCP(
    name="babybuddy-mcp",
    instructions=(
        "You are connected to a Baby Buddy baby tracking server. "
        "Use these tools to log and retrieve feeding, sleep, diaper change, "
        "pumping, tummy time, medication, and measurement events for a child. "
        "All times should be in ISO 8601 format (e.g. 2024-01-15T14:30:00). "
        "Call list_children first to discover available child IDs."
    ),
    auth=BabyBuddyTokenVerifier(),
)

mcp.mount(children.mcp, namespace="children")
mcp.mount(diapers.mcp, namespace="diapers")
mcp.mount(feedings.mcp, namespace="feedings")
mcp.mount(sleep.mcp, namespace="sleep")
mcp.mount(pumping.mcp, namespace="pumping")
mcp.mount(tummy_times.mcp, namespace="tummy_times")
mcp.mount(timers.mcp, namespace="timers")
mcp.mount(measurements.mcp, namespace="measurements")
mcp.mount(notes.mcp, namespace="notes")
mcp.mount(medications.mcp, namespace="medications")
mcp.mount(profile.mcp, namespace="profile")
