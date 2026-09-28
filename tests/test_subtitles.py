import unittest
from types import SimpleNamespace

from subtitles.cli import Word, _reliable_segment, make_cues, to_srt


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

    def test_subword_without_space_stays_attached(self):
        cues = make_cues([Word(0, 0.2, "Wi"), Word(0.2, 0.4, "-Fi"),
                          Word(0.5, 0.7, " ishlaydi.")])
        self.assertEqual(cues[0].text, "Wi-Fi ishlaydi.")

    def test_low_confidence_hallucination_is_filtered(self):
        weak = SimpleNamespace(avg_logprob=-1.3, words=[SimpleNamespace(probability=0.001)])
        spoken = SimpleNamespace(avg_logprob=-0.3, words=[SimpleNamespace(probability=0.9)])
        self.assertFalse(_reliable_segment(weak))
        self.assertTrue(_reliable_segment(spoken))

    def test_sentence_and_comma_boundaries_are_configurable(self):
        words = [Word(0, .3, "Salom,"), Word(.31, .6, "bugun."),
                 Word(.61, .9, "Yaxshi"), Word(.91, 1.2, "kun.")]
        combined = make_cues(words, split_sentences=False, split_commas=False,
                             split_pauses=False, max_lines=2, words_per_line=4)
        self.assertEqual(len(combined), 1)
        sentences = make_cues(words, split_sentences=True, split_commas=False,
                              split_pauses=False, max_lines=2, words_per_line=4)
        self.assertEqual([cue.text for cue in sentences], ["Salom, bugun.", "Yaxshi kun."])
        commas = make_cues(words, split_sentences=False, split_commas=True,
                           split_pauses=False, max_lines=2, words_per_line=4)
        self.assertEqual([cue.text for cue in commas], ["Salom,", "bugun. Yaxshi kun."])

    def test_start_and_end_padding_are_frame_aligned(self):
        cues = make_cues([Word(1.0, 1.5, "Salom.")], fps=25,
                         start_pad=.08, end_pad=.12, min_duration=0)
        self.assertEqual((cues[0].start, cues[0].end), (.92, 1.64))


if __name__ == "__main__":
    unittest.main()
