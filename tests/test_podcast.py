import copy
import tempfile
import unittest
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

import numpy as np
from subtitles.podcast import (camera_plan, retained_ranges, parse_timeline,
                              make_schedule, edit_xml, run, media_path)


def fixture(path, duration=300, fps=25, microphones=2):
    root=ET.Element('xmeml',version='5');seq=ET.SubElement(root,'sequence',id='original')
    ET.SubElement(seq,'name').text='O‘zbek podcast';ET.SubElement(seq,'duration').text=str(duration)
    rate=ET.SubElement(seq,'rate');ET.SubElement(rate,'timebase').text=str(fps);ET.SubElement(rate,'ntsc').text='FALSE'
    media=ET.SubElement(seq,'media')
    for kind in ('video','audio'):
        stream=ET.SubElement(media,kind)
        if kind=='video':
            sc=ET.SubElement(ET.SubElement(stream,'format'),'samplecharacteristics')
            ET.SubElement(sc,'width').text='1920';ET.SubElement(sc,'height').text='1080'
        for index in range(microphones):
            track=ET.SubElement(stream,'track');clip=ET.SubElement(track,'clipitem',id=f'{kind}{index}')
            for key,value in [('name',f'Camera {index}'),('start',0),('end',duration),('in',50),('out',duration+50),('duration',duration+50)]:
                ET.SubElement(clip,key).text=str(value)
            clip.append(copy.deepcopy(rate))
            file=ET.SubElement(clip,'file',id=f'media{index}');ET.SubElement(file,'pathurl').text=(path.parent/f'media {index}.wav').as_uri();file.append(copy.deepcopy(rate))
            audio=ET.SubElement(ET.SubElement(file,'media'),'audio');ET.SubElement(audio,'channelcount').text='1'
            source=ET.SubElement(clip,'sourcetrack');ET.SubElement(source,'mediatype').text=kind;ET.SubElement(source,'trackindex').text='1'
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
    return root


class PodcastTests(unittest.TestCase):
    def test_initial_camera_is_actual_speaker_and_brief_bleed_does_not_cut(self):
        levels=np.full((2,100),-100.);levels[1,:]=-20;levels[0,20:22]=-12
        plan=camera_plan(levels,step=3,duration=300,fps=25)
        self.assertTrue(all(p['speaker']==1 for p in plan))

    def test_sustained_speaker_changes_and_overlap_uses_wide(self):
        levels=np.full((2,100),-100.);levels[0,:50]=-20;levels[1,50:]=-20
        plan=camera_plan(levels,step=3,duration=300,fps=25)
        self.assertEqual([p['speaker'] for p in plan],[0,1])
        overlap=np.full((2,100),-20.)
        self.assertEqual(camera_plan(overlap,step=3,duration=300,fps=25,wide=True)[0]['speaker'],-1)
        with self.assertRaisesRegex(ValueError,'Nutq topilmadi'):
            camera_plan(np.full((2,100),-100.),step=3,duration=300,fps=25)

    def test_inout_preserves_outside_and_frame_exact_audio_video_ripple(self):
        with tempfile.TemporaryDirectory() as temp:
            xml=Path(temp)/'source.xml';fixture(xml);original=xml.read_bytes();timeline=parse_timeline(xml)
            plan=[{'start':0,'end':100,'speaker':0,'silent':False},
                  {'start':100,'end':175,'speaker':0,'silent':True},
                  {'start':175,'end':300,'speaker':1,'silent':False}]
            schedule=make_schedule(timeline,plan,[{'audio':0,'video':0},{'audio':1,'video':1}],wide_track=None,
                inside=50,outside=250,remove_silence=True,silence=1,padding=.2,switch_cameras=True)
            self.assertEqual(sum(s['end']-s['start'] for s in schedule),235)
            output=edit_xml(timeline,schedule,{0,1})
            self.assertEqual(output.findtext('sequence/duration'),'235')
            self.assertEqual(schedule[0]['camera'],None);self.assertEqual(schedule[-1]['camera'],None)
            # No cut changes the source offset: in = 50 + original frame.
            for clip in output.findall('sequence/media/audio/track/clipitem'):
                a=int(clip.findtext('start'));b=int(clip.findtext('end'));i=int(clip.findtext('in'));o=int(clip.findtext('out'))
                self.assertEqual(b-a,o-i);self.assertGreaterEqual(i,50)
            links=output.findall('.//link/linkclipref');ids={c.get('id') for c in output.findall('.//clipitem')}
            self.assertTrue(links);self.assertTrue(all(l.text in ids for l in links))
            self.assertEqual(xml.read_bytes(),original)
            self.assertEqual(timeline.sequence.get('id'),'original')

    def test_camera_gap_falls_back_and_total_offline_video_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            xml=Path(temp)/'source.xml';fixture(xml);timeline=parse_timeline(xml)
            timeline.video[1][0].end=100
            plan=[{'start':0,'end':300,'speaker':1,'silent':False}]
            settings=dict(wide_track=None,inside=0,outside=300,remove_silence=False,silence=1,padding=.2,switch_cameras=True)
            schedule=make_schedule(timeline,plan,[{'audio':0,'video':0},{'audio':1,'video':1}],**settings)
            self.assertEqual([s['camera'] for s in schedule],[1,0])
            timeline.video[0][0].end=100
            with self.assertRaisesRegex(ValueError,'kamera yo‘q'):
                make_schedule(timeline,plan,[{'audio':0,'video':0},{'audio':1,'video':1}],**settings)

    def test_social_format_and_motion_parameters(self):
        with tempfile.TemporaryDirectory() as temp:
            xml=Path(temp)/'source.xml';fixture(xml);timeline=parse_timeline(xml)
            output=edit_xml(timeline,[{'start':0,'end':300,'output':0,'camera':0}],{0,1},profile='vertical')
            self.assertEqual(output.findtext('sequence/media/video/format/samplecharacteristics/height'),'1920')
            parameters=output.findall('.//filter/effect/parameter/parameterid')
            self.assertEqual([p.text for p in parameters],['scale','center'])

    def test_unsupported_nested_transition_and_speed_rejected(self):
        for tag in ('nested','transition','speed'):
            with self.subTest(tag=tag),tempfile.TemporaryDirectory() as temp:
                xml=Path(temp)/'source.xml';root=fixture(xml)
                clip=root.find('sequence/media/video/track/clipitem')
                if tag=='nested':ET.SubElement(clip,'sequence')
                elif tag=='transition':ET.SubElement(root.find('sequence/media/video/track'),'transitionitem')
                else:ET.SubElement(ET.SubElement(ET.SubElement(clip,'filter'),'effect'),'effectid').text='timeremap'
                ET.ElementTree(root).write(xml)
                with self.assertRaises(ValueError):parse_timeline(xml)

    def test_unicode_path_ntsc_and_settings_validation(self):
        self.assertEqual(media_path('file://localhost/Users/me/O%CA%BBzbek%20audio.wav').name,'Oʻzbek audio.wav')
        with tempfile.TemporaryDirectory() as temp:
            xml=Path(temp)/'source.xml';root=fixture(xml,fps=30)
            for ntsc in root.findall('.//rate/ntsc'):ntsc.text='TRUE'
            ET.ElementTree(root).write(xml)
            self.assertEqual(parse_timeline(xml).fps,Fraction(30000,1001))
            with self.assertRaisesRegex(ValueError,'alohida mikrofon'):
                run(xml,Path(temp)/'edit.xml',{'speakers':[{'audio':0,'video':0},{'audio':0,'video':1}]})
            with self.assertRaisesRegex(ValueError,'threshold'):
                run(xml,Path(temp)/'edit.xml',{'speakers':[{'audio':0,'video':0}],'threshold':float('nan')})

    def test_empty_selected_range_does_not_pass_due_to_speech_elsewhere(self):
        with tempfile.TemporaryDirectory() as temp:
            xml=Path(temp)/'source.xml';fixture(xml);levels=np.full(100,-100.);levels[:20]=-20
            with patch('subtitles.podcast.track_activity',return_value=levels),self.assertRaisesRegex(ValueError,'In/Out'):
                run(xml,Path(temp)/'edit.xml',{'speakers':[{'audio':0,'video':0}],'start':8,'end':10})

    def test_xml_keeps_file_and_track_metadata_order_and_disabled_clips(self):
        with tempfile.TemporaryDirectory() as temp:
            xml=Path(temp)/'source.xml';root=fixture(xml)
            for track in root.findall('sequence/media/video/track'):
                ET.SubElement(track,'enabled').text='TRUE'
                ET.SubElement(track,'locked').text='FALSE'
            clip=root.find('sequence/media/video/track/clipitem')
            ET.SubElement(clip,'enabled').text='FALSE'
            ET.ElementTree(root).write(xml)
            timeline=parse_timeline(xml)
            result=edit_xml(timeline,[{'start':0,'end':300,'output':0,'camera':1}],{0,1})
            first=result.find('sequence/media/video/track')
            self.assertEqual([n.tag for n in first],['clipitem','enabled','locked'])
            copy=first.find('clipitem')
            self.assertEqual(copy.findtext('enabled'),'FALSE')
            self.assertLess([n.tag for n in copy].index('file'),[n.tag for n in copy].index('sourcetrack'))
