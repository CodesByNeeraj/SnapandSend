"""Trigger rule and fixed text for the periodic CSAT satisfaction survey."""

SURVEY_MESSAGE = "How has your experience using Snap&Send so far? Rate out of 10."
THANK_YOU_MESSAGE = "Thank you!"
CSAT_CALLBACK_PREFIX = "csat:"
FIRST_SURVEY_AT_USAGE_COUNT = 3
SURVEY_INTERVAL_USAGE_COUNT = 30


def shouldPromptForSatisfaction(usageCount: int) -> bool:
    """Return whether a just-completed batch should prompt a CSAT rating.

    Prompts on the 3rd completed batch, then every 30th after that
    (30, 60, 90, 120, ...).
    """

    if usageCount == FIRST_SURVEY_AT_USAGE_COUNT:
        return True
    return (
        usageCount > FIRST_SURVEY_AT_USAGE_COUNT
        and usageCount % SURVEY_INTERVAL_USAGE_COUNT == 0
    )
