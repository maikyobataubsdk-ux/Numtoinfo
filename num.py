#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║          🔥  Ultra OSINT Bot  v5.0                      ║
║          Built by @xbroze                               ║
╚══════════════════════════════════════════════════════════╝

Features:
  ✅ Dual source — Primary Bot + Backup Group
  ✅ Group-only (100+ members required)
  ✅ Force Subscribe via /setfs
  ✅ Credit system (2 free, 1/search, referral +1)
  ✅ Premium mode (unlimited searches)
  ✅ 23 OSINT commands
  ✅ Result via deeplink "Click Here" button
  ✅ Broadcast, stats, addcredits, setpremium

Requirements:
    pip install pyrogram tgcrypto
    Python 3.10+
"""

import asyncio, re, sqlite3, uuid, logging, functools, json

from pyrogram import Client, filters, enums, idle
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    Message, CallbackQuery
)
from pyrogram.errors import UserNotParticipant, FloodWait

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════
#   ⚙️  CONFIG  —  Apni values yahan bharo
# ══════════════════════════════════════════════════════════════
API_ID          = 1234567
API_HASH        = "your_api_hash_here"
BOT_TOKEN       = "your_bot_token_here"
SESSION_STRING  = "your_session_string_here"   # Userbot session

OWNER_ID        = 123456789          # Tumhara Telegram numeric ID
OWNER_USERNAME  = "@xbroze"
BOT_USERNAME    = "YourBotUsername"  # Without @; auto-set on startup

PRIMARY_BOT         = "@UkraineToOsint_bot"
BACKUP_GROUP_INVITE = "https://t.me/+EcpltYqKYoVjODVl"

FREE_CREDITS = 2     # New user ko milne wale free credits
MIN_MEMBERS  = 100   # Group me minimum members

# ══════════════════════════════════════════════════════════════
#   🗄️  DATABASE
# ══════════════════════════════════════════════════════════════
_db  = sqlite3.connect("osint.db", check_same_thread=False)
_db.row_factory = sqlite3.Row
_c   = _db.cursor()

_c.executescript("""
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS users (
    uid     INTEGER PRIMARY KEY,
    uname   TEXT    DEFAULT '',
    fname   TEXT    DEFAULT '',
    credits INTEGER DEFAULT 2,
    premium INTEGER DEFAULT 0,
    ref_by  INTEGER DEFAULT NULL,
    ts      TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    k TEXT PRIMARY KEY,
    v TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS rcache (
    rid    TEXT PRIMARY KEY,
    uid    INTEGER,
    qcmd   TEXT,
    result TEXT,
    ts     TEXT DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO settings(k) VALUES
    ('force_ch'), ('force_gp'), ('backup_gid');
""")
_db.commit()

# ── DB Helpers ──────────────────────────────────────────────────
def u_get(uid: int):
    _c.execute("SELECT * FROM users WHERE uid=?", (uid,))
    return _c.fetchone()

def u_reg(uid: int, uname: str, fname: str, ref: int = None):
    _c.execute(
        "INSERT OR IGNORE INTO users(uid,uname,fname,credits,ref_by) VALUES(?,?,?,?,?)",
        (uid, uname or "", fname or "User", FREE_CREDITS, ref)
    )
    _db.commit()
    # Referral bonus
    if ref and ref != uid and u_get(ref):
        _c.execute("UPDATE users SET credits=credits+1 WHERE uid=?", (ref,))
        _db.commit()

def s_get(k: str):
    _c.execute("SELECT v FROM settings WHERE k=?", (k,))
    r = _c.fetchone()
    return r["v"] if r else None

def s_set(k: str, v):
    _c.execute("UPDATE settings SET v=? WHERE k=?", (v, k))
    _db.commit()

def cr_use(uid: int) -> bool:
    u = u_get(uid)
    if not u: return False
    if u["premium"]: return True           # Premium = unlimited
    if u["credits"] <= 0: return False
    _c.execute("UPDATE users SET credits=credits-1 WHERE uid=?", (uid,))
    _db.commit()
    return True

def cr_refund(uid: int):
    _c.execute(
        "UPDATE users SET credits=credits+1 WHERE uid=? AND premium=0", (uid,)
    )
    _db.commit()

def r_save(rid: str, uid: int, qcmd: str, result: str):
    _c.execute(
        "INSERT OR REPLACE INTO rcache(rid,uid,qcmd,result) VALUES(?,?,?,?)",
        (rid, uid, qcmd, result)
    )
    _db.commit()

def r_get(rid: str):
    _c.execute("SELECT * FROM rcache WHERE rid=?", (rid,))
    return _c.fetchone()

# ══════════════════════════════════════════════════════════════
#   🤖  CLIENTS
# ══════════════════════════════════════════════════════════════
bot     = Client("_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = Client("_ub",  api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

_backup_gid: int | None = None   # Set at startup

# ══════════════════════════════════════════════════════════════
#   📋  COMMAND REGISTRY
#   (slash_cmd, description, example_input)
# ══════════════════════════════════════════════════════════════
CMDS: dict[str, tuple[str, str, str]] = {
    "num":     ("/num",     "📞 NUMBER TO DETAILS",              "7292739393"),
    "aadhar":  ("/aadhar",  "⁉️ AADHAR TO INFO",               "123412341234"),
    "tg":      ("/tg",      "🧑‍💻 TG UID → NUMBER",           "username_or_id"),
    "rc":      ("/rc",      "🚘 RC DETAILS",                    "MH12AB1234"),
    "vehicle": ("/vehicle", "🔗 VEHICLE → OWNER ADDRESS",       "MH12AB1234"),
    "family":  ("/family",  "👨‍👩‍👧 AADHAR → FAMILY DETAILS",  "123412341234"),
    "email":   ("/email",   "📧 EMAIL TO INFO",                 "test@gmail.com"),
    "vnum":    ("/vnum",    "📱 VEHICLE → OWNER NUMBER",        "MH12AB1234"),
    "leak":    ("/leak",    "🔓 ADV OSINT SEARCH",              "query_here"),
    "lpg":     ("/lpg",     "🛢️ LPG GAS INFO",                 "7292739393"),
    "mp":      ("/mp",      "🖼️ MP MOBILE → PIC + FAMILY",    "7292739393"),
    "challan": ("/challan", "🚔 CHALLAN INFO + PDF",            "MH12AB1234"),
    "hp":      ("/hp",      "🛢️ HP PIPELINE INFO",             "7292739393"),
    "chassis": ("/chassis", "⚙️ VEHICLE FROM CHASSIS NO.",      "CHASSIS123"),
    "eng":     ("/eng",     "🔧 VEHICLE FROM ENGINE NO.",       "ENGINE123"),
    "ig":      ("/ig",      "📸 INSTA ID → DETAILS",           "insta_username"),
    "pvtig":   ("/pvtig",   "🔒 PVT INSTA FOLLOWER LOOKUP",    "insta_username"),
    "pan":     ("/pan",     "🪪 PAN INFO",                      "ABCDE1234F"),
    "bh":      ("/bh",      "⛽ BHARAT PETROLEUM LOOKUP",       "7292739393"),
    "ind":     ("/ind",     "⛽ INDIAN PETROLEUM LOOKUP",       "7292739393"),
    "upi":     ("/upi",     "💸 UPI ID INFO",                  "name@upi"),
    "num2upi": ("/num2upi", "💸 NUMBER → UPI IDs",             "7292739393"),
    "pan2ad":  ("/pan2ad",  "🪪 PAN → AADHAAR",               "ABCDE1234F"),
}

# Primary bot supports only these 4 via button-trigger flow
PRIMARY_TRIGGERS: dict[str, str] = {
    "num":     "📞 Number to Info",
    "aadhar":  "⁉️ Aadhar to Info",
    "tg":      "🧑‍💻 TG to Number",
    "vehicle": "🔗 Vehicle to Info",
}

# ══════════════════════════════════════════════════════════════
#   🎙️  BACKUP GROUP RESPONSE LISTENER  (userbot side)
# ══════════════════════════════════════════════════════════════
_grp_lock = asyncio.Lock()
_grp_fut: asyncio.Future | None = None

@userbot.on_message(~filters.me)
async def _ub_listener(_, msg: Message):
    global _grp_fut, _backup_gid
    # Only care about the backup group
    if not _backup_gid or msg.chat.id != _backup_gid:
        return
    if not _grp_fut or _grp_fut.done():
        return

    text = msg.text or msg.caption or ""
    if not text:
        return

    is_bot  = bool(msg.from_user and msg.from_user.is_bot)
    is_data = any(x in text for x in ["{", "Error", "not found", "Invalid", "No data"])

    if is_bot or is_data:
        try:
            _grp_fut.set_result(text)
        except Exception:
            pass

# ══════════════════════════════════════════════════════════════
#   📡  DATA FETCHERS
# ══════════════════════════════════════════════════════════════
async def _safe_send(target, text: str, delay: float = 0) -> bool:
    try:
        await userbot.send_message(target, text)
        if delay:
            await asyncio.sleep(delay)
        return True
    except FloodWait as fw:
        log.warning(f"FloodWait {fw.value}s")
        await asyncio.sleep(fw.value + 1)
        return False
    except Exception as e:
        log.warning(f"send_message error: {e}")
        return False


async def fetch_primary(cmd: str, query: str) -> str | None:
    """Original button-trigger flow for the primary bot."""
    if cmd not in PRIMARY_TRIGGERS:
        return None
    try:
        # Step 1: Button trigger
        await _safe_send(PRIMARY_BOT, PRIMARY_TRIGGERS[cmd], delay=2)
        # Step 2: Actual input
        await _safe_send(PRIMARY_BOT, query, delay=5)
        # Step 3: Read response
        async for m in userbot.get_chat_history(PRIMARY_BOT, limit=5):
            t = m.text or m.caption or ""
            if any(x in t for x in ["{", "Error", "not found", "No data", "API Error"]):
                return t
    except Exception as e:
        log.warning(f"Primary fetch error: {e}")
    return None


async def fetch_backup(cmd: str, query: str) -> str | None:
    """Send /cmd query to backup group; wait for bot response."""
    global _grp_fut, _backup_gid
    if not _backup_gid:
        return None

    pfx = CMDS[cmd][0]                          # e.g. "/num"
    cmd_text = f"{pfx} {query}"

    async with _grp_lock:
        loop = asyncio.get_running_loop()
        _grp_fut = loop.create_future()
        try:
            if not await _safe_send(_backup_gid, cmd_text):
                return None
            return await asyncio.wait_for(asyncio.shield(_grp_fut), timeout=15)
        except asyncio.TimeoutError:
            log.warning(f"Backup timeout: {cmd_text}")
        except Exception as e:
            log.warning(f"Backup error: {e}")
        finally:
            _grp_fut = None
    return None


async def get_data(cmd: str, query: str) -> tuple[str | None, str]:
    """Try primary first, fallback to backup group."""
    raw = await fetch_primary(cmd, query)
    if raw:
        return raw, "🟢 Primary"
    raw = await fetch_backup(cmd, query)
    if raw:
        return raw, "🔵 Backup"
    return None, "❌"


def extract_json(text: str) -> str | None:
    m = re.search(r'\{[\s\S]*\}', text)
    if not m:
        return None
    try:
        return json.dumps(json.loads(m.group()), indent=2, ensure_ascii=False)
    except Exception:
        return m.group()

# ══════════════════════════════════════════════════════════════
#   🛡️  FORCE SUBSCRIBE
# ══════════════════════════════════════════════════════════════
async def fs_check(uid: int) -> tuple[bool, str]:
    for k in ("force_ch", "force_gp"):
        t = s_get(k)
        if not t:
            continue
        try:
            mb = await bot.get_chat_member(t, uid)
            if mb.status in (enums.ChatMemberStatus.BANNED,
                             enums.ChatMemberStatus.LEFT):
                return False, t
        except UserNotParticipant:
            return False, t
        except Exception:
            pass
    return True, ""


async def fs_button(target: str) -> InlineKeyboardMarkup:
    try:
        inv = await bot.export_chat_invite_link(target)
        ch  = await bot.get_chat(target)
        lbl = f"👉 Join {ch.title}"
    except Exception:
        inv = f"https://t.me/{target.lstrip('@')}"
        lbl = "👉 Join Required Channel/Group"
    return InlineKeyboardMarkup([[InlineKeyboardButton(lbl, url=inv)]])

# ══════════════════════════════════════════════════════════════
#   🎯  MAIN GROUP DISPATCHER  —  all OSINT commands
# ══════════════════════════════════════════════════════════════
@bot.on_message(filters.group & filters.text & ~filters.bot)
async def grp_handler(client: Client, msg: Message):
    text = msg.text or ""
    if not text.startswith("/"):
        return

    parts = text.split(None, 1)
    cmd   = parts[0].lstrip("/").split("@")[0].lower()
    if cmd not in CMDS:
        return

    pfx, desc, ex = CMDS[cmd]
    uid   = msg.from_user.id
    uname = msg.from_user.username or ""
    fname = msg.from_user.first_name or "User"
    mn    = f"@{uname}" if uname else fname   # mention

    # Auto-register
    if not u_get(uid):
        u_reg(uid, uname, fname)

    # ── Force Subscribe ──────────────────────────────────────
    ok, target = await fs_check(uid)
    if not ok:
        await msg.reply(
            "⚠️ **Access Denied!**\n\n"
            "🔒 Pehle required channel/group join karo.\n"
            "Join karne ke baad dobara command bhejo.",
            reply_markup=await fs_button(target)
        )
        return

    # ── Group Size Guard ─────────────────────────────────────
    try:
        mc = (await client.get_chat(msg.chat.id)).members_count or 0
        if mc < MIN_MEMBERS:
            await msg.reply(
                f"⚠️ **Group Too Small!**\n\n"
                f"Is bot ke liye minimum **{MIN_MEMBERS} members** chahiye.\n"
                f"Abhi: `{mc}` members"
            )
            return
    except Exception:
        pass   # skip if we can't fetch count

    # ── Query Required ───────────────────────────────────────
    if len(parts) < 2 or not parts[1].strip():
        await msg.reply(
            f"❓ **Usage:**\n`{pfx} {ex}`\n\n"
            f"**Example:** `{pfx} {ex}`"
        )
        return

    query = parts[1].strip()

    # ── Credit Check ─────────────────────────────────────────
    u = u_get(uid)
    if not u["premium"] and u["credits"] <= 0:
        await msg.reply(
            "❌ **No Credits Left!**\n\n"
            "**Credits paane ke tarike:**\n"
            f"• Dost ko refer karo → +1 credit\n"
            f"  `https://t.me/{BOT_USERNAME}?start=ref_{uid}`\n\n"
            "• **Premium** lo → Unlimited searches",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "💎 Buy Premium",
                    url=f"https://t.me/{OWNER_USERNAME.lstrip('@')}"
                )
            ]])
        )
        return

    # ── Searching ────────────────────────────────────────────
    st = await msg.reply(
        f"🔍 **Searching...**\n"
        f"👤 {mn}  |  🔎 `{pfx} {query}`"
    )

    if not cr_use(uid):
        await st.edit_text("❌ Credit deduction failed. Try again.")
        return

    raw, src = await get_data(cmd, query)

    if not raw:
        cr_refund(uid)
        await st.edit_text(
            f"❌ **No Result Found**\n\n"
            f"🔎 `{pfx} {query}`\n"
            f"⚠️ Dono sources ne respond nahi kiya.\n"
            f"💡 Credit refund ho gaya. Baad mein try karo."
        )
        return

    # ── Format & Deliver ─────────────────────────────────────
    jdata  = extract_json(raw)
    result = f"```json\n{jdata}\n```" if jdata else f"```\n{raw}\n```"

    rid = str(uuid.uuid4())[:8]
    r_save(rid, uid, f"{pfx} {query}", result)

    await st.edit_text(
        f"✅ **Result Ready!**\n\n"
        f"👤 {mn}\n"
        f"🔎 `{pfx} {query}`\n"
        f"{src}\n\n"
        f"👇 Apna data dekhne ke liye button dabao:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "📋 Here is Your Data — Click Here",
                url=f"https://t.me/{BOT_USERNAME}?start=result_{rid}"
            )
        ]])
    )

# ══════════════════════════════════════════════════════════════
#   🏠  /start  (Private Chat)
# ══════════════════════════════════════════════════════════════
@bot.on_message(filters.command("start") & filters.private)
async def cmd_start(client: Client, msg: Message):
    uid   = msg.from_user.id
    uname = msg.from_user.username or ""
    fname = msg.from_user.first_name or "User"
    parts = (msg.text or "").split(None, 1)
    param = parts[1].strip() if len(parts) > 1 else ""

    # ── Result deeplink  (/start result_XXXXXXXX) ────────────
    if param.startswith("result_"):
        rid = param[7:]
        row = r_get(rid)
        if not row:
            await msg.reply("❌ Result expired ya invalid link hai.")
            return
        if not u_get(uid):
            u_reg(uid, uname, fname)
        await msg.reply(
            f"📊 **OSINT Result**\n"
            f"🔍 `{row['qcmd']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{row['result']}"
        )
        return

    # ── Referral deeplink  (/start ref_12345) ────────────────
    ref = None
    if param.startswith("ref_"):
        try:
            ref = int(param[4:])
            if ref == uid:
                ref = None
        except ValueError:
            pass

    new = not u_get(uid)
    u_reg(uid, uname, fname, ref)
    u  = u_get(uid)
    rl = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"

    await msg.reply(
        f"{'🎉 Welcome!' if new else '👋 Welcome Back!'} **{fname}**\n\n"
        + (f"✨ Tumhe **{FREE_CREDITS} free credits** mile hain!\n\n" if new else "")
        + f"💰 Credits : `{u['credits']}`\n"
          f"💎 Status  : `{'Premium ♾️' if u['premium'] else 'Free'}`\n\n"
          f"🔗 **Referral Link:**\n`{rl}`\n"
          f"_Har dost ko refer karo → +1 credit_\n\n"
          f"👥 Bot sirf **groups** mein kaam karta hai!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 All Commands",  callback_data="cmds")],
            [
                InlineKeyboardButton("💰 My Credits",  callback_data="creds"),
                InlineKeyboardButton("💎 Buy Premium", url=f"https://t.me/{OWNER_USERNAME.lstrip('@')}")
            ],
            [InlineKeyboardButton("👥 Refer & Earn",  callback_data="refer")]
        ])
    )

# ══════════════════════════════════════════════════════════════
#   🎛️  INLINE CALLBACKS
# ══════════════════════════════════════════════════════════════
@bot.on_callback_query()
async def cbs(client: Client, q: CallbackQuery):
    uid = q.from_user.id
    u   = u_get(uid)
    d   = q.data

    if d == "cmds":
        lines = "⚡️ **All Commands** *(Group only)*\n\n"
        for _, (pfx, desc, _ex) in CMDS.items():
            lines += f"`{pfx}` — {desc}\n"
        await q.message.edit_text(
            lines,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="home")
            ]])
        )

    elif d == "creds":
        await q.answer(
            f"💰 Credits: {u['credits'] if u else 0}\n"
            f"💎 Status: {'Premium ♾️' if u and u['premium'] else 'Free'}",
            show_alert=True
        )

    elif d == "refer":
        rl = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
        await q.answer(
            f"🔗 Tumhara Referral Link:\n{rl}\n\nHar refer pe +1 Credit milega!",
            show_alert=True
        )

    elif d == "home":
        u  = u_get(uid)
        rl = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
        await q.message.edit_text(
            f"👤 **Your Profile**\n\n"
            f"💰 Credits : `{u['credits'] if u else 0}`\n"
            f"💎 Status  : `{'Premium ♾️' if u and u['premium'] else 'Free'}`\n\n"
            f"🔗 Referral:\n`{rl}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 All Commands",  callback_data="cmds")],
                [
                    InlineKeyboardButton("💰 My Credits",  callback_data="creds"),
                    InlineKeyboardButton("💎 Buy Premium", url=f"https://t.me/{OWNER_USERNAME.lstrip('@')}")
                ],
                [InlineKeyboardButton("👥 Refer & Earn",  callback_data="refer")]
            ])
        )

# ══════════════════════════════════════════════════════════════
#   👑  OWNER COMMANDS
# ══════════════════════════════════════════════════════════════
def owner_only(fn):
    @functools.wraps(fn)
    async def wrapper(client, msg, *a, **kw):
        if msg.from_user.id != OWNER_ID:
            return
        await fn(client, msg, *a, **kw)
    return wrapper


# /setfs  —  Force Subscribe configure karo
@bot.on_message(filters.command("setfs") & filters.private)
@owner_only
async def cmd_setfs(client: Client, msg: Message):
    p = (msg.text or "").split(None, 2)
    if len(p) == 1:
        await msg.reply(
            f"⚙️ **Force Subscribe Settings**\n\n"
            f"📢 Channel : `{s_get('force_ch') or 'None'}`\n"
            f"👥 Group   : `{s_get('force_gp') or 'None'}`\n\n"
            f"**Commands:**\n"
            f"`/setfs channel @handle` — channel set karo\n"
            f"`/setfs group @handle`   — group set karo\n"
            f"`/setfs clear`           — sab hatao\n\n"
            f"⚠️ Bot ko us channel/group ka **admin** banana padega!"
        )
        return

    sub = p[1].lower()
    if sub == "clear":
        s_set("force_ch", None)
        s_set("force_gp", None)
        await msg.reply("✅ Force subscribe clear ho gaya!")
        return

    if len(p) < 3:
        await msg.reply("❌ Target missing.\nExample: `/setfs channel @mychannel`")
        return

    target = p[2].strip()
    if sub == "channel":
        s_set("force_ch", target)
        await msg.reply(f"✅ Force channel set: `{target}`")
    elif sub == "group":
        s_set("force_gp", target)
        await msg.reply(f"✅ Force group set: `{target}`")
    else:
        await msg.reply("❌ Invalid. Use `channel` ya `group`")


# /setbackup  —  Backup group ka ID manually set karo
@bot.on_message(filters.command("setbackup") & filters.private)
@owner_only
async def cmd_setbackup(client: Client, msg: Message):
    global _backup_gid
    p = (msg.text or "").split()
    if len(p) < 2:
        await msg.reply(
            f"⚙️ **Backup Group ID:** `{s_get('backup_gid') or 'Not set'}`\n\n"
            f"Usage: `/setbackup -100XXXXXXXXXX`\n"
            f"_(Group ID usually starts with -100)_"
        )
        return
    try:
        gid = int(p[1])
        s_set("backup_gid", str(gid))
        _backup_gid = gid
        await msg.reply(f"✅ Backup group ID set: `{gid}`")
    except ValueError:
        await msg.reply("❌ Valid numeric group ID do.")


# /addcredits user_id amount
@bot.on_message(filters.command("addcredits") & filters.private)
@owner_only
async def cmd_addcredits(client: Client, msg: Message):
    p = (msg.text or "").split()
    if len(p) < 3:
        await msg.reply("Usage: `/addcredits user_id amount`")
        return
    try:
        uid_t, amt = int(p[1]), int(p[2])
        _c.execute("UPDATE users SET credits=credits+? WHERE uid=?", (amt, uid_t))
        _db.commit()
        await msg.reply(f"✅ User `{uid_t}` ko `{amt}` credits diye!")
    except Exception as e:
        await msg.reply(f"❌ Error: {e}")


# /setpremium user_id 1|0
@bot.on_message(filters.command("setpremium") & filters.private)
@owner_only
async def cmd_setpremium(client: Client, msg: Message):
    p = (msg.text or "").split()
    if len(p) < 3:
        await msg.reply("Usage: `/setpremium user_id 1` (1=ON 0=OFF)")
        return
    try:
        uid_t, val = int(p[1]), int(p[2])
        _c.execute("UPDATE users SET premium=? WHERE uid=?", (val, uid_t))
        _db.commit()
        await msg.reply(f"✅ User `{uid_t}` premium {'✅ ON' if val else '❌ OFF'}!")
    except Exception as e:
        await msg.reply(f"❌ Error: {e}")


# /stats
@bot.on_message(filters.command("stats") & filters.private)
@owner_only
async def cmd_stats(client: Client, msg: Message):
    _c.execute("SELECT COUNT(*) FROM users");              total   = _c.fetchone()[0]
    _c.execute("SELECT COUNT(*) FROM users WHERE premium=1"); prem = _c.fetchone()[0]
    _c.execute("SELECT COUNT(*) FROM rcache");             searches = _c.fetchone()[0]
    await msg.reply(
        f"📊 **Bot Statistics**\n\n"
        f"👥 Total Users  : `{total}`\n"
        f"💎 Premium      : `{prem}`\n"
        f"🔍 Searches     : `{searches}`\n"
        f"📢 Force Ch     : `{s_get('force_ch') or 'None'}`\n"
        f"👥 Force Gp     : `{s_get('force_gp') or 'None'}`\n"
        f"🔵 Backup GID   : `{s_get('backup_gid') or 'None'}`"
    )


# /broadcast — reply karo kisi message ko aur broadcast karega
@bot.on_message(filters.command("broadcast") & filters.private)
@owner_only
async def cmd_broadcast(client: Client, msg: Message):
    if not msg.reply_to_message:
        await msg.reply("❌ Broadcast ke liye kisi message ko reply karo!")
        return
    _c.execute("SELECT uid FROM users")
    uids = [r[0] for r in _c.fetchall()]
    sent = failed = 0
    st   = await msg.reply(f"📢 Broadcasting to **{len(uids)}** users...")
    for uid in uids:
        try:
            await msg.reply_to_message.copy(uid)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)   # flood prevention
    await st.edit_text(
        f"✅ **Broadcast Done!**\n"
        f"✔️ Sent   : `{sent}`\n"
        f"❌ Failed : `{failed}`"
    )

# ══════════════════════════════════════════════════════════════
#   🚫  PRIVATE — REDIRECT
# ══════════════════════════════════════════════════════════════
_SKIP_CMDS = {
    "start", "setfs", "setbackup",
    "addcredits", "setpremium", "stats", "broadcast"
}

@bot.on_message(filters.private & ~filters.command(list(_SKIP_CMDS)))
async def pvt_redirect(client: Client, msg: Message):
    if msg.text:
        await msg.reply(
            "🤖 **Bot sirf groups mein kaam karta hai!**\n\n"
            "Apne group mein add karo aur commands use karo.\n\n"
            "/start — apna profile aur credits dekho"
        )

# ══════════════════════════════════════════════════════════════
#   🚀  STARTUP
# ══════════════════════════════════════════════════════════════
async def main():
    global BOT_USERNAME, _backup_gid

    await userbot.start()
    await bot.start()

    # Auto-detect bot username
    me = await bot.get_me()
    BOT_USERNAME = me.username
    log.info(f"🤖 Bot: @{BOT_USERNAME}")

    # Restore backup group ID from DB
    saved = s_get("backup_gid")
    if saved:
        _backup_gid = int(saved)
        log.info(f"✅ Backup group restored: {_backup_gid}")
    else:
        # Auto-join backup group
        try:
            chat = await userbot.join_chat(BACKUP_GROUP_INVITE)
            _backup_gid = chat.id
            s_set("backup_gid", str(_backup_gid))
            log.info(f"✅ Joined backup group: {_backup_gid}")
        except Exception as e:
            log.warning(
                f"Backup group join failed: {e}\n"
                f"→ Use /setbackup <group_id> in bot PM to set it manually."
            )

    log.info("🚀 OSINT Bot v5.0 is ONLINE!")
    await idle()

    await bot.stop()
    await userbot.stop()


if __name__ == "__main__":
    asyncio.run(main())
