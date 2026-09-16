import unittest
from unittest.mock import Mock

from eva.brain.abc import VAApi
from eva.brain.contexts import TriggerPhraseContext
from eva.test_utuls import VAContextMock
from eva.test_utuls.stub_text_message import tm


class TriggerPhraseContextTest(unittest.TestCase):
    def setUp(self):
        self.ctx1 = VAContextMock()
        self.ctx2 = VAContextMock()

        self.next_ctx = VAContextMock()
        self.next_ctx.cmd_contexts["привет"] = self.ctx1
        self.next_ctx.cmd_contexts["пока"] = self.ctx2

        self.va = Mock(spec=VAApi)

    def test_simple_phrase(self):
        c = TriggerPhraseContext([["ева"]], self.next_ctx)
        self.assertIs(
            c.handle_command(self.va, tm("ева привет")),
            self.ctx1
        )
        self.assertIs(
            c.handle_command(self.va, tm("ева пока")),
            self.ctx2
        )

    def test_simple_phrase_omit_prefix(self):
        c = TriggerPhraseContext([["ева"]], self.next_ctx)
        self.assertIs(
            c.handle_command(self.va, tm("бла бла бла ева привет")),
            self.ctx1
        )
        self.assertIs(
            c.handle_command(self.va, tm("привет ева пока")),
            self.ctx2
        )

    def test_simple_phrase_no_match(self):
        c = TriggerPhraseContext([["ева"]], self.next_ctx)
        self.assertIs(
            c.handle_command(self.va, tm("ира привет")),
            None
        )
        self.next_ctx.handle_command.assert_not_called()

    def test_long_phrase(self):
        c = TriggerPhraseContext(
            [["окей", "ева", "ивановна"]], self.next_ctx)
        self.assertIs(
            c.handle_command(self.va, tm("окей ева ивановна привет")),
            self.ctx1
        )

    def test_varying_phrase(self):
        c = TriggerPhraseContext(
            [["ева"], ["евы"], ["еву"]], self.next_ctx)
        self.assertIs(
            c.handle_command(self.va, tm("ева привет")),
            self.ctx1
        )
        self.assertIs(
            c.handle_command(self.va, tm("евы привет")),
            self.ctx1
        )
        self.assertIs(
            c.handle_command(self.va, tm("еву привет")),
            self.ctx1
        )

    def test_forward_direct_message(self):
        c = TriggerPhraseContext(
            [["ева"], ["евы"], ["еву"]], self.next_ctx)
        self.assertIs(
            c.handle_command(self.va, tm("привет", {'is_direct': True})),
            self.ctx1
        )


if __name__ == '__main__':
    unittest.main()
