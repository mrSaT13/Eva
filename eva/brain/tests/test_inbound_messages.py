import unittest

from eva.brain.inbound_messages import PlainTextMessage, PartialTextMessage
from eva.brain.output_pool import OutputPoolImpl


class InboundMessagesTest(unittest.TestCase):
    def setUp(self):
        self.pool = OutputPoolImpl([])

    def test_plaintext_message(self):
        msg = PlainTextMessage("Привет, Eva!", self.pool)

        self.assertIs(
            msg.get_related_outputs(),
            self.pool
        )
        self.assertEqual(
            msg.get_text(),
            "привет ева"
        )
        self.assertEqual(
            msg.get_original_text(),
            "Привет, Eva!"
        )
        self.assertIs(
            msg.get_original(),
            msg
        )

    def test_partial_message(self):
        om = PlainTextMessage("Привет, Eva!", self.pool)
        msg = PartialTextMessage(om, "привет")

        self.assertIs(
            msg.get_related_outputs(),
            self.pool
        )
        self.assertEqual(
            msg.get_text(),
            "привет"
        )
        self.assertIs(
            msg.get_original(),
            om
        )


if __name__ == '__main__':
    unittest.main()
