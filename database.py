from motor.motor_asyncio import AsyncIOMotorClient
from configs import cfg

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(cfg.MONGO_URI)
        self.db = self.client['main']
        self.users = self.db['users']
        self.groups = self.db['groups']

    async def user_exists(self, user_id: int) -> bool:
        return bool(await self.users.find_one({"user_id": user_id}))

    async def group_exists(self, chat_id: int) -> bool:
        return bool(await self.groups.find_one({"chat_id": chat_id}))

    async def add_user(self, user_id: int):
        if not await self.user_exists(user_id):
            await self.users.insert_one({"user_id": user_id})

    async def add_group(self, chat_id: int):
        if not await self.group_exists(chat_id):
            await self.groups.insert_one({"chat_id": chat_id})

    async def count_users(self) -> int:
        return await self.users.count_documents({})

    async def count_groups(self) -> int:
        return await self.groups.count_documents({})

db = Database()
