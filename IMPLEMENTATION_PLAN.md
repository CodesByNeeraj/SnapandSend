# Snap&Send Implementation Plan

This is the end-to-end implementation checklist for the v1 Telegram bot. The
current PRD is the source of truth: batches stay open for 3 minutes after the
latest photo, images are held in memory only, and OpenAI is used for extraction
and note formatting.

## 0. Planning and project baseline

- [x] Create this implementation plan.
- [x] Confirm the local Python version matches the CI target.
- [x] Confirm the existing virtual environment has the application dependencies
      and test tooling installed.
- [ ] Add a safe environment-variable template if one is needed, without real
      credentials.
- [ ] Decide the initial module import strategy so `src/` and `tests/` work both
      locally and in CI.

## 1. Application foundation

- [ ] Create the `src/` package and the module structure from `AGENTS.md`.
- [x] Create `src/constants.py` for the 3-minute batch timeout, 30-photo daily
      limit, 20 MB file limit, maximum 15 photos per batch, AWS region, table
      name, and configured model settings.
- [x] Create configuration loading and validation for Telegram, OpenAI, Resend,
      AWS, DynamoDB, KMS, and encryption settings.
- [x] Ensure configuration fails clearly when required runtime secrets are
      missing and never prints secret values.

## 2. User storage and privacy

- [x] Implement KMS-backed email encryption and decryption boundaries.
- [x] Implement the DynamoDB user store using `telegram_user_id` as the
      partition key and `email` plus `created_at` attributes.
- [x] Ensure plaintext email addresses are never stored at rest.
- [x] Add tests for new users, existing users, email updates, encryption, and
      missing users using mocked AWS clients.

## 3. Rate limiting

- [ ] Implement the per-user limit of 30 accepted photos per day.
- [ ] Implement the documented unlimited-account exception without exposing the
      account identifier in logs or user-facing messages.
- [ ] Define the counting boundary and timezone behavior for a calendar day.
- [ ] Add tests for below-limit, at-limit, over-limit, reset, and exception cases.

## 4. Image intake and preparation

- [ ] Implement Telegram photo/document validation for image files only.
- [ ] Reject files over 20 MB with a clear user message.
- [ ] Download accepted images through Telegram `getFile` into memory.
- [x] Resize and compress images in memory before the OpenAI request.
- [x] Ensure image bytes are never written to disk, object storage, or logs.
- [x] Add tests for oversized files, malformed image bytes, and image
      preparation output.

## 5. Batch management

- [ ] Implement the in-memory per-user batch map containing ordered image bytes.
- [ ] Add each accepted photo to the user's current batch in arrival order.
- [ ] Implement the 3-minute inactivity timeout and automatic batch closure.
- [ ] Implement `/done` to close and process the current batch immediately.
- [ ] Make `/done` with no photos return the required upload-first message.
- [ ] Clear batch state after successful close or unrecoverable process failure.
- [ ] Ensure a restart does not recover or send a partial in-memory batch.
- [ ] Add tests for ordering, multiple users, timeout boundaries, `/done`, empty
      batches, and state clearing.

## 6. OpenAI extraction and note formatting

- [ ] Implement the OpenAI client boundary using the configured vision model.
- [ ] Build the prompt to extract visible text, preserve meaning, avoid
      fabricated content, and return structured Markdown with a heading and
      bullet points.
- [ ] Process each image while preserving batch order.
- [ ] Detect and report unreadable, blurry, dark, or textless photos without
      failing the rest of the batch.
- [ ] Retry an OpenAI timeout or error exactly once, then notify the user of
      failure rather than hanging silently.
- [ ] Remove near-duplicate content when two photos show the same slide.
- [ ] Add tests using mocked OpenAI responses for clear slides, handwriting,
      unreadable images, failures, retry behavior, ordering, and duplicates.

## 7. Email delivery

- [ ] Implement Markdown note rendering for the email body.
- [ ] Implement Resend delivery to the user's decrypted registered email.
- [ ] Send exactly one combined email per completed batch.
- [ ] Prevent email delivery when the batch fails or the process restarts before
      completion.
- [ ] Add tests for formatting, recipient handling, one-email-per-batch, and
      mocked Resend failures.

## 8. Telegram bot handlers and orchestration

- [ ] Implement `/start` onboarding, including data-handling information and the
      email prompt.
- [ ] Implement plain-text email reply handling, validation, encrypted
      persistence, and continuation of any photo waiting for email setup.
- [ ] Implement photo receipt acknowledgement within the 2-second target where
      practical, including the running batch count and 3-minute window message.
- [ ] Prompt for email before processing photos when no email is registered.
- [ ] Ensure a user can provide the requested email by typing a reply, without a
      `/setemail` command.
- [ ] Connect photo handling, rate limiting, image preparation, batch management,
      OpenAI extraction, and email delivery without blocking Telegram updates.
- [ ] Implement user-facing messages for unsupported files, rate limits,
      unreadable photos, processing failures, and restart-related reuploads.
- [ ] Add handler tests with mocked Telegram updates and external services.

## 9. End-to-end behavior and performance

- [ ] Test the complete clear-slide flow from upload to one formatted email.
- [ ] Test an 8-photo batch and verify order and exactly one email.
- [ ] Test the 15-photo batch limit and the under-60-second delivery target.
- [ ] Test photo-before-email registration and automatic continuation after the
      user replies with a valid email address.
- [ ] Test process-failure behavior and confirm no partial email is sent.
- [ ] Review logs to confirm image content, extracted text, email addresses,
      tokens, and sensitive identifiers are not emitted.

## 10. Local verification and deployment

- [ ] Add local setup and runtime instructions to the project documentation.
- [ ] Document required Telegram bot, OpenAI, DynamoDB/KMS, Resend, and Railway
      configuration without including secrets.
- [ ] Create the DynamoDB users table in `ap-southeast-1` with on-demand billing.
- [ ] Configure the Resend sending domain and sender address.
- [ ] Configure Railway environment variables and long-polling startup.
- [ ] Run formatter, linter, security checks, and the complete mocked test suite
      locally.
- [ ] Perform a manual Telegram smoke test with non-sensitive sample images.

## 11. CI/CD, deferred until the Actions minutes reset

- [ ] Verify the workflow is located at `.github/workflows/ci.yml`.
- [ ] Add or confirm CI checks for formatting, linting, SAST, dependency audit,
      and tests with no network or real credentials.
- [ ] Confirm CI uses Python 3.12 and installs from `requirements.txt`.
- [ ] Add deployment automation only after the local application is stable and
      Railway deployment has been manually verified.

## Definition of done

- [ ] Every PRD functional requirement FR-00 through FR-09 has a passing test.
- [ ] Every PRD non-functional requirement NFR-01 through NFR-07 has been
      implemented or verified.
- [ ] The complete test suite and configured static checks pass locally.
- [ ] No uploaded image, extracted text, or plaintext email is persisted or
      logged.
- [ ] A real smoke test completes the intended Telegram-to-email workflow.
- [ ] Deployment is reproducible from documented configuration without secrets
      committed to the repository.
