# Snap&Send

## About

Snap&Send is a Telegram bot for people who photograph slides, whiteboards, and
documents at events and never do anything with the photos afterward. Send it
one or more photos, and it extracts the visible text — preserving whatever
structure is actually on the page (headings, paragraphs, bullet lists,
tables, and flowcharts) — combines everything from a batch into one set of
notes, and emails it to you shortly after your last photo.

It runs as a single Python process (`python-telegram-bot`, long-polling)
backed by OpenAI for extraction, DynamoDB for the one thing it needs to
remember (your email, encrypted with KMS), and Resend for delivery. Photos
are held in memory only and discarded once a batch is sent or times out.

## Local setup

1. Create and activate a Python 3.12 virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and provide the required values.
4. Run `python -m src.bot` after configuring Telegram, OpenAI, Resend, DynamoDB,
   and KMS.

## Required configuration

`TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`, `RESEND_API_KEY`, `KMS_KEY_ID`, and
`RESEND_FROM_EMAIL` are required. Never commit `.env` or real credentials.

The users DynamoDB table uses `telegram_user_id` as its partition key. User
emails are encrypted with KMS before storage. Uploaded images and extracted
notes remain in memory and are not written to disk.

Provider and Railway configuration is documented in `docs/setup.md`.
