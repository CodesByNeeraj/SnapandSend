# Snap&Send

Telegram bot that turns batches of text-bearing images into one emailed set of
notes.

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
