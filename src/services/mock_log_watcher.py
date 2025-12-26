"""
Mock Log Watcher Service for Demo
"""
import threading
import time
import random

_instance = None

class MockLogWatcher:
    def __init__(self, callback=None):
        self.running = False
        self.thread = None
        self.listeners = []
        if callback:
             self.listeners.append(callback)
        
        self.active_players = {}
        self.player_avatars = {}
        self.current_world_id = "wrld_mock_1234"
        self.current_instance_id = "12345~private(usr_demo123)"
        self.current_group_id = "grp_demo_1"
        
        # Init some players
        for i in range(5):
             uid = f"usr_init_{i}"
             name = f"DemoFriend_{i}"
             self.active_players[uid] = name
        
    def add_listener(self, cb):
        if cb not in self.listeners:
            self.listeners.append(cb)
        
    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._mock_loop, daemon=True)
        self.thread.start()
        print("[MockLogWatcher] Started")
        
    def stop(self):
        self.running = False
        
    def _mock_loop(self):
        while self.running:
            time.sleep(4) 
            
            # Simulate joins/leaves
            evt = None
            ts = time.time()
            action = random.choice(["join", "leave", "switch", "nothing"])
            
            if action == "join":
                uid = f"usr_mock_{random.randint(1000,9999)}"
                name = f"Visitor_{random.randint(1,99)}"
                self.active_players[uid] = name
                evt = {
                    "type": "player_join",
                    "user_id": uid,
                    "display_name": name,
                    "timestamp": ts
                }
            elif action == "leave" and self.active_players:
                # Don't empty completely
                if len(self.active_players) > 1:
                    uid, name = random.choice(list(self.active_players.items()))
                    del self.active_players[uid]
                    evt = {
                        "type": "player_leave",
                        "user_id": uid,
                        "display_name": name,
                        "timestamp": ts
                    }
            elif action == "switch" and self.active_players:
                 uid, name = random.choice(list(self.active_players.items()))
                 avatar = f"Avatar_{random.randint(100, 999)}"
                 self.player_avatars[uid] = avatar
                 evt = {
                    "type": "player_avatar_change",
                    "user_id": uid,
                    "avatar_name": avatar,
                    "timestamp": ts
                 }
                 
            if evt:
                # print(f"[MockLogWatcher] Event: {evt['type']}")
                for l in self.listeners:
                    try: l(evt)
                    except: pass
                    
def get_log_watcher(callback=None):
    global _instance
    if _instance is None:
        _instance = MockLogWatcher(callback)
    elif callback:
        _instance.add_listener(callback)
    return _instance
