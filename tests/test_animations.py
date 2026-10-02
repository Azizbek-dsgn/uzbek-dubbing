import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from subtitles.animations import make_plan,frame,render,refine,PRESETS
from subtitles.cli import Word

class AnimationTests(unittest.TestCase):
    def data(self,preset='karaoke'):
        return {'width':320,'height':568,'fps':12,'theme':{'preset':preset,'keywords':['yangi']},'cues':[{'start':0,'end':1,'text':'Salom yangi dunyo.'}],'words':[{'start':0,'end':.3,'text':'Salom'},{'start':.3,'end':.6,'text':'yangi'},{'start':.6,'end':1,'text':'dunyo.'}]}
    def test_presets_are_transparent_and_safe(self):
        for preset in PRESETS:
            with self.subTest(preset=preset):
                data=self.data(preset);before=copy.deepcopy(data);plan=make_plan(data);im=frame(plan,.45);alpha=im.getchannel('A');bounds=alpha.getbbox()
                self.assertEqual(im.getpixel((0,0))[3],0);self.assertIsNotNone(bounds);self.assertLess(bounds[3],568*.80);self.assertEqual(data,before);self.assertIsNone(frame(plan,1.01).getchannel('A').getbbox())
    def test_actual_movie_retains_alpha(self):
        import av
        with tempfile.TemporaryDirectory() as tmp:
            for preset in PRESETS:
                output=Path(tmp)/f'{preset}.mov';plan=make_plan(self.data(preset));render(plan,output)
                with av.open(str(output)) as media:
                    video=media.streams.video[0];self.assertEqual(video.codec_context.name,'qtrle');frames=list(media.decode(video));self.assertEqual(len(frames),12);rgba=frames[5].to_ndarray(format='rgba');self.assertEqual(rgba[0,0,3],0);self.assertGreater(rgba[:,:,3].max(),0)
                self.assertFalse(output.with_name(output.stem+'.partial.mov').exists())
    def test_text_changes_require_explicit_word_times(self):
        data=self.data();data['cues'][0]['text']='Mutlaqo boshqa gap.'
        with self.assertRaisesRegex(ValueError,'mos emas'):make_plan(data)
        data['theme']['preset']='slide';self.assertTrue(make_plan(data)['cues'])
    def test_rounding_does_not_assign_neighbor_word(self):
        data=self.data();data['cues']=[{'start':0,'end':.32,'text':'Salom'},{'start':.32,'end':1,'text':'yangi dunyo.'}];plan=make_plan(data);self.assertEqual(len(plan['cues'][0]['runs']),1);self.assertEqual(len(plan['cues'][1]['runs']),2)
    def test_invalid_times_and_style_are_rejected(self):
        for change in [lambda d:d['theme'].update(color='red'),lambda d:d['words'][0].update(end=0),lambda d:d.update(width=0),lambda d:d['theme'].update(speed=0)]:
            data=self.data();change(data)
            with self.assertRaises(ValueError):make_plan(data)
    def test_line_breaks_remain(self):
        data=self.data();data['cues'][0]['text']='Salom\nyangi dunyo.';runs=make_plan(data)['cues'][0]['runs'];self.assertLess(runs[0]['y'],runs[1]['y']);self.assertEqual(runs[1]['y'],runs[2]['y'])
    def test_refinement_keeps_text_and_rejects_different_speech(self):
        data=self.data();before=copy.deepcopy(data)
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'times.json'
            with patch('subtitles.cli.transcribe',return_value=[Word(.01,.28,'Salom'),Word(.31,.58,'yangi'),Word(.62,1,'dunyo')]):refine(data,'audio.wav',output)
            self.assertEqual(data,before);self.assertIn('dunyo.',output.read_text())
            with patch('subtitles.cli.transcribe',return_value=[Word(0,1,'Boshqa')]):
                with self.assertRaisesRegex(ValueError,'mos kelmadi'):refine(data,'audio.wav',output)
