# Provider and deployment setup

## AWS

Create a DynamoDB table named by `USERS_TABLE_NAME` in `ap-southeast-1` with
on-demand billing and a string partition key named `telegram_user_id`.

Create or select a KMS key and grant the deployed application permission to
call `kms:Encrypt` and `kms:Decrypt` for that key. Set its ARN or alias as
`KMS_KEY_ID`.

## Resend

Verify a sending domain in Resend. Set `RESEND_FROM_EMAIL` to a verified sender
address on that domain, then set `RESEND_API_KEY` in the deployment environment.

## Telegram and OpenAI

Create a Telegram bot through BotFather and set `TELEGRAM_BOT_TOKEN`. Create an
OpenAI API key and set `OPENAI_API_KEY`. Do not place either value in a file
committed to the repository.

## Railway

Create a Railway service using Python 3.12. Install `requirements.txt` and use
this start command:

```
python -m src.bot
```

Set every value from `.env.example` as Railway environment variables. Railway
must keep the service running because Snap&Send uses Telegram long polling.
