# TLDRBot

A witty, slightly sarcastic Telegram bot for group chat summarization. Built with Python and an OpenAI-compatible chat completions API, TLDRBot helps teams catch up on conversations with personality.

## Features

### Conversation Summarization (`/tldr`)
Summarize the last N messages in a group chat with a snarky commentary.

```
/tldr      → Summarize last 50 messages
/tldr 100  → Summarize last 100 messages
```

### @Mention Replies
Tag the bot and it'll respond with its signature sarcasm.

```
@TLDRBot what's everyone talking about?
```

### Auto Video Downloads
Optional. When enabled, drop a TikTok, Instagram Reel, or YouTube Shorts link and the bot automatically downloads and shares the video. It is disabled by default because `yt-dlp` may require cookies or JavaScript support for some sites.

### Rate Limiting
Each user gets 10 AI requests per day. The bot will let you know when you're running low (with attitude, of course).

### Token Budget
`/tldr` prompts are trimmed with a Hugging Face `tokenizer.json` before they are sent to the AI endpoint. By default the bot downloads `Qwen/Qwen3.6-27B`'s tokenizer on startup and keeps at most 64,000 input tokens from the newest chat messages.

If `TOKEN_LIMIT_ENABLED=true` and the tokenizer cannot be downloaded or loaded, the bot exits instead of falling back to an approximate counter. Set `TOKEN_LIMIT_ENABLED=false` to disable this behavior.

## Personality Examples

**On /tldr:**
> "Summary complete. I'm basically your group's unpaid intern at this point."

**On @mention:**
> "You rang? I was busy judging other chats."

**On rate limit:**
> "Whoa there, chatty! You've used me 10 times today. I need a break."

## Getting Started

### Prerequisites
- Python 3.14+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- An OpenAI-compatible API endpoint and token

### Installation

1. Clone the repository:
```bash
git clone https://github.com/advaitbd/tldrbot.git
cd tldrbot
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set environment variables:
```bash
# Required
export BOT_TOKEN="your_telegram_bot_token"
export OPENAI_API_KEY="your_endpoint_token"

# Optional
export AI_BASE_URL="https://your-inference.example.com/v1"
export AI_MODEL="openai/qwen3.6-27b"
export DAILY_LIMIT="10"            # AI uses per user per day
export MAX_MESSAGES="400"          # Max messages to store per chat
export DATABASE_URL="sqlite:///data/tldrbot.sqlite"
export AUTO_DOWNLOAD_ENABLED="false"
export TOKEN_LIMIT_ENABLED="true"
export TOKEN_LIMIT_MAX_INPUT_TOKENS="64000"
export TOKENIZER_REPO_ID="Qwen/Qwen3.6-27B"
```

5. Run the bot:
```bash
cd bot
python main.py
```

### Docker Compose

Copy `.env.example` to `.env`, fill in `BOT_TOKEN`, `OPENAI_API_KEY`, and `AI_BASE_URL`, then run:

```bash
docker compose up --build
```

The compose setup stores SQLite analytics data in the `bot-data` volume and does not run an inference server. Point `AI_BASE_URL` at your own OpenAI-compatible endpoint, including llama.cpp servers that expose `/v1/chat/completions`.

For a llama.cpp endpoint, configure the model context on the inference side, for example `--ctx-size 262144`, and use:

```bash
AI_BASE_URL=https://your-inference.example.com/v1
AI_MODEL=openai/qwen3.6-27b
OPENAI_API_KEY=your_endpoint_token
```

The tokenizer cache also lives in the `bot-data` volume by default at `/data/tokenizers`, so startup only downloads `tokenizer.json` when it is missing.

## Project Structure

```
bot/
├── main.py              # Entry point
├── config.py            # Configuration
├── core/
│   ├── bot.py           # Bot orchestration
│   ├── ai.py            # AI service with personality
│   └── rate_limiter.py  # Per-user rate limiting
├── plugins/
│   ├── help.py          # /help command
│   ├── summarize.py     # /tldr command
│   ├── mention_reply.py # @mention handler
│   └── auto_download.py # Video URL detection
└── storage/
    ├── memory.py        # In-memory message storage
    └── analytics.py     # Optional event logging
```

## Commands

| Command | Description | Rate Limited |
|---------|-------------|--------------|
| `/help` | Show help | No |
| `/tldr [n]` | Summarize last n messages | Yes |
| `@bot` mention | Reply with personality | Yes |
| Auto-download | Detect & download videos | No |

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | Yes | - | Telegram bot token |
| `OPENAI_API_KEY` | Yes | - | OpenAI-compatible API token |
| `AI_BASE_URL` | No | OpenAI default | Custom OpenAI-compatible `/v1` endpoint |
| `AI_MODEL` | No | gpt-4o-mini | Model name to request |
| `DAILY_LIMIT` | No | 10 | AI uses per user per day |
| `MAX_MESSAGES` | No | 400 | Messages to store per chat |
| `DATABASE_URL` | No | - | SQLite/PostgreSQL URL for analytics |
| `TOKEN_LIMIT_ENABLED` | No | true | Enable fail-fast tokenizer-backed prompt trimming |
| `TOKEN_LIMIT_MAX_INPUT_TOKENS` | No | 64000 | Maximum `/tldr` input tokens sent to the AI endpoint |
| `TOKENIZER_REPO_ID` | No | Qwen/Qwen3.6-27B | Hugging Face repo used for `tokenizer.json` |
| `TOKENIZER_REVISION` | No | main | Hugging Face revision for the tokenizer |
| `TOKENIZER_FILENAME` | No | tokenizer.json | Tokenizer file inside the repo |
| `TOKENIZER_CACHE_DIR` | No | data/tokenizers | Local tokenizer cache directory |
| `TOKENIZER_URL` | No | - | Direct tokenizer URL override |
| `HF_TOKEN` | No | - | Optional Hugging Face token for tokenizer download |
| `AUTO_DOWNLOAD_ENABLED` | No | false | Enable `yt-dlp` video auto-download plugin |
| `VIDEO_URL_PATTERNS` | No | built-in list | JSON array of URL regexes used when auto-download is enabled |

## Contributing

Contributions welcome! Feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.
