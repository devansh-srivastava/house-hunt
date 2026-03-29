# Bot Instructions

## Setup (first time only)

```
cd bot
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Fill in `bot/.env` before running (Telegram token, Gemini key, Supabase URL + key, your Telegram user ID).

---

## Starting the bot

```
cd bot
.\venv\Scripts\activate
python main.py
```

The bot will start polling. Keep the terminal open.

---

## Workflow

### 1. Set a broker
Send a message starting with `broker` followed by their name and phone number in any natural format:
```
Broker Rajesh 9876543210
broker: Amit Kumar 8765432109
Broker Sharma ji, 9012345678
```
Gemini will extract the name and phone automatically — no strict format needed.

### 2. Forward / paste broker messages
Paste or forward the raw WhatsApp/text messages you received from the broker.
You can paste multiple messages — the bot batches them over a 5-second window and processes all of them together with Gemini.

### 3. Review the extracted listings
After the batch is processed, the bot sends a card for each property found:

```
📋 Society Name — 3BHK
📍 Location
📐 Area: 1250 sqft
💰 Price: ₹85L
🏢 Floor: 4th
🧭 Facing: East
📦 Ready to move
👤 BrokerName (9876543210)
```

Each card has three buttons:
| Button | Action |
|--------|--------|
| ✅ Save | Saves the listing to the database |
| ❌ Skip | Discards the listing |
| ✏️ Edit | Prompts you to send corrected details as text, then re-extracts |

### 4. End the broker session
When done with a broker, type:
```
done
```
This clears the session so you can move to a new broker.

---

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and quick-reference instructions |
| `/help` | Full command and workflow guide |
| `/list` | Show all saved societies with their location and status |
| `/status Society Name` | Show all configs and broker quotes for a society |

### Example usage

```
/status Ace Aspire
```
Shows all 2BHK / 3BHK configs saved for Ace Aspire, with each broker's price, floor, and facing.

---

## Tips

- **Multiple brokers in one session?** Type `done` after finishing with one broker, then set the next one with `Broker ...`.
- **Wrong data extracted?** Tap ✏️ Edit and re-send the relevant part of the message in cleaner text.
- **Bot not responding?** Make sure your Telegram user ID matches `ALLOWED_USER_ID` in `.env`.
- **No listings found?** The message likely didn't contain structured property data. Try pasting just the relevant part.
