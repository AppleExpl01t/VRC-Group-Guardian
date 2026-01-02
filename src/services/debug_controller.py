import json
import threading
import flet as ft
from services.debug_logger import get_logger

logger = get_logger("debug_controller")

class DebugController:
    """
    Agentic Debug Interface (ADI) Controller.
    Allows external agents/processes to control the application state and UI 
    via JSON commands sent over stdin.
    """
    
    def __init__(self, app_instance):
        """
        Args:
            app_instance: Reference to the GroupGuardianApp instance
        """
        self.app = app_instance
        self.page = app_instance.page
        self._running = True

    def start_listener(self):
        """Start the stdin listener thread"""
        self_thread = threading.Thread(target=self._stdin_listener, daemon=True, name="ADI-Listener")
        self_thread.start()
        logger.info("ADI Listener started")

    def _stdin_listener(self):
        """Background thread to read stdin"""
        import sys
        
        # We need to be careful not to block app exit, but daemon thread handles that.
        while self._running:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                    
                line = line.strip()
                if not line:
                    continue
                
                # Check if it looks like a JSON command
                if line.startswith("{") and line.endswith("}"):
                    try:
                        cmd_data = json.loads(line)
                        self._dispatch_command(cmd_data)
                    except json.JSONDecodeError:
                        self._send_response({"error": "Invalid JSON", "raw": line})
            except Exception as e:
                logger.error(f"ADI Listener Error: {e}")
                
    def _dispatch_command(self, cmd_data: dict):
        """Dispatch command to appropriate handler on the UI thread"""
        cmd_type = cmd_data.get("cmd")
        req_id = cmd_data.get("id", None)
        
        if not cmd_type:
            return

        # Define handler
        async def task():
            try:
                result = None
                
                if cmd_type == "ping":
                    result = {"status": "pong"}
                elif cmd_type == "inspect_ui":
                    result = self._handle_inspect_ui()
                elif cmd_type == "click":
                    result = await self._handle_click(cmd_data.get("key"))
                elif cmd_type == "set_value":
                    result = await self._handle_set_value(cmd_data.get("key"), cmd_data.get("value"))
                elif cmd_type == "navigate":
                    result = self._handle_navigate(cmd_data.get("route"))
                elif cmd_type == "get_state":
                    result = self._handle_get_state()
                elif cmd_type == "find_keys":
                    result = self._handle_find_keys(cmd_data.get("pattern"))
                elif cmd_type == "click_pattern":
                    result = await self._handle_click_pattern(cmd_data.get("pattern"))
                elif cmd_type == "type_text":
                    result = await self._handle_type_text(cmd_data.get("key"), cmd_data.get("text"))
                elif cmd_type == "focus":
                    result = await self._handle_focus(cmd_data.get("key"))
                elif cmd_type == "get_focus":
                    result = self._handle_get_focus()
                else:
                    result = {"error": f"Unknown command: {cmd_type}"}
                
                self._send_response({"id": req_id, "result": result, "status": "success"})
            except Exception as e:
                import traceback
                self._send_response({
                    "id": req_id, 
                    "error": str(e), 
                    "status": "error",
                    "trace": traceback.format_exc()
                })

        # Run on UI thread in Flet
        async def async_wrapper():
            await task()
            
        self.page.run_task(async_wrapper)

    def _send_response(self, data: dict):
        """Print JSON response to stdout with special prefix"""
        import sys
        # Use a distinctive prefix so the agent can grep it easily
        print(f"[ADI-RESPONSE] {json.dumps(data)}", flush=True)

    # --- Handlers ---
    
    async def _handle_click_pattern(self, pattern):
        """Click the first control whose key contains pattern"""
        if not pattern:
            raise ValueError("Pattern is required")
            
        keys = self._handle_find_keys(pattern)
        if not keys:
            raise ValueError(f"No key found matching '{pattern}'")
            
        return await self._handle_click(keys[0])

    
    def _handle_find_keys(self, pattern=None):
        """Return list of all keys in current view"""
        if not self.page.views:
            return []
            
        current_view = self.page.views[-1]
        keys = []
        
        def walk(control):
            if hasattr(control, "key") and control.key:
                if not pattern or pattern in control.key:
                    keys.append(control.key)
            
            if hasattr(control, "controls") and control.controls:
                for c in control.controls:
                    if c: walk(c)
            if hasattr(control, "content") and control.content:
                walk(control.content)

        # Walk main view
        for c in current_view.controls:
            walk(c)
            
        # Walk overlays (Dialogs, Snackbars, BottomSheets)
        # page.overlay_controls is used in recent Flet versions for 'page.open'
        if hasattr(self.page, "overlay"):
             for c in self.page.overlay:
                 walk(c)
        
        return keys

    def _handle_get_state(self):
        """Return high-level application state"""
        user = self.app._current_user
        group = self.app._current_group
        return {
            "route": self.app._current_route,
            "authenticated": self.app._is_authenticated,
            "username": self.app._username,
            "current_group": {
                "id": group.get("id"),
                "name": group.get("name")
            } if group else None,
            "user_id": user.get("id") if user else None
        }

    def _handle_navigate(self, route):
        if not route:
            raise ValueError("Route is required")
        self.page.go(route)
        self.page.update()  # Force UI refresh
        return {"new_route": route}

    def _handle_inspect_ui(self):
        """Walk the current view's widget tree and return structure"""
        if not self.page.views:
            return {"views": []}
        
        current_view = self.page.views[-1]
        
        def walk(control):
            node = {
                "type": type(control).__name__,
            }
            if hasattr(control, "key") and control.key:
                node["key"] = control.key
            if hasattr(control, "data") and control.data:
                node["data"] = control.data
            if hasattr(control, "value") and control.value:
                # Truncate potentially long values
                val = str(control.value)
                node["value"] = val if len(val) < 50 else val[:50] + "..."
            if hasattr(control, "text") and control.text:
                 node["text"] = control.text
            
            # Recurse
            children = []
            # Check common content/controls properties
            if hasattr(control, "controls") and control.controls:
                children.extend([walk(c) for c in control.controls if c])
            if hasattr(control, "content") and control.content:
                children.append(walk(control.content))
            
            if children:
                node["children"] = children
            return node

        return {"view": current_view.route, "tree": [walk(c) for c in current_view.controls]}

    def _find_control(self, key):
        """Find a control by key in the current view"""
        if not self.page.views:
            return None
            
        current_view = self.page.views[-1]
        found = None
        
        def walk(control):
            nonlocal found
            if found: return
            
            if hasattr(control, "key") and control.key == key:
                found = control
                return
            
            if hasattr(control, "controls") and control.controls:
                for c in control.controls:
                    if c: walk(c)
            if hasattr(control, "content") and control.content:
                walk(control.content)

        for c in current_view.controls:
            walk(c)
            
        return found

    async def _handle_click(self, key):
        if not key:
            raise ValueError("Key is required")
            
        control = self._find_control(key)
        if not control:
            raise ValueError(f"Control with key '{key}' not found")
        
        if not hasattr(control, "on_click"):
            raise ValueError(f"Control '{key}' is not clickable (no on_click)")
            
        # --- Visual Feedback ---
        original_border = getattr(control, "border", None)
        import asyncio
        
        try:
            # Highlight
            control.border = ft.border.all(2, "red") # Bright red highlight
            control.update()
            await asyncio.sleep(0.5) # Wait for human to see
        except Exception:
            pass # Ignore styling errors on non-stylable controls
            
        # Restore
        try:
            control.border = original_border
            control.update()
        except Exception:
            pass
        # -----------------------

        # Trigger click
        e = ft.ControlEvent(
            target=control.uid,
            name="click",
            data="",
            control=control,
            page=self.page
        )
        
        handler = control.on_click
        if handler:
            import inspect
            if inspect.iscoroutinefunction(handler):
                await handler(e) # Await directly since we are in async_wrapper now
                return {"status": "clicked_async", "key": key}
            else:
                handler(e)
                return {"status": "clicked_sync", "key": key}
        
        return {"status": "no_handler", "key": key}

    async def _handle_set_value(self, key, value):
        if not key:
            raise ValueError("Key is required")
            
        control = self._find_control(key)
        if not control:
            raise ValueError(f"Control with key '{key}' not found")
            
        if hasattr(control, "value"):
            # --- Visual Feedback ---
            original_border = getattr(control, "border", None)
            import asyncio
            try:
                control.border = ft.border.all(2, "yellow") 
                control.update()
                await asyncio.sleep(0.3)
            except: pass
            # -----------------------

            control.value = value
            control.update()
            
            try:
                control.border = original_border
                control.update()
            except: pass
            
            # If there's an on_change, trigger it
            if hasattr(control, "on_change") and control.on_change:
                 e = ft.ControlEvent(
                    target=control.uid,
                    name="change",
                    data=str(value),
                    control=control,
                    page=self.page
                )
                 # Handle async/sync on_change
                 import inspect
                 handler = control.on_change
                 if inspect.iscoroutinefunction(handler):
                     await handler(e)
                 else:
                     handler(e)
                 
            return {"status": "value_set", "key": key, "value": value}
        else:
            raise ValueError(f"Control '{key}' does not support 'value'")

    async def _handle_type_text(self, key, text):
        """Type text character by character into a TextField, simulating real typing"""
        if not key:
            raise ValueError("Key is required")
        if not text:
            raise ValueError("Text is required")
            
        control = self._find_control(key)
        if not control:
            raise ValueError(f"Control with key '{key}' not found")
            
        if not hasattr(control, "value"):
            raise ValueError(f"Control '{key}' does not support 'value'")
        
        import asyncio
        
        # Focus the control first
        control.focus()
        await asyncio.sleep(0.1)
        
        # Get current value
        current_value = control.value or ""
        
        logger.debug(f"[ADI] type_text starting: key={key}, text={text}, current_value={current_value}")
        
        typed_chars = []
        for i, char in enumerate(text):
            # Append character
            current_value += char
            control.value = current_value
            typed_chars.append(char)
            
            logger.debug(f"[ADI] Typed char {i}: '{char}', value now: '{current_value}'")
            
            # Update control
            try:
                control.update()
            except Exception as e:
                logger.error(f"[ADI] Control update failed after char '{char}': {e}")
            
            # Trigger on_change if exists
            if hasattr(control, "on_change") and control.on_change:
                e = ft.ControlEvent(
                    target=control.uid,
                    name="change",
                    data=current_value,
                    control=control,
                    page=self.page
                )
                import inspect
                handler = control.on_change
                if inspect.iscoroutinefunction(handler):
                    await handler(e)
                else:
                    handler(e)
            
            # Small delay between keystrokes
            await asyncio.sleep(0.05)
            
            # Check if control is still focused (debug)
            logger.debug(f"[ADI] After char '{char}': control.value={control.value}")
        
        # Final check
        final_value = control.value
        logger.debug(f"[ADI] type_text complete: final_value={final_value}")
        
        return {
            "status": "typed", 
            "key": key, 
            "text": text, 
            "final_value": final_value,
            "chars_typed": len(typed_chars)
        }
    
    async def _handle_focus(self, key):
        """Focus a specific control"""
        if not key:
            raise ValueError("Key is required")
            
        control = self._find_control(key)
        if not control:
            raise ValueError(f"Control with key '{key}' not found")
        
        if hasattr(control, "focus"):
            control.focus()
            import asyncio
            await asyncio.sleep(0.1)
            return {"status": "focused", "key": key}
        else:
            raise ValueError(f"Control '{key}' does not support focus()")
    
    def _handle_get_focus(self):
        """Get info about currently focused control (if trackable)"""
        # Flet doesn't have a direct "get focused control" API
        # But we can try to check autofocus state on fields
        if not self.page.views:
            return {"focused": None, "note": "No views"}
        
        current_view = self.page.views[-1]
        focused_info = []
        
        def walk(control):
            # Check for autofocus or any focus indicator
            if hasattr(control, "autofocus") and control.autofocus:
                info = {"type": type(control).__name__}
                if hasattr(control, "key") and control.key:
                    info["key"] = control.key
                if hasattr(control, "value"):
                    info["value"] = str(control.value)[:50] if control.value else None
                focused_info.append(info)
            
            if hasattr(control, "controls") and control.controls:
                for c in control.controls:
                    if c: walk(c)
            if hasattr(control, "content") and control.content:
                walk(control.content)

        for c in current_view.controls:
            walk(c)
        
        return {"autofocus_controls": focused_info, "note": "Flet doesn't expose current focus directly"}

