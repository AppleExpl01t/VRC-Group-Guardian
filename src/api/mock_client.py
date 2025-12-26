
import asyncio
import random
from typing import Dict, Optional, List
from datetime import datetime

class MockVRChatAPI:
    """Mock API client for Demo Mode"""
    
    def __init__(self):
        self._current_user = {
            "id": "usr_demo123",
            "displayName": "DemoUser",
            "userIcon": "https://assets.vrchat.com/www/avatars/default_v2.png", # Fallback
            "currentAvatarImageUrl": "https://assets.vrchat.com/www/avatars/default_v2.png",
            "currentAvatarThumbnailImageUrl": "https://assets.vrchat.com/www/avatars/default_v2.png",
            "tags": ["system_trust_legend"],
            "bio": "I am a demo user. I love testing apps and being safe.",
            "status": "active",  # VRChat status: active, join me, ask me, busy, offline
        }
        self._is_authenticated = False
        
        # Generation Pools
        self._usernames = [
            "Mirror_Dweller_420", "E-Boy_Slayer69", "Toaster_Lover_9000", "Headpats_Please",
            "Mute_Neko_Girl", "Crash_Override", "FBT_Expert", "Phantom_Touch_Guru",
            "Public_Lobby_Survivor", "VRC_Police_Dept", "Anime_Protagonist_Main",
            "Floor_Gang_Leader", "Unity_Crash_Logs", "Pickle_Rick_VRC"
        ]
        
        self._illnesses = [
            "chronic obsession with virtual mirrors", "phantom sensing anxiety", "severe lack of grass touching",
            "social anxiety unless in anime avatar", "addiction to sparkly shaders and D.I.D", "insomnia driven by different timezones",
            "pathological need for headpats"
        ]
        
        self._hobbies = [
            "judging people's polygon count", "sleeping in public lobbies", "crashing quest users",
            "ERP (Extreme Role Play)", "collecting e-boy tears", "dancing with 3 fps", 
            "staring at self in mirror for 6 hours"
        ]
        
        self._horror_story = "Don't look behind you. No seriously, in real life. I saw something move in your room while you were reading this. It's still there. Watching."
        
        # Generate data store
        self._members_store = {}
        self._requests_store = {}
        self._init_data()
        
    def _init_data(self):
        """Initialize random data for groups"""
        groups = ["grp_demo_1", "grp_demo_2"]
        
        # Ensure horror story is used exactly once
        horror_used = False
        
        for gid in groups:
            # Generate 5-10 members
            count = random.randint(5, 10)
            members = []
            
            for i in range(count):
                is_horror = False
                if not horror_used and (random.random() < 0.2 or (gid == groups[-1] and i == count - 1)):
                    is_horror = True
                    horror_used = True
                
                members.append(self._generate_user(i, is_horror=is_horror))
                
            self._members_store[gid] = members
            
            # Generate 1-2 requests
            req_count = random.randint(1, 2)
            requests = []
            for i in range(req_count):
                requests.append({
                    "id": f"req_{gid}_{i}",
                    "user": self._generate_user(i + 100, is_request=True),
                    "created_at": datetime.now().isoformat()
                })
            self._requests_store[gid] = requests

    def _generate_user_tags(self):
        """Generate random user tags including potential age verification"""
        tags = []
        
        # Trust rank (always have one)
        trust_ranks = ["system_trust_basic", "system_trust_known", "system_trust_trusted", "system_trust_veteran", "system_trust_legend"]
        tags.append(random.choice(trust_ranks))
        
        # Age verification (about 40% chance)
        if random.random() < 0.4:
            tags.append("system_trust_verified_adult")
        
        return tags

    def _generate_user(self, seed, is_horror=False, is_request=False):
        """Generate a random user dict"""
        username = random.choice(self._usernames) + str(random.randint(1, 99))
        
        if is_horror:
            bio = self._horror_story
        else:
            illness = random.choice(self._illnesses)
            hobby = random.choice(self._hobbies)
            bio = f"Hi! I'm {username}. My doctor says I have {illness}. In my free time I enjoy {hobby}. Add me!"
            
        user_obj = {
            "id": f"usr_mock_{random.randint(1000, 9999)}_{seed}",
            "displayName": username,
            "userIcon": "https://assets.vrchat.com/www/avatars/default_v2.png",
            "currentAvatarThumbnailImageUrl": "https://assets.vrchat.com/www/avatars/default_v2.png",
            "tags": self._generate_user_tags(),
            "bio": bio
        }
        
        if is_request:
            return user_obj
            
        return {
            "groupId": "grp_dummy",
            "user": user_obj
        }

    async def get_user(self, user_id: str) -> Optional[Dict]:
        await asyncio.sleep(0.1)
        # Check stores for this user to return consistent bio
        for members in self._members_store.values():
            for m in members:
                if m["user"]["id"] == user_id:
                    return m["user"]
        return {
            "id": user_id,
            "displayName": "MockUser",
            "bio": "This is a mock bio loaded lazily.",
            "userIcon": "https://assets.vrchat.com/www/avatars/default_v2.png" 
        }
        
    async def login(self, *args, **kwargs) -> Dict:
        await asyncio.sleep(0.5) # Simulate network
        self._is_authenticated = True
        return {"success": True, "requires_2fa": False}
        
    async def check_session(self) -> Dict:
        if self._is_authenticated:
            return {"valid": True, "user": self._current_user}
        return {"valid": False}
        
    async def logout(self):
        self._is_authenticated = False
        
    @property
    def is_authenticated(self) -> bool:
        return self._is_authenticated
        
    @property
    def current_user(self) -> Optional[Dict]:
        return self._current_user if self._is_authenticated else None

    @property
    def requires_2fa(self) -> bool:
        return False
    
    async def get_my_location(self) -> Optional[Dict]:
        """Mock get current user's location"""
        await asyncio.sleep(0.1)
        # Return a mock location (simulating being in an active instance for Live View)
        return {
            "world_id": "wrld_123",
            "instance_id": "instance_1~region(us)",
            "location": "wrld_123:instance_1~region(us)"
        }

    async def get_my_groups(self, **kwargs) -> List[Dict]:
        await asyncio.sleep(0.3)
        # Update member counts dynamically
        grp1_count = len(self._members_store.get("grp_demo_1", [])) + 1240
        grp2_count = len(self._members_store.get("grp_demo_2", [])) + 440
        
        return [
            {
                "id": "grp_demo_1",
                "name": "Demo Community",
                "shortCode": "DEMO",
                "iconUrl": "", 
                "bannerUrl": "",
                "memberCount": grp1_count,
                "pendingRequestCount": len(self._requests_store.get("grp_demo_1", [])),
                "msg_count": 5,
                "local_icon": None
            },
            {
                "id": "grp_demo_2", 
                "name": "VRChat Events",
                "shortCode": "EVENT",
                "memberCount": grp2_count,
                "pendingRequestCount": len(self._requests_store.get("grp_demo_2", [])),
                "msg_count": 0
            }
        ]

    async def get_group_instances(self, group_id: str) -> List[Dict]:
        await asyncio.sleep(0.3)
        return [
            {
                "location": "wrld_123:instance_1~region(us)",
                "memberCount": 24,
                "capacity": 32,
                "world": {"name": "The Great Pug", "imageUrl": "https://assets.vrchat.com/www/avatars/default_v2.png"}
            },
            {
                "location": "wrld_456:instance_2~region(eu)",
                "memberCount": 12,
                "capacity": 40,
                "world": {"name": "Black Cat", "imageUrl": "https://assets.vrchat.com/www/avatars/default_v2.png"}
            },
            {
                "location": "wrld_789:instance_3~region(jp)",
                "memberCount": 5,
                "capacity": 12,
                "world": {"name": "Midnight Rooftop", "imageUrl": "https://assets.vrchat.com/www/avatars/default_v2.png"}
            }
        ]

    async def create_instance(self, world_id, type, region, group_id, group_access_type, queue_enabled, name):
        """Mock create instance"""
        await asyncio.sleep(1.5) # Simulate API delay
        print(f"Mock: Created instance {name} in {region} for group {group_id}")
        return {
             "id": f"{world_id}:12345~hidden(usr_mock)~region({region})",
             "name": name if name else f"Group Instance {random.randint(100, 999)}",
             "shortName": f"#{random.randint(1000, 9999)}",
             "world": {"name": "Mock World", "id": world_id},
             "ownerId": self._current_user["id"],
        }
        
    async def get_group_join_requests(self, group_id: str) -> List[Dict]:
        await asyncio.sleep(0.2)
        return self._requests_store.get(group_id, [])
    
    async def close_group_instance(self, world_id: str, instance_id: str, hard_close: bool = False) -> bool:
        """Mock close instance - always succeeds"""
        await asyncio.sleep(0.5)
        return True

    async def get_group_audit_logs(self, group_id: str, n: int = 50) -> List[Dict]:
        return [
             {"created_at": datetime.now().isoformat(), "type": "group.user.join", "actorDisplayName": "System", "description": "User joined"},
             {"created_at": datetime.now().isoformat(), "type": "group.instance.create", "actorDisplayName": "DemoUser", "description": "Created instance"},
        ]
        
    async def get_group_bans(self, group_id: str, n: int = 50) -> List[Dict]:
        await asyncio.sleep(0.2)
        # Return some mock banned users
        if not hasattr(self, '_bans_store'):
            self._bans_store = {}
            
        if group_id not in self._bans_store:
            # Generate 2-5 banned users
            ban_count = random.randint(2, 5)
            banned = []
            for i in range(ban_count):
                user = self._generate_user(seed=i + 200)
                banned.append({
                    "id": f"ban_{group_id}_{i}",
                    "groupId": group_id,
                    "userId": user["user"]["id"],
                    "user": user["user"],
                    "createdAt": "2024-12-15T10:30:00Z",
                    "bannedAt": "2024-12-15T10:30:00Z",
                })
            self._bans_store[group_id] = banned
            
        return self._bans_store.get(group_id, [])
        
    async def search_group_members(self, group_id: str, query: str = None, limit: int = 50, offset: int = 0) -> List[Dict]:
        await asyncio.sleep(0.2)
        members = self._members_store.get(group_id, [])
        if query:
            members = [m for m in members if query.lower() in m["user"]["displayName"].lower()]
        
        # Sort by display name
        members.sort(key=lambda x: x["user"]["displayName"])
        
        # Paginate
        return members[offset : offset + limit]
        
    async def download_image(self, url: str, save_name: str) -> Optional[str]:
        return None 
        
    async def cache_user_image(self, user: Dict) -> Optional[str]:
        return user.get("currentAvatarThumbnailImageUrl") or user.get("userIcon")

    async def cache_group_images(self, group: Dict) -> None:
        """Mock implementation - just return without caching"""
        pass

    async def handle_join_request(self, group_id: str, request_id: str, action: str = "Accept") -> bool:
        """Mock handle join request"""
        await asyncio.sleep(0.5)
        # Remove from store
        if group_id in self._requests_store:
            self._requests_store[group_id] = [r for r in self._requests_store[group_id] if r["id"] != request_id]
        print(f"Mock: {action}ed join request {request_id}")
        return True

    async def ban_user(self, group_id: str, user_id: str) -> bool:
        """Mock ban user"""
        await asyncio.sleep(0.5)
        # Remove from members if present
        if group_id in self._members_store:
            self._members_store[group_id] = [m for m in self._members_store[group_id] if m["user"]["id"] != user_id]
            
        print(f"Mock: Banned user {user_id} from group {group_id}")
        return True

    async def unban_user(self, group_id: str, user_id: str) -> bool:
        """Mock unban user"""
        await asyncio.sleep(0.5)
        # Remove from bans store
        if hasattr(self, '_bans_store') and group_id in self._bans_store:
            self._bans_store[group_id] = [b for b in self._bans_store[group_id] if b.get("userId") != user_id and b.get("user", {}).get("id") != user_id]
            
        print(f"Mock: Unbanned user {user_id} from group {group_id}")
        return True

    async def invite_user_to_group(self, group_id: str, user_id: str) -> bool:
        """Mock invite user to group"""
        await asyncio.sleep(0.3)
        print(f"Mock: Invited user {user_id} to group {group_id}")
        return True

    async def get_friends(self, offline: bool = False, n: int = 100, offset: int = 0) -> List[Dict]:
        """Mock get friends list"""
        await asyncio.sleep(0.2)
        # Generate some mock friends
        mock_friends = []
        statuses = ["active", "join me", "ask me", "busy"] if not offline else ["offline"]
        
        for i in range(min(n, 15)):  # Return up to 15 mock friends
            mock_friends.append({
                "id": f"usr_friend_{i + offset}",
                "displayName": f"{random.choice(self._usernames)}_{i + offset}",
                "status": random.choice(statuses),
                "currentAvatarThumbnailImageUrl": "https://assets.vrchat.com/www/avatars/default_v2.png",
            })
        return mock_friends

    async def get_all_friends(self) -> List[Dict]:
        """Mock get all friends"""
        online = await self.get_friends(offline=False)
        offline = await self.get_friends(offline=True)
        return online + offline

    async def invite_to_instance(self, user_id: str, world_id: str, instance_id: str) -> bool:
        """Mock invite user to instance"""
        await asyncio.sleep(0.3)
        print(f"Mock: Invited {user_id} to instance {world_id}:{instance_id}")
        return True

    async def search_users(self, query: str, n: int = 20, offset: int = 0) -> List[Dict]:
        """Mock search users"""
        await asyncio.sleep(0.3)
        
        if not query or not query.strip():
            return []
        
        # Generate mock search results
        results = []
        query_lower = query.lower()
        
        # Return some mock users that "match" the query
        mock_names = [
            f"{query}_Pro_2024",
            f"Official_{query}",
            f"{query}VR",
            f"The_Real_{query}",
            f"{query}_Gaming",
        ]
        
        for i, name in enumerate(mock_names[:min(n, 5)]):
            results.append({
                "id": f"usr_search_{i}_{random.randint(1000, 9999)}",
                "displayName": name,
                "bio": f"Hi! I'm {name}. {random.choice(self._illnesses)}. I enjoy {random.choice(self._hobbies)}.",
                "currentAvatarThumbnailImageUrl": "https://assets.vrchat.com/www/avatars/default_v2.png",
                "userIcon": "https://assets.vrchat.com/www/avatars/default_v2.png",
                "status": random.choice(["active", "join me", "ask me", "busy", "offline"]),
                "tags": self._generate_user_tags(),
            })
        
        return results
