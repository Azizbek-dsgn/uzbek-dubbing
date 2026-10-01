"""Local Uzbek retake cleanup on an exported Premiere timeline.

ASR proposes repeated takes; VAD controls silence removal independently so an
unrecognized word is never mistaken for silence. The source sequence is retained.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
import subprocess
import sys
import tempfile
import unicodedata
import wave
from difflib import SequenceMatcher
from pathlib import Path
import xml.etree.ElementTree as ET

# Match the verified Intel installation native-library initialization order.
if sys.platform == 'darwin' and platform.machine().lower() == 'x86_64':
    try:
        import torch
    except ImportError:
        pass

if __package__:
    from .cli import Word, transcribe, _join
    from .podcast import audio_route, speech_activity, parse_timeline, track_activity, retained_ranges, edit_xml
else:
    from cli import Word, transcribe, _join
    from podcast import audio_route, speech_activity, parse_timeline, track_activity, retained_ranges, edit_xml


def reels_transcribe(audio, model, device, progress=None):
    return transcribe(audio,model,device,progress=progress,preserve_repeats=True)

def tokens(text):
    text=unicodedata.normalize('NFKC',text).casefold()
    for apostrophe in ('’','‘','ʻ','ʼ','`'):
        text=text.replace(apostrophe,"'")
    return re.findall(r"[\w]+(?:'[\w]+)*",text,flags=re.UNICODE)


def utterances(words, *, gap=.65):
    result=[];current=[]
    for word in words:
        if (not math.isfinite(word.start) or not math.isfinite(word.end) or
                word.start<0 or word.end<=word.start):
            raise ValueError('Transkripsiya so‘z vaqti noto‘g‘ri.')
        if current and (word.start-current[-1].end>=gap or
                        re.search(r'[.!?…]["”\']?\s*$',current[-1].text) or len(current)>=40):
            result.append(current);current=[]
        current.append(word)
    if current:result.append(current)
    return [{'id':i,'start':group[0].start,'end':group[-1].end,'text':_join(group),
             'tokens':tokens(_join(group)),
             'complete':bool(re.search(r'[.!?…]["”\']?\s*$',group[-1].text)),
             'confidence':sum(w.confidence if w.confidence is not None else 1 for w in group)/len(group)}
            for i,group in enumerate(result)]


def protected(parts):
    # Uzbek negation and numbers are meaningful even when every other word matches.
    return {p for p in parts if any(c.isdigit() for c in p) or
            p in {'emas','yo‘q',"yo'q",'yoq','hech','нет','не'} or
            re.search(r'(maydi|magan|mas|ма[йг]|эмас)$',p)}


def repeated(a,b,strength='safe'):
    if min(a.get('confidence',1),b.get('confidence',1))<.6:return False
    left,right=a['tokens'],b['tokens']
    if protected(left)!=protected(right):return False
    if min(len(left),len(right))<3:return False
    if left==right:return len(left)>=4
    # A restarted, unfinished prefix may be replaced by the full sentence.
    short,long=(a,b) if len(left)<len(right) else (b,a)
    if not short['complete'] and len(short['tokens'])>=3 and long['tokens'][:len(short['tokens'])]==short['tokens']:
        return len(long['tokens'])>=len(short['tokens'])+2
    if strength!='balanced' or min(len(left),len(right))<6:return False
    matcher=SequenceMatcher(None,left,right,autojunk=False)
    # Only harmless discourse fillers may differ. Similar subject matter is not a retake.
    fillers={'ha','xo‘sh',"xo'sh",'xosh','demak','hmm','eee'}
    changed=[]
    for op,la,lb,ra,rb in matcher.get_opcodes():
        if op!='equal':changed.extend(left[la:lb]+right[ra:rb])
    return matcher.ratio()>=.9 and bool(changed) and set(changed)<=fillers


def retake_proposals(parts, *, window=45, strength='safe', keep='complete'):
    parents=list(range(len(parts)))
    def find(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]];i=parents[i]
        return i
    for j,b in enumerate(parts):
        # Compare nearby attempts, not identical phrases from a later topic.
        for i in range(max(0,j-2),j):
            if b['start']-parts[i]['end']<=window and repeated(parts[i],b,strength):
                parents[find(i)]=find(j)
    groups={}
    for i in range(len(parts)):groups.setdefault(find(i),[]).append(i)
    proposals=[]
    for indices in groups.values():
        if len(indices)<2:continue
        if keep=='last':winner=indices[-1]
        else:winner=max(indices,key=lambda i:(len(parts[i]['tokens']),parts[i]['complete'],parts[i]['confidence'],i))
        for i in indices:
            if i!=winner:
                proposals.append({'id':parts[i]['id'],'start':parts[i]['start'],'end':parts[i]['end'],
                                  'text':parts[i]['text'],'kept_id':parts[winner]['id'],
                                  'kept_text':parts[winner]['text'],'reason':'Takroriy dubl'})
    return sorted(proposals,key=lambda p:p['start'])


def merged_ranges(ranges, duration):
    result=[]
    for a,b in sorted((max(0,a),min(duration,b)) for a,b in ranges if b>a):
        if b<=a:continue
        if result and a<=result[-1][1]:result[-1]=(result[-1][0],max(b,result[-1][1]))
        else:result.append((a,b))
    return result


def schedule_from_removals(ranges, duration):
    schedule=[];position=output=0
    for a,b in merged_ranges(ranges,duration)+[(duration,duration)]:
        if a>position:
            schedule.append({'start':position,'end':a,'output':output,'camera':None});output+=a-position
        position=b
    if not schedule:raise ValueError('Natija bo‘sh. Kesish sozlamalarini kamaytiring.')
    return schedule


def render_audio(timeline, track, inside, outside, output):
    """Stream a selected timeline audio channel to WAV, preserving source offsets/gaps."""
    import imageio_ffmpeg
    if not isinstance(track,int) or not 0<=track<len(timeline.audio):raise ValueError('Audio trek topilmadi.')
    clips=sorted((c for c in timeline.audio[track] if c.enabled and c.end>inside and c.start<outside),key=lambda c:c.start)
    if not clips:raise ValueError('Tanlangan audio trek bu oraliqda bo‘sh.')
    fps=float(timeline.fps);cursor=0;total=round((outside-inside)/fps*16000)
    with wave.open(str(output),'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000)
        def zeros(count):
            while count>0:
                block=min(count,16000);wav.writeframesraw(b'\0\0'*block);count-=block
        for clip in clips:
            a,b=max(inside,clip.start),min(outside,clip.end)
            start,end=round((a-inside)/fps*16000),round((b-inside)/fps*16000)
            if start<cursor:raise ValueError('Audio trekda ustma-ust kliplar bor. Avval alohida trekka joylang.')
            if not clip.path.is_file():raise ValueError('Media offline: '+clip.path.name)
            audio_stream,audio_channel=audio_route(clip)
            zeros(start-cursor);cursor=start
            seek=float(clip.inside/clip.fps)+(a-clip.start)/fps
            command=[imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-v','error','-ss',str(seek),'-i',str(clip.path),
                     '-t',str((b-a)/fps),'-map',f'0:a:{audio_stream}','-vn','-af',f'pan=mono|c0=c{audio_channel}',
                     '-ar','16000','-f','s16le','pipe:1']
            with tempfile.TemporaryFile() as error:
                process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=error)
                try:
                    while True:
                        data=process.stdout.read(65536)
                        if not data:break
                        usable=data[:max(0,(end-cursor)*2)];wav.writeframesraw(usable);cursor+=len(usable)//2
                    if process.wait():
                        error.seek(0);raise ValueError('Audio o‘qilmadi: '+error.read().decode('utf-8','replace')[-800:])
                finally:
                    if process.poll() is None:process.kill();process.wait()
                    process.stdout.close()
            # A truncated source must not silently become a proposed silence cut.
            if end-cursor>800:raise ValueError('Manba audio klipdan qisqa. Offline yoki trim mosligini tekshiring.')
            zeros(end-cursor);cursor=end
        zeros(total-cursor)


def cached_transcript(timeline, track, inside, outside, model, cache, decode=reels_transcribe):
    root=Path(__file__).resolve().parents[1]
    if model not in {'gigaam-uzbek','large-v3','navai-medium'}:raise ValueError('Nutq modelini tekshiring.')
    clips=[]
    for c in timeline.audio[track]:
        if not c.enabled or c.end<=inside or c.start>=outside:continue
        stat=c.path.stat();clips.append([str(c.path),stat.st_size,stat.st_mtime_ns,c.start,c.end,c.inside,c.outside,str(c.fps),c.channel])
    model_files=[root/'models'/model/'model.bin'] if model!='gigaam-uzbek' else [root/'models/gigaam-uzbek/checkpoints/large_full_600m/best.pt',root/'models/gigaam-base-large/modeling_gigaam.py']
    weights=[[str(p),p.stat().st_size,p.stat().st_mtime_ns] for p in model_files if p.is_file()]
    key=hashlib.sha256(json.dumps([3,model,weights,str(timeline.fps),inside,outside,clips],ensure_ascii=False).encode()).hexdigest()
    cache.mkdir(parents=True,exist_ok=True);file=cache/(key+'.json')
    if file.is_file():
        try:
            data=json.loads(file.read_text(encoding='utf-8'));return [Word(**w) for w in data['words']],True
        except (ValueError,TypeError,KeyError):pass
    print('UZREELS O‘zbekcha nutq tanilmoqda…',flush=True)
    with tempfile.TemporaryDirectory(prefix='uzscribe-reels-') as temporary:
        audio=Path(temporary)/'timeline.wav';render_audio(timeline,track,inside,outside,audio)
        words=decode(audio,model,'auto',progress=lambda done,total:print(f'UZREELS Nutq {round(done/max(1,total)*100)}%',flush=True))
    offset=inside/float(timeline.fps)
    words=[Word(w.start+offset,w.end+offset,w.text,w.confidence) for w in words]
    data={'schema':2,'model':model,'words':[w.__dict__ for w in words]}
    temporary=file.with_suffix('.tmp');temporary.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');temporary.replace(file)
    return words,False


def run(source,output,settings,*,vad=True,decode=reels_transcribe):
    timeline=parse_timeline(source,allow_transitions=True);fps=float(timeline.fps)
    def number(key,default,low,high):
        value=float(settings.get(key,default))
        if not math.isfinite(value) or not low<=value<=high:raise ValueError('Reels sozlamasi noto‘g‘ri: '+key)
        return value
    inside=round(number('start',0,0,timeline.duration/fps)*fps)
    outside=round(number('end',timeline.duration/fps,0,timeline.duration/fps)*fps)
    if inside>=outside:raise ValueError('In/Out oralig‘i noto‘g‘ri.')
    track=settings.get('audio',0)
    if not isinstance(track,int) or not 0<=track<len(timeline.audio):raise ValueError('Audio trek topilmadi.')
    model=settings.get('model','gigaam-uzbek');strength=settings.get('strength','safe');keep=settings.get('keep','complete')
    if strength not in {'safe','balanced'} or keep not in {'complete','last'}:raise ValueError('Dubl tanlovini tekshiring.')
    gap=number('sentence_gap',.65,.2,3);silence=number('silence',.7,.3,10);padding=number('padding',.18,.08,.5)
    threshold=number('threshold',-42,-80,-10);window=number('window',45,3,120)
    if not any(c.enabled for t in timeline.video for c in t):raise ValueError('Faol video klip topilmadi.')
    print('UZREELS Nutq va pauzalar tahlili…',flush=True)
    step=max(1,round(fps/10));track,activity,audio_warning=speech_activity(timeline,track,step,inside,outside,threshold,vad=vad)
    if not any(activity[inside//step:math.ceil(outside/step)]>threshold):raise ValueError('Tanlangan audio kanalida bu oraliqda nutq topilmadi. Nutqli audio trekni tanlang; mikrofon va trekning mute holatini tekshiring.')
    plan=[{'start':i*step,'end':min(timeline.duration,(i+1)*step),'silent':bool(level<=threshold)} for i,level in enumerate(activity)]
    retained=retained_ranges(plan,timeline.duration,inside=inside,outside=outside,
                             remove_silence=bool(settings.get('remove_silence',True)),silence_frames=round(silence*fps),pad_frames=round(padding*fps))
    ranges=[];cursor=0
    for a,b in retained:
        if a>cursor:ranges.append((cursor,a))
        cursor=b
    if cursor<timeline.duration:ranges.append((cursor,timeline.duration))
    proposals=[];parts=[];cached=False
    if settings.get('remove_retakes',True):
        words,cached=cached_transcript(timeline,track,inside,outside,model,source.parent/'reels-cache',decode)
        if not words:raise ValueError('Nutq matni tanilmadi. Boshqa model yoki faqat pauza rejimini sinang.')
        parts=utterances(words,gap=gap);proposals=retake_proposals(parts,window=window,strength=strength,keep=keep)
        protected_ids=settings.get('keep_retake_ids',[])
        for proposal in proposals:
            proposal['remove']=proposal['id'] not in protected_ids
            if not proposal['remove']:continue
            part=parts[proposal['id']];previous=parts[proposal['id']-1]['end'] if proposal['id'] else inside/fps
            following=parts[proposal['id']+1]['start'] if proposal['id']+1<len(parts) else outside/fps
            a=max(inside,round(max(previous,part['start']-.08)*fps))
            b=min(outside,round(min(following,part['end']+.08)*fps))
            if b>a:ranges.append((a,b))
    schedule=schedule_from_removals(ranges,timeline.duration)
    result=edit_xml(timeline,schedule,set(),profile=settings.get('profile','original'))
    result.find('sequence/name').text=timeline.sequence.findtext('name','Reels')+' · UzScribe Reels'
    total=sum(s['end']-s['start'] for s in schedule)
    report={'schema':1,'xml':str(output),'fps':fps,'model':model,'cached_transcript':cached,
            'original_frames':timeline.duration,'output_frames':total,'output_seconds':total/fps,
            'removed_seconds':(timeline.duration-total)/fps,'retakes':proposals,
            'removed_retakes':sum(p['remove'] for p in proposals),'cuts':schedule,
            'audio': track, 'warnings': ([audio_warning] if audio_warning else []) + (['Timeline’da yaratilgan qatlamlar bor. Premiere XML ayrim Adjustment Layer/Graphic effektlarini saqlamaydi; yangi sequence ko‘rinishini tekshiring.'] if any(c.path is None for t in timeline.video for c in t) else []) + (['Kesishga tushgan fade/transition yangi sequence’da olib tashlanadi.'] if len(result.findall('.//transitionitem')) < len(timeline.sequence.findall('.//transitionitem')) else []),
            'transcript':[{k:v for k,v in p.items() if k!='tokens'} for p in parts]}
    output.parent.mkdir(parents=True,exist_ok=True);temporary=output.with_suffix('.tmp.xml')
    ET.ElementTree(result).write(temporary,encoding='utf-8',xml_declaration=True);temporary.replace(output)
    output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description='UzScribe Reels: o‘zbekcha dubl va pauzalarni tozalash')
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--settings',type=Path,required=True)
    args=parser.parse_args()
    try:run(args.input,args.output,json.loads(args.settings.read_text(encoding='utf-8')))
    except (OSError,ValueError,KeyError,TypeError,ImportError,ET.ParseError,subprocess.SubprocessError) as exc:
        print('Reels montaji tugamadi: '+str(exc),file=sys.stderr);return 1
    print('UZREELS Reels montaji tayyor.',flush=True);return 0

if __name__=='__main__':raise SystemExit(main())
