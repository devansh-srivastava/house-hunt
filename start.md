# How to Run

## Terminal 1 — Website

```
cd website
npx serve .
```

Open the URL it prints (usually http://localhost:3000).

---

## Terminal 2 — Bot

First time only (create virtual environment and install dependencies):

```
cd bot
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Then run the bot (activate the venv first if not already active):

```
cd bot
.\venv\Scripts\activate
python main.py
```

Make sure `bot/.env` is filled in before running.
