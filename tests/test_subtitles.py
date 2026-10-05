import unittest
from types import SimpleNamespace

from subtitles.cli import (Word, _reliable_segment, apply_replacements,
                           make_cues, to_srt, to_vtt, to_ass, to_cyrillic, cue_speaker)
from subtitles.gigaam import _chunks
from subtitles.sentences import restore_sentences, standardize_literary


class SubtitleTests(unittest.TestCase):
    def test_missing_optional_speaker_model_does_not_discard_subtitles(self):
        import tempfile, json
        from pathlib import Path
        from unittest.mock import patch
        from subtitles.cli import main, optional_speakers
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);audio=folder/'audio.wav';audio.write_bytes(b'fixture')
            output=folder/'captions.srt'
            with patch('subtitles.cli.transcribe',return_value=[Word(0,1,'Salom.')]),patch('subtitles.cli.diarize',side_effect=RuntimeError('So‘zlovchilar modeli o‘rnatilmagan')):
                self.assertEqual(main(['--input',str(audio),'--output',str(output),'--speakers','--no-sentence-restore']),0)
            self.assertIn('Salom.',output.read_text(encoding='utf-8-sig'))
            data=json.loads(output.with_suffix('.json').read_text())
            self.assertEqual(data['speaker_turns'],[])
            self.assertIn('subtitrlar yaratildi',data['warnings'][0])
            with patch('subtitles.cli.diarize',return_value=[{'start':0,'end':1,'speaker':'SPEAKER_00'}]):
                turns,warnings=optional_speakers(audio,folder)
            self.assertEqual(turns[0]['speaker'],'SPEAKER_00');self.assertEqual(warnings,[])

    def test_natural_caption_finishes_phrase_instead_of_exact_three_words(self):
        parts = 'Bugun havo juda yaxshi.'.split()
        words = [Word(i*.3, i*.3+.25, text) for i,text in enumerate(parts)]
        cues = make_cues(words, max_lines=1, words_per_line=3)
        self.assertEqual([c.text for c in cues], ['Bugun havo juda yaxshi.'])
        self.assertEqual(cues[0].start, 0)
        self.assertGreaterEqual(cues[0].end, words[-1].end)

    def test_natural_caption_keeps_negation_and_helpers_attached(self):
        words = [Word(i*.3, i*.3+.25, text) for i,text in enumerate('Bu men uchun juda muhim emas.'.split())]
        cues = make_cues(words, max_lines=1, words_per_line=3)
        self.assertEqual([c.text for c in cues], ['Bu men uchun', 'juda muhim emas.'])

    def test_natural_caption_prefers_clause_boundary_and_preserves_all_words(self):
        text = 'Bugun sizga yangi maslahat beraman, lekin avval yaxshilab eshiting.'
        words = [Word(i*.3, i*.3+.25, token) for i,token in enumerate(text.split())]
        cues = make_cues(words, max_lines=1, words_per_line=3)
        self.assertEqual([c.text for c in cues], ['Bugun sizga yangi maslahat beraman,', 'lekin avval yaxshilab eshiting.'])
        self.assertEqual(' '.join(c.text.replace('\n',' ') for c in cues), text)
        self.assertTrue(all(a.end <= b.start for a,b in zip(cues,cues[1:])))

    def test_natural_caption_respects_readable_width_duration_and_pause(self):
        words = [Word(i*.5, i*.5+.4, token) for i,token in enumerate('Bugun biz yangi ishlarni birgalikda boshlaymiz va davom ettiramiz.'.split())]
        cues = make_cues(words, words_per_line=3, max_chars=22, max_lines=2, max_duration=2, min_duration=0)
        self.assertTrue(all(len(c.text.splitlines()) <= 2 for c in cues))
        self.assertTrue(all(len(line) <= 22 for c in cues for line in c.text.splitlines()))
        self.assertTrue(all(c.end-c.start <= 2.04 for c in cues))
        self.assertEqual(' '.join(c.text.replace('\n',' ') for c in cues), ' '.join(w.text for w in words))

    def test_gigaam_chunks_preserve_timeline(self):
        import numpy as np
        rate = 100
        audio = np.ones(5000, dtype=np.float32)
        chunks = list(_chunks(audio, rate))
        self.assertGreater(len(chunks), 1)
        self.assertEqual(sum(len(part) for _, part in chunks), len(audio))
        self.assertTrue(all(len(part) <= 22 * rate for _, part in chunks))
        self.assertEqual([round(offset * rate) for offset, _ in chunks],
                         [0] + [sum(len(part) for _, part in chunks[:i])
                                for i in range(1, len(chunks))])

    def test_gigaam_splits_repeated_phrases_at_silence(self):
        import numpy as np
        rate = 100
        utterance = np.ones(690, dtype=np.float32)
        pause = np.zeros(80, dtype=np.float32)
        audio = np.concatenate([utterance, pause, utterance, pause,
                                utterance, pause, utterance])
        chunks = list(_chunks(audio, rate))
        self.assertEqual(len(chunks), 4)
        self.assertEqual(sum(len(part) for _, part in chunks), len(audio))

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
        cues = make_cues(words, max_lines=1, words_per_line=3, natural=False)
        self.assertEqual([cue.text for cue in cues], ["Bugun havo juda", "yaxshi ertalab uchrashamiz"])
        self.assertTrue(all("\n" not in cue.text for cue in cues))

        cues = make_cues(words, max_lines=2, words_per_line=2, natural=False)
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

    def test_fast_words_do_not_drift_from_audio(self):
        words = [Word(i * .02, i * .02 + .015, str(i)) for i in range(5)]
        cues = make_cues(words, fps=25, max_lines=1, words_per_line=1, natural=False)
        self.assertEqual([cue.start for cue in cues], [0, .04, .08])
        self.assertEqual([cue.text for cue in cues], ["0 1", "2 3", "4"])
        self.assertTrue(all(a.end <= b.start for a, b in zip(cues, cues[1:])))

    def test_word_glossary_preserves_timing_and_punctuation(self):
        words = [Word(.2, .5, " Turkiya,"), Word(.6, .9, "OʻZBEKCHA.")]
        fixed = apply_replacements(words, ["turkiya=O‘zbekiston", "o'zbekcha=toza"])
        self.assertEqual([w.text for w in fixed], ["O'zbekiston,", "TOZA."])
        self.assertEqual([(w.start, w.end) for w in fixed], [(.2, .5), (.6, .9)])
        with self.assertRaises(ValueError):
            apply_replacements(words, ["ikki so‘z=bitta"])

    def test_exports_and_cyrillic_keep_timing(self):
        cues = make_cues([Word(.12, .5, "O'zbekcha"), Word(.5, 1.0, "shahar.")])
        self.assertIn("00:00:00.120 --> 00:00:01.000", to_vtt(cues))
        self.assertIn("Dialogue: 0,0:00:00.12,0:00:01.00", to_ass(cues))
        self.assertEqual(to_cyrillic("O'zbekcha shahar."), "Ўзбекча шаҳар.")

    def test_glossary_keeps_confidence(self):
        word = Word(0, .5, "xato", .42)
        self.assertEqual(apply_replacements([word], ["xato=to'g'ri"])[0].confidence, .42)

    def test_speaker_overlap_uses_dominant_voice(self):
        cue = make_cues([Word(1, 2, "Salom")], min_duration=0)[0]
        turns = [{"start": 1, "end": 1.2, "speaker": "SPEAKER_00"},
                 {"start": 1.2, "end": 2, "speaker": "SPEAKER_01"}]
        self.assertEqual(cue_speaker(cue, turns), "SPEAKER_01")
        self.assertIn("SPEAKER_01", to_ass([cue], ["SPEAKER_01"]))

    def test_sentence_restoration_keeps_words_and_timing(self):
        words = [Word(i * .4, i * .4 + .3, text, .7) for i, text in
                 enumerate(["bugun", "havo", "yaxshi", "ertaga", "ishlaymiz"])]
        fixed = restore_sentences(words, lambda text: "Bugun havo yaxshi. Ertaga ishlaymiz.")
        self.assertEqual([w.text for w in fixed],
                         ["Bugun", "havo", "yaxshi.", "Ertaga", "ishlaymiz."])
        self.assertEqual([(w.start, w.end, w.confidence) for w in fixed],
                         [(w.start, w.end, w.confidence) for w in words])
        self.assertEqual([c.text for c in make_cues(fixed)],
                         ["Bugun havo yaxshi.", "Ertaga ishlaymiz."])

    def test_literary_forms_preserve_timing_punctuation_and_unknown_words(self):
        words = [Word(0, .3, "Qivotti,", .8), Word(.3, .6, "shunaqa", .7),
                 Word(.6, .9, "turkcha.", .6), Word(.9, 1.2, "OʻZBEKCHA", .9)]
        fixed = standardize_literary(words)
        self.assertEqual([w.text for w in fixed],
                         ["Qilyapti,", "shunday", "turkcha.", "OʻZBEKCHA"])
        self.assertEqual([(w.start, w.end, w.confidence) for w in fixed],
                         [(w.start, w.end, w.confidence) for w in words])

    def test_corrector_cannot_insert_or_translate_words(self):
        words = [Word(0, .3, "men"), Word(.3, .6, "ozbekcha"), Word(.6, .9, "gapirdim")]
        fixed = restore_sentences(words, lambda _: "Men turkcha gapirdim.")
        self.assertEqual([w.text for w in fixed], ["Men", "ozbekcha", "gapirdim."])
        changed = restore_sentences(words, lambda _: "Merhaba nasilsin dostlar")
        self.assertEqual([w.text for w in changed], ["Men", "ozbekcha", "gapirdim."])

    def test_restoration_falls_back_to_strong_pause(self):
        words = [Word(0, .2, "salom"), Word(1.6, 1.9, "bugun"),
                 Word(2, 2.4, "yaxshi")]
        fixed = restore_sentences(words)
        self.assertEqual([w.text for w in fixed], ["Salom.", "Bugun", "yaxshi."])

    def test_long_sentence_chunk_does_not_gain_false_capital(self):
        words = [Word(i * .2, i * .2 + .15, "gap") for i in range(31)]
        fixed = restore_sentences(words, lambda text: text.capitalize() + ".")
        self.assertEqual(fixed[0].text, "Gap")
        self.assertEqual(fixed[29].text, "gap")
        self.assertEqual(fixed[30].text, "gap.")


if __name__ == "__main__":
    unittest.main()
