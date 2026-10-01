import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from subtitles.cli import Word
from subtitles.reels import (tokens,utterances,retake_proposals,repeated,schedule_from_removals,run)
from test_podcast import fixture


def speech(sentences,gap=1):
    words=[];clock=0
    for sentence in sentences:
        for part in sentence.split():
            words.append(Word(clock,clock+.25,' '+part,.95));clock+=.3
        clock+=gap
    return words

class ReelsTests(unittest.TestCase):
    def test_six_repeated_takes_keep_last_complete(self):
        text='Bugun sizga juda foydali maslahat beraman.'
        parts=utterances(speech([text]*6))
        proposals=retake_proposals(parts)
        self.assertEqual(len(proposals),5)
        self.assertEqual({p['kept_id'] for p in proposals},{5})

    def test_unfinished_restart_replaced_by_full_sentence(self):
        parts=utterances(speech(['Bugun sizga juda','Bugun sizga juda foydali maslahat beraman.']))
        proposals=retake_proposals(parts)
        self.assertEqual(len(proposals),1);self.assertEqual(proposals[0]['id'],0)

    def test_complete_take_beats_later_fragment(self):
        parts=utterances(speech(['Bugun sizga juda foydali maslahat beraman.','Bugun sizga juda']))
        self.assertEqual(retake_proposals(parts)[0]['kept_id'],0)

    def test_numbers_negation_changed_content_and_short_emphasis_are_kept(self):
        pairs=[['Buni olish uchun 5 kun kerak.','Buni olish uchun 6 kun kerak.'],
               ['Bu ish biz uchun juda yaxshi.','Bu ish biz uchun juda yaxshi emas.'],
               ['Bugun men sizga foydali maslahat beraman.','Bugun men sizga zararli maslahat beraman.'],
               ['Bu juda muhim.','Bu juda muhim.']]
        for pair in pairs:
            with self.subTest(pair=pair):self.assertEqual(retake_proposals(utterances(speech(pair)),strength='balanced'),[])

    def test_apostrophes_and_case_normalize_without_changing_source_words(self):
        self.assertEqual(tokens('O‘ZBEKCHA yozuv!'),tokens("o'zbekcha yozuv"))
        words=speech(['Bugun O‘zbekcha yozuv haqida gaplashamiz.','Bugun o\'zbekcha yozuv haqida gaplashamiz.'])
        original=list(words)
        self.assertEqual(len(retake_proposals(utterances(words))),1)
        self.assertEqual(words,original)

    def test_low_confidence_and_distant_repeats_not_removed(self):
        words=speech(['Bugun sizga juda foydali maslahat beraman.']*2,gap=60)
        self.assertEqual(retake_proposals(utterances(words)),[])
        low=[Word(w.start,w.end,w.text,.3) for w in speech(['Bugun sizga juda foydali maslahat beraman.']*2)]
        self.assertEqual(retake_proposals(utterances(low)),[])

    def test_balanced_only_allows_discourse_fillers(self):
        parts=utterances(speech(['Bugun sizga juda foydali yangi maslahat beraman.','Ha bugun sizga juda foydali yangi maslahat beraman.']))
        self.assertEqual(retake_proposals(parts,strength='safe'),[])
        self.assertEqual(len(retake_proposals(parts,strength='balanced')),1)

    def test_overlapping_removals_are_merged_and_audio_frames_do_not_drift(self):
        plan=schedule_from_removals([(25,50),(40,80),(90,100)],200)
        self.assertEqual([(p['start'],p['end'],p['output']) for p in plan],[(0,25,0),(80,90,25),(100,200,35)])
        with self.assertRaises(ValueError):schedule_from_removals([(0,200)],200)

    def test_run_preserves_original_and_approved_take_with_cached_words(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);source=folder/'source.xml';fixture(source,duration=500,microphones=1)
            words=speech(['Bugun sizga juda foydali maslahat beraman.']*2)
            settings={'audio':0,'remove_silence':False}
            with patch('subtitles.reels.track_activity',return_value=np.full(167,-20.)),patch('subtitles.reels.cached_transcript',return_value=(words,True)):
                original=source.read_bytes();report=run(source,folder/'edit.xml',settings)
                self.assertEqual(report['removed_retakes'],1);self.assertGreater(report['removed_seconds'],1)
                settings['keep_retake_ids']=[0];report=run(source,folder/'keep.xml',settings)
                self.assertEqual(report['removed_retakes'],0);self.assertEqual(report['output_frames'],500)
                self.assertEqual(original,source.read_bytes())

    def test_inout_silence_cut_keeps_outside_and_no_speech_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);source=folder/'source.xml';fixture(source,duration=500,microphones=1)
            levels=np.full(167,-100.);levels[45:55]=-20
            settings={'audio':0,'start':4,'end':8,'remove_retakes':False}
            with patch('subtitles.reels.track_activity',return_value=levels):
                report=run(source,folder/'edit.xml',settings)
                self.assertEqual(report['cuts'][0]['start'],0);self.assertEqual(report['cuts'][-1]['end'],500)
                self.assertLess(report['removed_seconds'],4)
            with patch('subtitles.reels.track_activity',return_value=np.full(167,-100.)),self.assertRaisesRegex(ValueError,'nutq topilmadi'):
                run(source,folder/'none.xml',settings)

    def test_invalid_settings_and_word_times_fail(self):
        with self.assertRaises(ValueError):utterances([Word(float('nan'),1,'Salom')])
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source.xml';fixture(source)
            for settings in ({'audio':99},{'padding':float('nan')},{'strength':'random'}):
                with self.subTest(settings=settings),self.assertRaises(ValueError):run(source,source.parent/'edit.xml',settings)
