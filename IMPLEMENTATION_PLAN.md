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

- [x] Implement the per-user limit of 30 accepted photos per day.
- [x] Implement the documented unlimited-account exception without exposing the
      account identifier in logs or user-facing messages.
- [x] Define the counting boundary and timezone behavior for a calendar day.
- [x] Add tests for below-limit, at-limit, over-limit, reset, and exception cases.

## 4. Image intake and preparation

- [x] Implement Telegram photo/document validation for image files only.
- [x] Reject files over 20 MB with a clear user message.
- [x] Download accepted images through Telegram `getFile` into memory.
- [x] Resize and compress images in memory before the OpenAI request.
- [x] Ensure image bytes are never written to disk, object storage, or logs.
- [x] Add tests for accepted images, non-image files, oversized files,
      malformed image bytes, and image preparation output.

## 5. Batch state management

- [x] Implement the in-memory per-user batch map containing ordered image bytes.
- [x] Add each accepted photo to the user's current batch in arrival order.
- [x] Implement 3-minute inactivity timeout detection.
- [x] Provide atomic closure for batches selected by timeout detection.
- [x] Ensure a restart does not recover or send a partial in-memory batch.
- [x] Add tests for ordering, multiple users, timeout boundaries, empty batches,
      and state clearing.

The batch state primitives are complete. Timeout processing, `/done`, and
post-processing state handling are implemented with the router and
`BatchOrchestrator` in section 8, after extraction and email delivery exist.

## 6. OpenAI extraction and note formatting

- [x] Implement the OpenAI client boundary using the configured vision model.
- [x] Build the prompt to extract visible text, preserve meaning, avoid
      fabricated content, and return strict structured data with a title and
      ordered bullet points.
- [x] Curate readable image results while preserving their source order.
- [x] Detect and report unreadable, blurry, dark, or textless photos without
      failing the rest of the batch.
- [x] Retry an OpenAI timeout or error exactly once, then notify the user of
      failure rather than hanging silently.
- [x] Remove near-duplicate content when two photos show the same slide.
- [x] Add mocked tests for clear slides, unreadable images, failures, retry
      behavior, and invalid model output.
- [x] Add mocked curation tests for unreadable images, ordering, and duplicates.

## 7. Email delivery

- [x] Implement Markdown note rendering for the email body.
- [x] Implement Resend delivery to a provided registered recipient email.
- [x] Send at most one combined email for a successfully curated batch.
- [x] Prevent delivery when extraction fails or curation yields no notes.
- [x] Add mocked tests for formatting, recipient handling, delivery failures,
      and one-email behavior.
- [ ] Resolve the recipient from the decrypted `UserStore` email during
      Telegram and orchestration integration.

## 8. Telegram routing and batch orchestration

- [x] Implement `/start` onboarding, including data-handling information and the
      email prompt.
- [x] Implement plain-text email reply handling, validation, encrypted
      persistence, and continuation of any photo waiting for email setup.
- [ ] Implement the remaining deterministic Telegram routing for photos,
      documents, commands, and unsupported input.
- [x] Implement photo receipt acknowledgement within the 2-second target where
      practical, including the running batch count and 3-minute window message.
- [x] Prompt for email before processing photos when no email is registered.
- [x] Ensure a user can provide the requested email by typing a reply, without a
      `/setemail` command.
- [ ] Connect photo handling, rate limiting, image preparation, batch management,
      OpenAI extraction, and email delivery without blocking Telegram updates.
- [x] Implement `/done` through the `BatchOrchestrator` using the decrypted
      registered `UserStore` email and one email delivery.
- [x] Process timeout-closed batches through the `BatchOrchestrator` using the
      decrypted registered `UserStore` email.
- [x] Make `/done` with no photos return the required upload-first message.
- [ ] Clear batch state after successful processing or unrecoverable process
      failure, without sending partial email.
- [x] Implement the user-facing message for unsupported files.
- [ ] Implement user-facing messages for rate limits,
      unreadable photos, processing failures, and restart-related reuploads.
- [x] Add adapter tests with mocked Telegram updates for `/start` and text.
- [ ] Add upload and external-service handler tests.

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
