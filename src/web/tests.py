from django.test import TestCase

# Create your tests here.
# Unit Tests


# System integration test.
class SystemIntegrationTestCase(TestCase):
    """
    Complete system integration test that tests the system from
    initialization to final score prediction.

    0. Assumes database is set up with a small corpus of 10 documents.
    1. Load a submission on this corpus.
    2. Check that the submission generates a sample.
    3. Check that the submission generates evaluation questions.
    4. Check that the submission generates mturk HITs (through a MTurk mock).

    5. Request mturk tasks
    6. Mock interface responses.

    7. Check postprocessing of data and loading into evaluation.

    8. Check final score and output.
    """

    def setUp(self):
        """
        0. Set up with a small corpus of 10 documents.
        """

