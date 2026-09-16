import unittest

from eva.brain.canonical_text import convert_to_canonical, is_canonical


class ToCanonicalTest(unittest.TestCase):
    def test_leave_canonical_unchanged(self):
        txt = "привет ева включи свет"
        self.assertEqual(
            txt,
            convert_to_canonical(txt)
        )

    def test_strip(self):
        self.assertEqual(
            "привет ева включи свет",
            convert_to_canonical("\t привет ева включи свет\n")
        )

    def test_drop_duplicate_whitespace(self):
        self.assertEqual(
            "привет ева включи свет",
            convert_to_canonical("привет  ева\t включи     свет")
        )

    def test_drop_punctuation(self):
        self.assertEqual(
            "привет ева включи свет",
            convert_to_canonical("привет, ева! включи свет")
        )

    def test_lowercase(self):
        self.assertEqual(
            "привет ева включи свет",
            convert_to_canonical("Привет Ева включи свет")
        )

    def test_all(self):
        self.assertEqual(
            "привет ева включи свет",
            convert_to_canonical(
                "  \nПривет \nЕва!! !   включи свет!! :)))) ^_^")
        )


class IsCanonicalTextTest(unittest.TestCase):
    def test_pad_right(self):
        self.assertFalse(is_canonical("привет ева включи свет "))

    def test_pad_left(self):
        self.assertFalse(is_canonical(" привет ева включи свет"))

    def test_double_space(self):
        self.assertFalse(is_canonical("привет ева  включи свет"))

    def test_non_space_whitespace(self):
        self.assertFalse(is_canonical("привет ева\nвключи свет"))
        self.assertFalse(is_canonical("привет ева включи\tсвет"))

    def test_uppercase(self):
        self.assertFalse(is_canonical("привет Ева включи свет"))

    def test_canonical(self):
        self.assertTrue(is_canonical("привет ева включи свет"))


if __name__ == '__main__':
    unittest.main()
