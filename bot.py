from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram import filters, Client, errors, enums
from pyrogram.errors import UserNotParticipant
from pyrogram.errors.exceptions.flood_420 import FloodWait
from database import add_user, add_group, all_users, all_groups, users, remove_user
from configs import cfg
import random, asyncio

app = Client(
    "approver",
    api_id=cfg.API_ID,
    api_hash=cfg.API_HASH,
    bot_token=cfg.BOT_TOKEN
)

gif = [
    'https://telegra.ph/file/f7c587a11397f095a48a1.jpg'
]


#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Main process ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_chat_join_request(filters.group | filters.channel & ~filters.private)
async def approve(_, m : Message):
    op = m.chat
    kk = m.from_user
    try:
        add_group(m.chat.id)
        await app.approve_chat_join_request(op.id, kk.id)
        buttons = [[            
            InlineKeyboardButton("🎥 GROUP 1 🎥", url="https://t.me/+Acp3hogTGpcyOTFl"),
            ],[
            InlineKeyboardButton("🎥 NEW MOVIES 🎥", url="https://t.me/CINEMA_HUB_NEWMOVIES")
        ]]
             
        await app.send_message(kk.id,f"**Hello {m.from_user.mention}!\nYou Request To Join {m.chat.title} Was Approved.🏻",
        reply_markup = InlineKeyboardMarkup(buttons))
        add_user(kk.id)
    except errors.PeerIdInvalid as e:
        print("user isn't start bot(means group)")
    except Exception as err:
        print(str(err))    
 
#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Start ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("start"))
async def op(_, m :Message):
    try:
        if m.chat.type == enums.ChatType.PRIVATE:
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🗯 Channel", url="https://t.me/REQUSET_ACCEPT_BOT"),
                        InlineKeyboardButton("💬 Support", url="https://t.me/REQUSET_ACCEPT_BOT")
                    ],[
                        InlineKeyboardButton("➕ Add me to your Chat ➕", url="https://t.me/REQUSET_ACCEPT_BOT")
                    ]
                ]
            )
            add_user(m.from_user.id)
            await m.reply_text(text="**🦊 Hello {}!\nI'm an auto approve Admin Join Requests Bot..\nI can approve users in Groups/Channels.Add me to your chat and promote me to admin with add members permission.**".format(m.from_user.mention, "https://t.me/telegram/153"), reply_markup=keyboard)
    
        elif m.chat.type == enums.ChatType.GROUP or enums.ChatType.SUPERGROUP:
            keyboar = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("💁‍♂️ Start me private 💁‍♂️", url="https://t.me/Auto_Request_Acceptor_BOT")
                    ]
                ]
            )
            add_group(m.chat.id)
            await m.reply_text("**🦊 Hello {}!\nwrite me private for more details**".format(m.from_user.first_name), reply_markup=keyboar)
        print(m.from_user.first_name +" Is started Your Bot!")

    except UserNotParticipant:
        key = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🍀 Check Again 🍀", "chk")
                ]
            ]
        )

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ callback ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_callback_query(filters.regex("chk"))
async def chk(_, cb : CallbackQuery):
    try:
        if cb.message.chat.type == enums.ChatType.PRIVATE:
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🗯 Channel", url="https://t.me/REQUSET_ACCEPT_BOT"),
                        InlineKeyboardButton("💬 Support", url="https://t.me/REQUSET_ACCEPT_BOT")
                    ],[
                        InlineKeyboardButton("➕ Add me to your Chat ➕", url="https://t.me/REQUSET_ACCEPT_BOT")
                    ]
                ]
            )
            add_user(cb.from_user.id)
            await cb.message.edit("**🦊 Hello {}!\nI'm an auto approve [Admin Join Requests]({}) Bot.\nI can approve users in Groups/Channels.Add me to your chat and promote me to admin with add members permission.\n\n__Powerd By : @REQUSET_ACCEPT_BOT**".format(cb.from_user.mention, "https://t.me/telegram/153"), reply_markup=keyboard, disable_web_page_preview=True)
        print(cb.from_user.first_name +" Is started Your Bot!")
    except UserNotParticipant:
        await cb.answer("🙅‍♂️ You are not joined to channel join and try again. 🙅‍♂️")

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ info ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("users") & filters.user(cfg.SUDO))
async def dbtool(_, m : Message):
    xx = all_users()
    x = all_groups()
    tot = int(xx + x)
    await m.reply_text(text=f"""
🍀 Chats Stats 🍀
🙋‍♂️ Users : `{xx}`
👥 Groups : `{x}`
🚧 Total users & groups : `{tot}` """)

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Broadcast ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("bcast") & filters.user(cfg.SUDO))
async def bcast(_, m : Message):
    allusers = users
    lel = await m.reply_text("`⚡️ Processing...`")
    success = 0
    failed = 0
    deactivated = 0
    blocked = 0
    for usrs in allusers.find():
        try:
            userid = usrs["user_id"]
            #print(int(userid))
            if m.command[0] == "bcast":
                await m.reply_to_message.copy(int(userid))
            success +=1
        except FloodWait as ex:
            await asyncio.sleep(ex.value)
            if m.command[0] == "bcast":
                await m.reply_to_message.copy(int(userid))
        except errors.InputUserDeactivated:
            deactivated +=1
            remove_user(userid)
        except errors.UserIsBlocked:
            blocked +=1
        except Exception as e:
            print(e)
            failed +=1

    await lel.edit(f"✅Successfull to `{success}` users.\n❌ Faild to `{failed}` users.\n👾 Found `{blocked}` Blocked users \n👻 Found `{deactivated}` Deactivated users.")

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Broadcast Forward ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("fcast") & filters.user(cfg.SUDO))
async def fcast(_, m : Message):
    allusers = users
    lel = await m.reply_text("`⚡️ Processing...`")
    success = 0
    failed = 0
    deactivated = 0
    blocked = 0
    for usrs in allusers.find():
        try:
            userid = usrs["user_id"]
            #print(int(userid))
            if m.command[0] == "fcast":
                await m.reply_to_message.forward(int(userid))
            success +=1
        except FloodWait as ex:
            await asyncio.sleep(ex.value)
            if m.command[0] == "fcast":
                await m.reply_to_message.forward(int(userid))
        except errors.InputUserDeactivated:
            deactivated +=1
            remove_user(userid)
        except errors.UserIsBlocked:
            blocked +=1
        except Exception as e:
            print(e)
            failed +=1

    await lel.edit(f"✅Successfull to `{success}` users.\n❌ Faild to `{failed}` users.\n👾 Found `{blocked}` Blocked users \n👻 Found `{deactivated}` Deactivated users.")

print("I'm Alive Now!")
app.run()


# Optimized broadcast handler for Pyrogram bot
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked
import asyncio, json, os
from database import all_users, remove_user
from configs import cfg

broadcast_state = {
    "is_running": False,
    "cancel": False,
    "current": 0,
    "success": 0,
    "failed": 0,
    "total": 0
}

BCAST_STATE_FILE = "broadcast_status.json"

# Save progress to file (for resuming)
def save_state():
    with open(BCAST_STATE_FILE, 'w') as f:
        json.dump(broadcast_state, f)

# Load state if exists (on bot startup)
def load_state():
    if os.path.exists(BCAST_STATE_FILE):
        with open(BCAST_STATE_FILE, 'r') as f:
            data = json.load(f)
            broadcast_state.update(data)

@app.on_message(filters.command("bcast") & filters.user(cfg.SUDO))
async def broadcast_handler(client: Client, msg: Message):
    if broadcast_state["is_running"]:
        return await msg.reply("🚫 A broadcast is already in progress.")

    users = all_users()
    if not users:
        return await msg.reply("No users in the database.")

    content = msg.reply_to_message
    if not content:
        return await msg.reply("Reply to a message to broadcast.")

    broadcast_state.update({
        "is_running": True,
        "cancel": False,
        "current": 0,
        "success": 0,
        "failed": 0,
        "total": len(users)
    })
    save_state()

    status_msg = await msg.reply("📣 Starting broadcast...", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_bcast")]
    ]))

    for user_id in users:
        if broadcast_state["cancel"]:
            break

        try:
            await content.copy(chat_id=user_id)
            broadcast_state["success"] += 1
        except UserIsBlocked:
            remove_user(user_id)
            broadcast_state["failed"] += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except:
            broadcast_state["failed"] += 1

        broadcast_state["current"] += 1
        if broadcast_state["current"] % 10 == 0:
            await status_msg.edit_text(
            await status_msg.edit_text(
                f"""📊 Broadcast Status:

✅ Success: {broadcast_state['success']}
❌ Failed: {broadcast_state['failed']}
📤 Sent: {broadcast_state['current']}/{broadcast_state['total']}""",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel_bcast")]
                ])
",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel_bcast")]
                ])
            )
        save_state()

    broadcast_state["is_running"] = False
    await status_msg.edit_text(
        f"✅ Broadcast Finished!

"
        f"✅ Success: {broadcast_state['success']}
"
        f"❌ Failed: {broadcast_state['failed']}
"
        f"📤 Total: {broadcast_state['total']}"
    )
    os.remove(BCAST_STATE_FILE)

@app.on_callback_query(filters.regex("cancel_bcast") & filters.user(cfg.SUDO))
async def cancel_broadcast(_, cb: CallbackQuery):
    broadcast_state["cancel"] = True
    await cb.message.edit_text("🚫 Broadcast canceled by admin.")
    await cb.answer("Canceled.")

# Load saved state on startup to resume if needed
load_state()
