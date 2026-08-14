# Snap&Send

## What is Snap&Send?

Snap&Send is a Telegram bot for people who frequent conferences & networking
events. Many take photos of presenter slides but never look at them again.
As a result, the knowledge gained from the event gets lost.

## How Snap&Send Works

Send it photos whenever u capture them at an event & never feel the need to
manually take notes when you are on the go during the event or after the
event.

Snap&Send bot extracts the visible text, preserving whatever structure is
actually on the page: headings, paragraphs, bullet lists, tables, and
flowcharts.

It combines everything from a batch of photos sent into one set of notes and
emails it to you almost immediately.

By the time you're back at the laptop, the notes are already in your inbox, ready to file away wherever you keep them.

## Table of Contents

1. [Product Walkthrough](#product-walkthrough)
2. [Privacy & Security](#privacy--security)
3. Tech Stack Used
4. Why these Technologies?
5. System Architecture Diagram
6. Key Decisions Made
7. Evaluations
8. View PRD

## Product Walkthrough

### Starting a conversation

![The /start command onboarding a new user](gallery/start_message.jpeg)

*The bot's onboarding message after /start, followed by email registration.*

Sending `/start` shows what the bot does, discloses that photos are sent to
OpenAI for extraction and notes are delivered through Resend, and asks for
an email address. Reply with a valid email address and the bot confirms it
is saved. Photos can be sent right after.

### Sending photos and getting a response

![Photos being sent to the bot and accepted one by one](gallery/send_images.jpeg)

![The bot acknowledging /done and confirming the email was sent](gallery/botresponse.jpeg)

*Each photo is acknowledged with a running count, and /done triggers
processing right away.*

Every accepted photo gets an immediate reply with a running count, for
example "Image accepted (2/15)". A batch holds a maximum of 15 photos.
Sending `/done` starts processing right away instead of waiting for the
3-minute inactivity window to close the batch automatically. The bot
replies once to confirm it is processing, then again once the email has
been sent.

### The emailed notes

![An example email with formatted notes from a batch of slides](gallery/snap&send_email_example.png)

*The final email: one heading per photo, with the extracted content kept in
its original structure.*

Once processing finishes, one email arrives with all of the batch's content
combined, in the order the photos were sent.

## Privacy & Security

- **Emails are encrypted at rest.** Registered addresses are encrypted with
  AWS KMS before being written to the database, using a per-user encryption
  context so one user's ciphertext cannot be decrypted in another user's
  context.
