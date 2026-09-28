import unittest

from subtitles.cli import Word, make_cues, to_srt


class SubtitleTests(unittest.TestCase):
    def test_pause_and_frame_alignment(self):
        cues = make_cues([
            Word(0.013, 0.42, "Salom"),
            Word(0.43, 0.95, "dunyo!"),
            Word(1.8, 2.2, "Bugun"),
            Word(2.25, 2.7, "yaxshi."),
        ], fps=25)
        self.assertEqual(len(cues), 2)
        self.assertEqual((cues[0].start, cues[0].end), (0.0, 0.96))
        self.assertEqual(cues[1].start, 1.8)
        self.assertIn("Salom dunyo!", to_srt(cues))

    def test_wrap_and_empty_words(self):
        cues = make_cues([
            Word(0, 0.2, "  "), Word(0, 0.3, "O'zbekiston"),
            Word(0.3, 0.6, "poytaxti"), Word(0.6, 0.9, "Toshkent."),
        ], max_chars=16)
        self.assertEqual(cues[0].text.count("\n"), 1)
        self.assertEqual(len(cues), 2)
        self.assertTrue(all(len(line) <= 16 for cue in cues for line in cue.text.splitlines()))

    def test_short_caption_gets_reading_time_without_overlap(self):
        cues = make_cues([Word(0, 0.1, "Ha."), Word(1.0, 1.1, "Yo'q.")], fps=25)
        self.assertEqual(cues[0].end, 0.8)
        self.assertLess(cues[0].end, cues[1].start)

    def test_word_and_line_limits_split_cues(self):
        words = [Word(i * 0.3, i * 0.3 + 0.2, word) for i, word in
                 enumerate(["Bugun", "havo", "juda", "yaxshi", "ertalab", "uchrashamiz"])]
        cues = make_cues(words, max_lines=1, words_per_line=3)
        self.assertEqual([cue.text for cue in cues], ["Bugun havo juda", "yaxshi ertalab uchrashamiz"])
        self.assertTrue(all("\n" not in cue.text for cue in cues))

        cues = make_cues(words, max_lines=2, words_per_line=2)
        self.assertEqual(cues[0].text, "Bugun havo\njuda yaxshi")
        self.assertEqual(cues[1].text, "ertalab uchrashamiz")


if __name__ == "__main__":
    unittest.main()
