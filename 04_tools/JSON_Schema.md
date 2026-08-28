# Prompt for JSON Schema
Write a valid JSON schema for the purposes of tool calling for the below function.
Follow the best practices listed in Claude docs site - https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview

# Function to get current date and time in a specific format
def get_current_datetime(format_string = "%Y-%m-%d %H:%M:%S"):
    """
    Returns the current date and time formatted according to the provided format string.

    Parameters:
    - format_string (str): The format in which to return the current date and time. 
      Defaults to "%Y-%m-%d %H:%M:%S".

    Returns:
    - str: The current date and time as a formatted string.
    """
    if not format_string:
        raise ValueError("Format string cannot be empty.")
    
    return datetime.now().strftime(format_string)

# JSON Schema

```json
{
  "name": "get_current_datetime",
  "description": "Get the current date and time, formatted according to a Python strftime-style format string. Use this tool whenever you need to know the current date, time, or both — for example, to timestamp output, compute relative dates ('in 3 days', 'next Monday'), or answer direct questions like 'what time is it now' or 'what's today's date'. If no format_string is provided, defaults to 'YYYY-MM-DD HH:MM:SS' (e.g. '2026-08-08 11:56:54').",
  "input_schema": {
    "type": "object",
    "properties": {
      "format_string": {
        "type": "string",
        "description": "A Python strftime format string controlling the output format. Examples: '%Y-%m-%d %H:%M:%S' -> '2026-08-08 11:56:54', '%Y-%m-%d' -> '2026-08-08', '%B %d, %Y' -> 'August 08, 2026', '%H:%M' -> '11:56', '%A, %B %d, %Y %I:%M:%S %p' -> 'Saturday, August 08, 2026 11:56:54 AM'. Must not be an empty string.",
        "default": "%Y-%m-%d %H:%M:%S"
      }
    },
    "required": []
  }
}
```
