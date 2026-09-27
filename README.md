# ⚡️ OSINT Search Telegram Bot & Assistant Userbot

A powerful, dual-source OSINT Telegram Bot built with **Pyrogram** and **SQLite**. It allows users to search OSINT details directly in groups while serving raw JSON results privately through deep-link inline buttons.

---

## 🌟 Key Features

1. **Dual Source Architecture (Primary + Backup)**:
   - **Primary Source**: Interacts directly with the primary OSINT bot (`@UkraineToOsint_bot`).
   - **Backup Target Group**: Uses an integrated Pyrogram **Userbot Assistant** joined to the target backup group (`https://t.me/+EcpltYqKYoVjODVl`). If the primary bot fails, the assistant executes `/cmd <query>` in the backup group, captures the JSON/text response, and returns it to the user.

2. **Group Usage & Member Count Requirement**:
   - Commands are restricted to Telegram **Groups/Supergroups**.
   - Requires the group to have **at least 100 members** before allowing OSINT searches.

3. **Inline Result Delivery (Public Group Notification + Private Result)**:
   - When a search command is issued in a group, the bot sends a notification message with an `InlineKeyboardButton`:
     > *"Here is your data! Click the button below to view your results in private chat."*
   - Clicking the inline button (`https://t.me/<bot_username>?start=result_<rid>`) opens a direct message with the bot and retrieves the raw JSON formatted response.

4. **Credit, Referral & Premium Tier**:
   - **New Users**: Receive **2 Free Credits** upon initial registration.
   - **Search Cost**: **1 Credit per Search**.
   - **Referral System**: Earn **1 Credit per referral** using personal referral links (`t.me/<bot_username>?start=ref_<user_id>`).
   - **Premium Tier**: Premium users get **Unlimited Searches**. Contact Owner [**@xbroze**](https://t.me/xbroze) to purchase premium.

5. **Force Subscribe System (`/setfs`)**:
   - Channel owners/admins can mandate joining a Telegram Channel before using OSINT features.
   - Configured dynamically using `/setfs @channel_username`.

---

## ⚡️ Available Commands (23 OSINT Lookup Commands)

| Command | Description |
| :--- | :--- |
| `⚡️ /num` | NUMBER TO DETAILS |
| `⚡️ /aadhar` | AADHAR TO INFO |
| `⚡️ /tg` | TELEGRAM UID TO NUMBER |
| `🟢 /rc` | RC DETAILS |
| `⚡️ /vehicle` | VEHICLE NUMBER TO OWNER ADDRESS |
| `⚡️ /family` | AADHAR NUMBER TO FAMILY DETAILS |
| `⚡️ /email` | EMAIL TO INFO |
| `⚡️ /vnum` | VEHICLE TO OWNER NUM |
| `⚡️ /leak` | ADV OSINT SEARCH |
| `⚡️ /lpg` | LPG GAS INFO USING MOBILE NUMBER |
| `⚡️ /mp` | MP MOBILE NUM TO PIC + FAMILY INFO |
| `⚡️ /challan` | Challan info + challan pdf |
| `⚡️ /hp` | HP - LPG PIPELINE INFO THROUGH NUM |
| `⚡️ /chassis` | GET VEHICLE INFO FROM CHASSIS NUM |
| `⚡️ /eng` | GET VEHICLE INFO FROM ENGINE NUMBER |
| `⚡️ /ig` | INSTA ID TO BASIC DETAILS |
| `⚡️ /pvtig` | PVT INSTA ID FOLLOWER LOOKUP |
| `⚡️ /pan` | PAN INFO |
| `⚡️ /bh` | BHARAT PETROLEUM LOOKUP |
| `⚡️ /ind` | INDIAN PETROLEUM LOOKUP |
| `⚡️ /upi` | UPI INFO |
| `⚡️ /num2upi` | NUMBER TO UPI |
| `⚡️ /pan2ad` | PAN TO AADHAR |

---

## 🛠 User & Utility Commands

| Command | Description |
| :--- | :--- |
| `/start` | Start the bot, claim initial credits, view referral link or view search results |
| `/credits` or `/me` | Check remaining credits and referral link |
| `/help` | Show command list and usage guidelines |

---

## 👑 Owner & Admin Commands

Only accessible by the bot owner (`OWNER_ID` / `@xbroze`):

| Command | Usage | Description |
| :--- | :--- | :--- |
| `/setfs` | `/setfs @channel_username` or `/setfs off` | Set mandatory Force Subscribe channel |
| `/setbackup` | `/setbackup https://t.me/+EcpltYqKYoVjODVl` | Update backup group invite link |
| `/addcredits` | `/addcredits <user_id> <amount>` | Add search credits to a user |
| `/setpremium` | `/setpremium <user_id> 1` or `0` | Grant or revoke unlimited premium status |
| `/stats` | `/stats` | View total users, group stats, and active cache |
| `/broadcast` | `/broadcast <message>` or reply | Broadcast announcement to all users |

---

## ⚙️ Configuration & Setup

### 1. Prerequisites
- Python 3.10 or higher
- Telegram API Credentials (`API_ID`, `API_HASH`) from [my.telegram.org](https://my.telegram.org)
- Bot Token from [@BotFather](https://t.me/BotFather)
- Pyrogram String Session for the Assistant Userbot

### 2. Environment Variables / Config

Set environment variables or edit the configuration in `num.py`:

```env
API_ID=1234567
API_HASH=your_api_hash_here
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyZ
SESSION_STRING=your_pyrogram_userbot_session_string
OWNER_ID=123456789
OWNER_USERNAME=xbroze
BOT_USERNAME=your_bot_username
PRIMARY_BOT=UkraineToOsint_bot
BACKUP_GROUP_INVITE=https://t.me/+EcpltYqKYoVjODVl
```

### 3. Installation & Running

1. Install dependencies:
   ```bash
   pip install pyrogram tgcrypto
   ```

2. Generate Userbot Pyrogram String Session:
   ```python
   from pyrogram import Client
   async with Client("userbot", api_id=1234567, api_hash="your_api_hash") as app:
       print(await app.export_session_string())
   ```

3. Start the bot:
   ```bash
   python3 num.py
   ```

---

## 📁 Database Schema (`osint.db`)

The bot automatically creates and manages SQLite tables:
- `users`: Tracks `user_id`, `credits`, `is_premium`, `ref_by`, `joined_date`.
- `settings`: Configures key-value settings (`force_channel`, `backup_group_id`, `backup_invite`).
- `rcache`: Stores generated result UUIDs and raw OSINT JSON payloads for secure private retrieval.

---

## 📩 Owner Support & Contact

For purchasing **Premium Membership** (Unlimited searches) or technical support, contact the owner:
- **Telegram Owner**: [@xbroze](https://t.me/xbroze)
