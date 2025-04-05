from motor.motor_asyncio import AsyncIOMotorClient
from configs import cfg
import asyncio

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(
            cfg.MONGO_URI,
            serverSelectionTimeoutMS=5000,
            socketTimeoutMS=30000,
            connectTimeoutMS=10000,
            waitQueueTimeoutMS=10000
        )
        self.db = self.client.get_database()
        self.users = self.db.users
        self.groups = self.db.groups

    async def _safe_cursor_execute(self, cursor_op):
        """Handle cursor operations safely"""
        try:
            return await cursor_op
        except Exception as e:
            if "CursorNotFound" in str(e):
                logger.warning("Cursor expired, retrying...")
                await asyncio.sleep(1)
                return await cursor_op
            raise e

    async def load_users_to_cache(self):
        """Safe user cache loading"""
        user_cache.clear()
        cursor = self.users.find({}, {'user_id': 1}).batch_size(100)
        async for user in await self._safe_cursor_execute(cursor):
            user_cache[user['user_id']] = True

    async def load_groups_to_cache(self):
        """Safe group cache loading"""
        group_cache.clear()
        cursor = self.groups.find({}, {'chat_id': 1}).batch_size(100)
        async for group in await self._safe_cursor_execute(cursor):
            group_cache[group['chat_id']] = True

    # ... keep other methods ...
