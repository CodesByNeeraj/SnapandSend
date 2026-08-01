import unittest

from src.satisfaction_survey import shouldPromptForSatisfaction


class ShouldPromptForSatisfactionTests(unittest.TestCase):
    def test_prompts_on_the_third_completed_batch(self):
        self.assertTrue(shouldPromptForSatisfaction(3))

    def test_does_not_prompt_before_the_third_completed_batch(self):
        for count in [1, 2]:
            self.assertFalse(shouldPromptForSatisfaction(count))

    def test_does_not_prompt_between_the_third_and_thirtieth(self):
        for count in [4, 10, 15, 29]:
            self.assertFalse(shouldPromptForSatisfaction(count))

    def test_prompts_every_thirty_after_the_third(self):
        for count in [30, 60, 90, 120]:
            self.assertTrue(shouldPromptForSatisfaction(count))

    def test_does_not_prompt_just_off_a_thirty_multiple(self):
        for count in [31, 59, 89]:
            self.assertFalse(shouldPromptForSatisfaction(count))


if __name__ == "__main__":
    unittest.main()
