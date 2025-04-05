import asyncio
import time
import logging
import pickle
import os
from typing import Dict, List
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import FloodWait, UserNotParticipant
from database import db
from configs import cfg
import pyrogram
from pyrogram import errors  # Add this import
from pyrogram.errors import FloodWait

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Pyrogram Client
app = Client(
    "approver",
    api_id=cfg.API_ID,
    api_hash=cfg.API_HASH,
    bot_token=cfg.BOT_TOKEN,
    workers=1000,
    max_concurrent_transmissions=100
)

# Cache system
user_cache: Dict[int, bool] = {}
group_cache: Dict[int, bool] = {}
broadcast_state = {
    'active': False,
    'current_position': 0,
    'total_users': 0,
    'success': 0,
    'failed': 0,
    'deactivated': 0,
    'message': None,
    'is_forward': False,
    'start_time': 0
}

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Core Functions ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def save_state():
    """Save broadcast state to file"""
    with open('broadcast_state.pkl', 'wb') as f:
        pickle.dump(broadcast_state, f)

async def load_state():
    """Load broadcast state from file"""
    if os.path.exists('broadcast_state.pkl'):
        with open('broadcast_state.pkl', 'rb') as f:
            return pickle.load(f)
    return None

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Join Request Handler ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_chat_join_request(filters.group | filters.channel & ~filters.private)
async def approve_request(_, message):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Add to database and cache
        await db.add_user(user_id)
        await db.add_group(chat_id)
        user_cache[user_id] = True
        group_cache[chat_id] = True
        
        try:
            # Try to approve the request
           try:
               await app.approve_chat_join_request(chat_id, user_id)
               logger.info(f"Approved join request from {user_id} in {chat_id}")
           except errors.UserAlreadyParticipant:
               logger.info(f"User {user_id} already in chat {chat_id}")
               return
           except FloodWait as e:
               logger.warning(f"Flood wait: sleeping for {e.value} seconds")
               await asyncio.sleep(e.value)
               return await approve_request(_, message)
           except Exception as e:
               logger.error(f"Approval error for {user_id}: {e}")
               return
        
        # Send welcome message
        buttons = [
            [InlineKeyboardButton("🎥 GROUP 1 🎥", url="https://t.me/+Acp3hogTGpcyOTFl")],
            [InlineKeyboardButton("🎥 NEW MOVIES 🎥", url="https://t.me/CINEMA_HUB_NEWMOVIES")]
        ]
        
        try:
            await app.send_message(
                user_id,
                f"**Hello {message.from_user.mention}!\nYour request to join {message.chat.title} was approved.**",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            logger.error(f"Welcome message failed: {e}")

    except Exception as e:
        logger.error(f"Approval processing error: {e}", exc_info=True)

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Start Command ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("start"))
async def start_command(_, message: Message):
    try:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🗯 Channel", url="https://t.me/REQUSET_ACCEPT_BOT"),
                InlineKeyboardButton("💬 Support", url="https://t.me/REQUSET_ACCEPT_BOT")
            ],
            [InlineKeyboardButton("➕ Add me to Chat ➕", url="https://t.me/REQUSET_ACCEPT_BOT")]
        ]) if message.chat.type == enums.ChatType.PRIVATE else InlineKeyboardMarkup([
            [InlineKeyboardButton("💁‍♂️ Start privately", url="https://t.me/Auto_Request_Acceptor_BOT")]
        ])
        
        await message.reply_text(
            f"**🦊 Hello {message.from_user.mention}!\nI'm an auto-approval bot!**",
            reply_markup=keyboard
        )
        
        # Add user to database if not exists
        if message.from_user.id not in user_cache:
            await db.add_user(message.from_user.id)
            user_cache[message.from_user.id] = True
            
    except Exception as e:
        logger.error(f"Start command error: {e}")

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Broadcast System ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command(["bcast", "fcast"]) & filters.user(cfg.SUDO_USERS))
async def broadcast_command(_, message: Message):
    if broadcast_state['active']:
        await message.reply_text("⚠️ Broadcast already in progress!")
        return
    
    if not message.reply_to_message:
        await message.reply_text("ℹ️ Reply to a message to broadcast it")
        return
    
    # Initialize broadcast
    broadcast_state.update({
        'active': True,
        'current_position': 0,
        'total_users': await db.count_users(),
        'success': 0,
        'failed': 0,
        'deactivated': 0,
        'message': message.reply_to_message,
        'is_forward': message.command[0] == "fcast",
        'start_time': time.time()
    })
    
    await save_state()
    
    # Start broadcast
    control_buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton("🛑 Cancel", callback_data="cancel_bcast")
    ]])
    
    progress_msg = await message.reply_text(
        "📢 Starting broadcast...",
        reply_markup=control_buttons
    )
    
    asyncio.create_task(run_broadcast(progress_msg))

async def run_broadcast(progress_msg: Message):
    try:
        # Get all user IDs
        user_ids = []
        async for user in db.users.find({}, {'user_id': 1}):
            user_ids.append(user['user_id'])
        
        # Process in chunks
        chunk_size = 100
        while broadcast_state['current_position'] < len(user_ids) and broadcast_state['active']:  # REMOVED EXTRA (
            chunk = user_ids[broadcast_state['current_position']:broadcast_state['current_position']+chunk_size]
            
            # Process chunk
            results = await asyncio.gather(
                *[send_broadcast(user_id) for user_id in chunk],
                return_exceptions=True
            )
            
            # Update stats
            for result in results:
                if result == "success":
                    broadcast_state['success'] += 1
                elif result == "deactivated":
                    broadcast_state['deactivated'] += 1
                else:
                    broadcast_state['failed'] += 1
            
            broadcast_state['current_position'] += len(chunk)
            await save_state()
            
            # Update progress
            progress = (
                f"📊 Progress: {broadcast_state['current_position']}/{len(user_ids)}\n"
                f"✅ Success: {broadcast_state['success']}\n"
                f"❌ Failed: {broadcast_state['failed']}\n"
                f"👻 Deactivated: {broadcast_state['deactivated']}"
            )
            await progress_msg.edit_text(progress)
            
            await asyncio.sleep(0.1)  # Small delay
        
        # Broadcast complete
        await progress_msg.edit_text(
            f"🎉 Broadcast complete!\n"
            f"⏱️ Time: {time.time()-broadcast_state['start_time']:.1f}s\n"
            f"✅ Success: {broadcast_state['success']}\n"
            f"❌ Failed: {broadcast_state['failed']}\n"
            f"👻 Deactivated: {broadcast_state['deactivated']}"
        )
        
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        await progress_msg.edit_text(f"⚠️ Broadcast failed: {e}")
    finally:
        broadcast_state['active'] = False
        await save_state()

async def send_broadcast(user_id: int):
    try:
        if broadcast_state['is_forward']:
            await broadcast_state['message'].forward(user_id)
        else:
            await broadcast_state['message'].copy(user_id)
        return "success"
    except errors.InputUserDeactivated:
        await db.remove_user(user_id)
        return "deactivated"
    except errors.UserIsBlocked:
        await db.remove_user(user_id)
        return "deactivated"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await send_broadcast(user_id)
    except Exception:
        return "failed"

@app.on_callback_query(filters.regex("cancel_bcast"))
async def cancel_broadcast(_, query: CallbackQuery):
    if broadcast_state['active']:
        broadcast_state['active'] = False
        await query.answer("Broadcast cancelled!")
        await query.message.edit_text("🛑 Broadcast cancelled!")
    else:
        await query.answer("No active broadcast")

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Startup ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Startup ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def load_cache():
    """Load users and groups into cache"""
    global user_cache, group_cache
    
    try:
        # Load users
        user_cache.clear()
        async for user in db.users.find({}, {'user_id': 1}):
            user_cache[user['user_id']] = True
            
        # Load groups
        group_cache.clear()
        async for group in db.groups.find({}, {'chat_id': 1}):
            group_cache[group['chat_id']] = True
            
        logger.info(f"Cache loaded - Users: {len(user_cache)}, Groups: {len(group_cache)}")
        
        # Resume interrupted broadcast
        saved_state = await load_state()
        if saved_state and saved_state.get('active'):
            broadcast_state.update(saved_state)
            logger.info("Resuming broadcast...")
            
            dummy_msg = Message(
                id=0,
                chat=await app.get_chat(cfg.SUDO_USERS[0]),
                from_user=await app.get_me(),
                date=int(time.time())
            )
            asyncio.create_task(run_broadcast(dummy_msg))
            
    except Exception as e:
        logger.error(f"Cache load error: {e}")

@app.on_raw_update()
async def startup(client, update, users_chats, _):  # Now accepts all 4 parameters
    """Initialize on startup"""
    if not user_cache or not group_cache:
        await load_cache()

if __name__ == "__main__":
    logger.info("Starting bot...")
    app.run()
