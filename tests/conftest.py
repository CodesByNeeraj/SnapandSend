"""Pytest-wide setup, applied before any test module is collected.

Disables real Langfuse tracing for the whole test run. Several test
modules import src.bot, which calls load_dotenv() at module import time
and pulls real Langfuse credentials into the process environment; without
this, @observe-decorated code exercised by tests (even with fully mocked
OpenAI/Resend clients) would send genuine traces to the live project.
"""

import os

os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
