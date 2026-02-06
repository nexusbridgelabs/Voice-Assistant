from datetime import datetime
import json

def get_current_time():
    """Returns the current time in HH:MM AM/PM format."""
    return datetime.now().strftime("%I:%M %p")

def get_current_date():
    """Returns the current date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")

TIME_TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current time.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_date",
            "description": "Get the current date.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

AVAILABLE_TOOLS = {
    "get_current_time": get_current_time,
    "get_current_date": get_current_date,
}
