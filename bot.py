import asyncio
import time
from typing import List, Optional, Dict
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram import filters, Client, errors, enums
from pyrogram.errors import FloodWait
from database import add_user, add_group, all_users, all_groups, users, groups, remove_user
from configs import cfg
import logging
import pickle
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Performance tuning
MAX_CONCURRENT_TASKS = 500  # Adjust based on your server capacity
BROADCAST_CHUNK_SIZE = 100
BROADCAST_DELAY = 0.02  # Seconds between chunks

app = Client(
    "approver",
    api_id=cfg.API_ID,
    api_hash=cfg.API_HASH,
    bot_token=cfg.BOT_TOKEN,
    workers=1000,  # High number for concurrent processing
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
    """Save broadcast state to file for recovery"""
    with open('broadcast_state.pkl', 'wb') as f:
        pickle.dump(broadcast_state, f)

async def load_state():
    """Load broadcast state from file"""
    if os.path.exists('broadcast_state.pkl'):
        with open('broadcast_state.pkl', 'rb') as f:
            return pickle.load(f)
    return None

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Join Request Handler ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_chat_join_request(filters.group | filters.channel & ~filters.private)
async def approve(_, m: Message):
    """Ultra-fast join request approval with bulk processing"""
    try:
        user_id = m.from_user.id
        chat_id = m.chat.id
        
        # Add to cache if not present
        if chat_id not in group_cache:
            add_group(chat_id)
            group_cache[chat_id] = True
        
        # Process approval and welcome message concurrently
        await asyncio.gather(
            app.approve_chat_join_request(chat_id, user_id),
            send_welcome_message(user_id, m),
            return_exceptions=True  # Prevent one failure from blocking others
        )
        
        if user_id not in user_cache:
            add_user(user_id)
            user_cache[user_id] = True
            
    except Exception as err:
        logger.error(f"Error in approve: {str(err)}", exc_info=True)

async def send_welcome_message(user_id: int, m: Message):
    """Optimized welcome message sender"""
    try:
        buttons = [
            [InlineKeyboardButton("🎥 GROUP 1 🎥", url="https://t.me/+Acp3hogTGpcyOTFl")],
            [InlineKeyboardButton("🎥 NEW MOVIES 🎥", url="https://t.me/CINEMA_HUB_NEWMOVIES")]
        ]
        
        await app.send_message(
            user_id,
            f"**Hello {m.from_user.mention}!\nYour request to join {m.chat.title} was approved.**",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        logger.error(f"Welcome message failed for {user_id}: {str(e)}")

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Start Command ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("start"))
async def start(_, m: Message):
    """Optimized start command without force subscription"""
    try:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🗯 Channel", url="https://t.me/REQUSET_ACCEPT_BOT"),
                InlineKeyboardButton("💬 Support", url="https://t.me/REQUSET_ACCEPT_BOT")
            ],
            [InlineKeyboardButton("➕ Add me to your Chat ➕", url="https://t.me/REQUSET_ACCEPT_BOT")]
        ]) if m.chat.type == enums.ChatType.PRIVATE else InlineKeyboardMarkup([
            [InlineKeyboardButton("💁‍♂️ Start me private 💁‍♂️", url="https://t.me/Auto_Request_Acceptor_BOT")]
        ])
        
        if m.from_user.id not in user_cache:
            add_user(m.from_user.id)
            user_cache[m.from_user.id] = True
        
        await m.reply_text(
            "**🦊 Hello {}!\nI'm an ultra-fast auto approval bot!**".format(m.from_user.mention),
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Start command error: {str(e)}")

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Enhanced Broadcast System ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command(["bcast", "fcast"]) & filters.user(cfg.SUDO))
async def broadcast_handler(_, m: Message):
    """Advanced broadcast system with resume capability"""
    if broadcast_state['active']:
        await m.reply_text("⚠️ A broadcast is already in progress!")
        return
    
    if not m.reply_to_message:
        await m.reply_text("ℹ️ Please reply to a message to broadcast it.")
        return
    
    # Initialize broadcast state
    broadcast_state.update({
        'active': True,
        'current_position': 0,
        'total_users': users.count_documents({}),
        'success': 0,
        'failed': 0,
        'deactivated': 0,
        'message': m.reply_to_message,
        'is_forward': m.command[0] == "fcast",
        'start_time': time.time()
    })
    
    await save_state()
    
    # Create control buttons
    control_buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton("🛑 Cancel Broadcast", callback_data="cancel_bcast")
    ]])
    
    progress_msg = await m.reply_text(
        "📢 Starting broadcast...",
        reply_markup=control_buttons
    )
    
    # Process broadcast in background
    asyncio.create_task(process_broadcast(progress_msg))

async def process_broadcast(progress_msg: Message):
    """Process broadcast in chunks with resume capability"""
    try:
        user_ids = [user["user_id"] async for user in users.find({}, {'user_id': 1})]
        
        while broadcast_state['current_position'] < len(user_ids) and broadcast_state['active']:
            chunk = user_ids[
                broadcast_state['current_position']:
                broadcast_state['current_position'] + BROADCAST_CHUNK_SIZE
            ]
            
            # Process chunk concurrently
            results = await asyncio.gather(
                *[send_broadcast(user_id) for user_id in chunk],
                return_exceptions=True
            )
            
            # Update statistics
            for result in results:
                if isinstance(result, Exception):
                    broadcast_state['failed'] += 1
                    logger.error(f"Broadcast error: {str(result)}")
                elif result == "deactivated":
                    broadcast_state['deactivated'] += 1
                elif result == "success":
                    broadcast_state['success'] += 1
            
            broadcast_state['current_position'] += len(chunk)
            await save_state()
            
            # Update progress
            elapsed = time.time() - broadcast_state['start_time']
            remaining = (len(user_ids) - broadcast_state['current_position']) * (elapsed / broadcast_state['current_position']) if broadcast_state['current_position'] > 0 else 0
            
            progress_text = (
                f"📊 Broadcast Progress\n\n"
                f"✅ Success: {broadcast_state['success']}\n"
                f"❌ Failed: {broadcast_state['failed']}\n"
                f"👻 Deactivated: {broadcast_state['deactivated']}\n"
                f"⏳ Remaining: {int(remaining)}s\n"
                f"📤 Processed: {broadcast_state['current_position']}/{len(user_ids)}"
            )
            
            try:
                await progress_msg.edit_text(progress_text)
            except Exception as e:
                logger.error(f"Progress update failed: {str(e)}")
            
            await asyncio.sleep(BROADCAST_DELAY)
        
        # Broadcast complete
        final_text = (
            f"🎉 Broadcast Complete!\n\n"
            f"✅ Success: {broadcast_state['success']}\n"
            f"❌ Failed: {broadcast_state['failed']}\n"
            f"👻 Deactivated: {broadcast_state['deactivated']}\n"
            f"⏱️ Total Time: {int(time.time() - broadcast_state['start_time'])}s"
        )
        
        await progress_msg.edit_text(final_text)
        
    except Exception as e:
        logger.error(f"Broadcast processing failed: {str(e)}", exc_info=True)
        await progress_msg.edit_text(f"⚠️ Broadcast failed: {str(e)}")
    finally:
        broadcast_state['active'] = False
        await save_state()

async def send_broadcast(user_id: int):
    """Send broadcast message to a single user with error handling"""
    try:
        if broadcast_state['is_forward']:
            await broadcast_state['message'].forward(user_id)
        else:
            await broadcast_state['message'].copy(user_id)
        return "success"
    except errors.InputUserDeactivated:
        # Remove deactivated users
        remove_user(user_id)
        if user_id in user_cache:
            del user_cache[user_id]
        return "deactivated"
    except errors.UserIsBlocked:
        # Remove blocked users
        remove_user(user_id)
        if user_id in user_cache:
            del user_cache[user_id]
        return "deactivated"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await send_broadcast(user_id)
    except Exception as e:
        raise e

@app.on_callback_query(filters.regex("cancel_bcast"))
async def cancel_broadcast(_, cb: CallbackQuery):
    """Handle broadcast cancellation"""
    if broadcast_state['active']:
        broadcast_state['active'] = False
        await cb.answer("Broadcast cancelled!")
        await cb.message.edit_text(
            "🛑 Broadcast Cancelled!\n\n"
            f"✅ Success: {broadcast_state['success']}\n"
            f"❌ Failed: {broadcast_state['failed']}\n"
            f"👻 Deactivated: {broadcast_state['deactivated']}\n"
            f"⏱️ Time Elapsed: {int(time.time() - broadcast_state['start_time'])}s"
        )
    else:
        await cb.answer("No active broadcast to cancel!")

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Bot Startup ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def startup_tasks():
    """Initialize bot state on startup"""
    global user_cache, group_cache
    
    try:
        # Fixed MongoDB queries - Proper async handling
        users_cursor = users.find({}, {'user_id': 1})
        user_cache = {u["user_id"]: True async for u in users_cursor}
        
        groups_cursor = groups.find({}, {'group_id': 1})
        group_cache = {g["group_id"]: True async for g in groups_cursor}
        
        logger.info(f"Cache warmed up: {len(user_cache)} users, {len(group_cache)} groups")
        
        # Check for incomplete broadcast
        saved_state = await load_state()
        if saved_state and saved_state.get('active'):
            broadcast_state.update(saved_state)
            logger.info("Resuming interrupted broadcast...")
            
            dummy_msg = Message(
                id=0,
                chat=await app.get_chat(cfg.SUDO),
                from_user=await app.get_me(),
                date=int(time.time())
            )
            asyncio.create_task(process_broadcast(dummy_msg))
            
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        user_cache = {}
        group_cache = {}

@app.on_raw_update()
async def cache_warmup(_, update, *args):
    """Warm up cache on startup"""
    if not user_cache or not group_cache:
        await startup_tasks()

print("🚀 Ultra-Fast Bot is now running!")
app.run()
