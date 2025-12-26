---
description: How to use the Agentic Debug Interface (ADI) to control and debug the application
---

# Agentic Debug Interface (ADI) Workflow

The ADI allows you to programmatically control the running application via standard input/output. This is useful for verification, debugging, and automated testing.

## 1. Starting the App
Run the application normally using `run_command`. Ensure you capture a `CommandId` to send inputs later.
```powershell
py src/main.py
```
*Note: The ADI is always active in the background thread of the app.*

## 2. Sending Commands
Use the `send_command_input` tool to send JSON commands to the running process.
**Format**: `{"cmd": "COMMAND_NAME", "id": "REQUEST_ID", "args": ...}`

### Available Commands

#### `ping`
Verify the interface is responsive.
```json
{"cmd": "ping", "id": "1"}
```

#### `inspect_ui`
Get a JSON dump of the current widget tree. Use this to find `key`s of elements.
```json
{"cmd": "inspect_ui", "id": "2"}
```

#### `click`
Simulate a click on a UI element found by its `key`.
```json
{"cmd": "click", "key": "element_key_here", "id": "3"}
```

#### `set_value`
Set the value of a text field or input.
```json
{"cmd": "set_value", "key": "input_key", "value": "hello world", "id": "4"}
```

#### `navigate`
Force navigation to a specific route.
```json
{"cmd": "navigate", "route": "/dashboard", "id": "5"}
```

#### `get_state`
Get high-level app state (CurrentUser, CurrentGroup, Route).
```json
{"cmd": "get_state", "id": "6"}
```

## 3. Reading Responses
Use `command_status` or see the output of `send_command_input`.
Responses are printed to stdout with the prefix: `[ADI-RESPONSE]`

**Example Response**:
```json
[ADI-RESPONSE] {"id": "2", "result": {"view": "/login", "tree": [...]}, "status": "success"}
```

## 4. Best Practices
1.  **Always use `inspect_ui` first** to discover value keys if you aren't sure.
2.  **Add Keys**: If an element is hard to target, edit the code to add a unique `key="my_element"` to the Flet control, then reload/restart.
3.  **Check Route**: Use `get_state` to confirm you are on the expected view before interacting.
