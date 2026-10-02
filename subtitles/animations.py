"""UzScribe's own offline caption animation planner and transparent renderer."""
from __future__ import annotations
import argparse,json,math,re,os,signal,subprocess,tempfile,struct
from functools import lru_cache
from pathlib import Path
from difflib import SequenceMatcher
from PIL import Image,ImageDraw,ImageFont

PRESETS={'karaoke','pop','pill','reveal','slide','emphasis'}
def lexical(text):
    return re.sub(r"[^\w']",'',text.casefold().translate(str.maketrans('‘’ʻʼ',"''''")))
def color(value):
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',str(value)):raise ValueError('Rangni #RRGGBB shaklida kiriting.')
    return value

def font_path(wanted=''):
    candidates=[wanted,'/System/Library/Fonts/Supplemental/Arial Bold.ttf',
                str(Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts/arialbd.ttf'),
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
    for p in candidates:
        if p and Path(p).is_file():return p
    raise ValueError('Shrift topilmadi. Uslub sozlamasidan TTF/OTF shrift tanlang.')

def postscript_name(path,fallback):
    # OpenType name ID 6 is the name expected by AE TextDocument.font.
    try:
        data=Path(path).read_bytes();count=struct.unpack_from('>H',data,4)[0]
        for i in range(count):
            tag,_,offset,length=struct.unpack_from('>4sIII',data,12+i*16)
            if tag!=b'name':continue
            table=data[offset:offset+length];_,n,storage=struct.unpack_from('>HHH',table)
            for j in range(n):
                platform,encoding,language,name,length,start=struct.unpack_from('>HHHHHH',table,6+j*12)
                if name==6 and platform in (0,1,3):
                    result=table[storage+start:storage+start+length].decode('mac_roman' if platform==1 else 'utf-16-be')
                    if result and len(result)<=63 and all(33<=ord(c)<=126 and c not in '[](){}<>/%' for c in result):return result
    except (OSError,ValueError,struct.error):pass
    return fallback

def make_plan(data):
    theme=dict(data.get('theme',{}));preset=theme.get('preset','karaoke')
    if preset not in PRESETS:raise ValueError('Animatsiya presetini tekshiring.')
    width=int(data.get('width',1920));height=int(data.get('height',1080));fps=float(data.get('fps',25))
    if not 64<=width<=7680 or not 64<=height<=7680 or not 1<=fps<=120:raise ValueError('Video o‘lchami/FPS noto‘g‘ri.')
    size=float(theme.get('size',56));speed=float(theme.get('speed',.16))
    if not 16<=size<=160 or not .05<=speed<=.6:raise ValueError('Shrift/animatsiya tezligini tekshiring.')
    theme.update(preset=preset,color=color(theme.get('color','#FFFFFF')),active=color(theme.get('active','#F5D76E')),
                 position=theme.get('position','bottom'),safe=bool(theme.get('safe',True)),speed=speed)
    if theme['position'] not in {'top','center','bottom'}:raise ValueError('Subtitr joylashuvini tekshiring.')
    fp=font_path(theme.get('font',''));base_size=max(14,round(size*height/1080));font=ImageFont.truetype(fp,base_size)
    theme['fontFamily']=font.getname()[0];theme['fontPostscript']=postscript_name(fp,font.getname()[0]);theme['font']=fp
    highlights={lexical(t) for t in theme.get('keywords',[])}
    words=sorted(data.get('words',[]),key=lambda w:float(w['start']))
    previous=0
    for w in words:
        a,b=float(w['start']),float(w['end'])
        if not math.isfinite(a+b) or a<0 or b<=a or a<previous-.001:raise ValueError('So‘z vaqtlari tartibsiz. Vaqtni tahrirlashdan tekshiring.')
        previous=a
    plans=[];previous=0;cursor=0
    for index,c in enumerate(data.get('cues',[])):
        a,b=float(c['start']),float(c['end']);text=str(c['text']).strip()
        if not math.isfinite(a+b) or not 0<=a<b or a<previous-.001 or not text:raise ValueError('Subtitr matni/vaqti noto‘g‘ri.')
        previous=b
        tokens=text.split();matches=words[cursor:cursor+len(tokens)]
        if [lexical(w['text']) for w in matches]!=[lexical(t) for t in tokens]:
            matches=[w for w in words if float(w['start'])<b and float(w['end'])>a]
        else:cursor+=len(tokens)
        # Punctuation edits are safe; changing recognized words needs explicit timing edits.
        if preset!='slide' and [lexical(w['text']) for w in matches]!=[lexical(t) for t in tokens]:
            raise ValueError(f'{index+1}-subtitr matni so‘z vaqtlariga mos emas. Qayta taning yoki so‘z vaqtlarini tuzating; Slide + Fade vaqtli so‘zsiz ham ishlaydi.')
        if preset!='slide' and any(min(b,float(w['end']))<=max(a,float(w['start'])) for w in matches):
            raise ValueError(f'{index+1}-subtitr so‘zlari vaqt oralig‘iga sig‘madi. So‘z vaqtlari yoki SRT chegaralarini tekshiring.')
        f=font;fs=base_size
        # Wrap by measured pixels, then reduce only if a single word is too wide.
        longest=max(float(f.getlength(t)) for t in tokens)
        if longest>width*.80:fs=max(12,int(fs*width*.80/longest));f=ImageFont.truetype(fp,fs)
        lines=[];current=[]
        explicit_lines=text.splitlines();breaks=set();n=0
        for line in explicit_lines[:-1]:n+=len(line.split());breaks.add(n)
        for ti,token in enumerate(tokens):
            if current and ti in breaks:lines.append(current);current=[]
            if current and f.getlength(' '.join(current+[token]))>width*.80:lines.append(current);current=[]
            current.append(token)
        if current:lines.append(current)
        line_height=round(fs*1.35);block_height=len(lines)*line_height
        y={'top':height*.16,'center':(height-block_height)/2,
           'bottom':height*(.77 if theme['safe'] and height>width else .88)-block_height}[theme['position']]
        if block_height>height*.60:raise ValueError('Subtitr ekranga sig‘madi. Qatorni bo‘ling yoki shriftni kichraytiring.')
        y=max(height*.08,min(y,height*.92-block_height));runs=[];token_index=0
        for li,line in enumerate(lines):
            x=(width-float(f.getlength(' '.join(line))))/2
            for token in line:
                w=matches[token_index] if matches and preset!='slide' else None
                runs.append({'text':token,'start':max(a,float(w['start'])) if w else a,
                             'end':min(b,float(w['end'])) if w else b,'x':round(x,2),'y':round(y+li*line_height,2),
                             'width':round(float(f.getlength(token)),2),'height':line_height,'emphasis':lexical(token) in highlights})
                x+=float(f.getlength(token+' '));token_index+=1
        plans.append({'start':a,'end':b,'text':text,'size':fs,'runs':runs})
    if not plans:raise ValueError('Subtitr yo‘q.')
    return {'schema':1,'width':width,'height':height,'fps':fps,'duration':plans[-1]['end'],'theme':theme,'cues':plans}

@lru_cache(maxsize=64)
def load_font(path,size):return ImageFont.truetype(path,size)

def frame(plan,time):
    image=Image.new('RGBA',(plan['width'],plan['height']),(0,0,0,0))
    cue=next((c for c in plan['cues'] if c['start']<=time<c['end']),None)
    if cue is None:return image
    theme=plan['theme'];preset=theme['preset'];f=load_font(theme['font'],cue['size']);draw=ImageDraw.Draw(image)
    active=next((r for r in cue['runs'] if r['start']<=time<r['end']),None)
    if preset=='pill' and active:
        i=cue['runs'].index(active);prev=cue['runs'][max(0,i-1)];progress=min(1,max(0,(time-active['start'])/theme['speed']))
        x=prev['x']+(active['x']-prev['x'])*progress;y=prev['y']+(active['y']-prev['y'])*progress
        w=prev['width']+(active['width']-prev['width'])*progress
        draw.rounded_rectangle((x-8,y-3,x+w+8,y+active['height']-4),radius=10,fill=theme['active']+'B0')
    for r in cue['runs']:
        if preset=='reveal' and time<r['start']:continue
        fill=theme['active'] if ((preset in {'karaoke','pop'} and r is active) or (preset=='emphasis' and r['emphasis'])) else theme['color']
        x,y=r['x'],r['y'];rf=f
        if preset=='pop' and r is active:
            phase=min(1,max(0,(time-r['start'])/theme['speed']));scale=1+.14*math.sin(math.pi*phase)
            rf=load_font(theme['font'],max(12,round(cue['size']*scale)))
            x-=(float(rf.getlength(r['text']))-r['width'])/2;y-=(rf.size-f.size)/2
        alpha=255
        if preset=='slide':
            p=min(1,max(0,(time-cue['start'])/theme['speed']));p=1-(1-p)**3;y+=24*(1-p)
            alpha=round(255*min(p,max(0,(cue['end']-time)/min(theme['speed'],(cue['end']-cue['start'])/2))))
        draw.text((x,y),r['text'],font=rf,fill=fill+f'{alpha:02X}',stroke_width=max(1,round(cue['size']/32)),stroke_fill=(0,0,0,alpha),anchor='lt')
    return image

def render(plan,output):
    import imageio_ffmpeg
    output=Path(output);temp=output.with_name(output.stem+'.partial.mov');output.parent.mkdir(parents=True,exist_ok=True)
    count=math.ceil(plan['duration']*plan['fps'])
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-v','error','-y','-f','rawvideo','-pix_fmt','rgba','-s',f"{plan['width']}x{plan['height']}",'-r',str(plan['fps']),'-i','pipe:0','-an','-c:v','qtrle','-pix_fmt','argb',str(temp)]
    process=None
    def terminate(*_):
        if process is not None:process.terminate()
        raise KeyboardInterrupt
    old=signal.signal(signal.SIGTERM,terminate)
    try:
        with tempfile.TemporaryFile() as error:
            process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=error)
            try:
                for i in range(count):
                    process.stdin.write(frame(plan,i/plan['fps']).tobytes())
                    if i%max(1,round(plan['fps']))==0:print(f'UZANIM {round(i/count*100)}%',flush=True)
                process.stdin.close()
                if process.wait():
                    error.seek(0);raise ValueError(error.read().decode('utf-8','replace')[-1000:])
            finally:
                if process.poll() is None:process.kill();process.wait()
                if process.stdin and not process.stdin.closed:process.stdin.close()
        temp.replace(output)
    finally:
        signal.signal(signal.SIGTERM,old);temp.unlink(missing_ok=True)


def refine(data,audio,output):
    try:from .cli import transcribe
    except ImportError:from cli import transcribe
    recognized=transcribe(Path(audio),'large-v3','auto')
    original=data.get('words',[]);matched=0;result=[dict(w) for w in original]
    match=SequenceMatcher(None,[lexical(w['text']) for w in original],[lexical(w.text) for w in recognized],autojunk=False)
    for block in match.get_matching_blocks():
        for i in range(block.size):
            old=result[block.a+i];new=recognized[block.b+i]
            old.update(start=new.start,end=new.end);matched+=1
    # Reject insufficient agreement rather than inventing timings for different words.
    if not original or matched/len(original)<.8:raise ValueError('Whisper matni yetarlicha mos kelmadi. So‘z vaqtlarini qo‘lda tekshiring; oldingi vaqtlar saqlandi.')
    if any(a['end']>b['start']+.04 for a,b in zip(result,result[1:])):raise ValueError('Moslashtirilgan so‘z vaqtlari to‘qnashdi. Oldingi vaqtlar saqlandi.')
    Path(output).write_text(json.dumps({'words':result,'matched':matched,'total':len(original)},ensure_ascii=False),encoding='utf-8')

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--plan-only',action='store_true');p.add_argument('--refine-audio')
    a=p.parse_args()
    try:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        data=json.loads(a.input.read_text(encoding='utf-8'))
        if a.refine_audio:refine(data,a.refine_audio,a.output);return 0
        plan=make_plan(data);a.output.with_suffix('.plan.json').write_text(json.dumps(plan,ensure_ascii=False),encoding='utf-8')
        if not a.plan_only:render(plan,a.output)
    except (OSError,ValueError,KeyError,ImportError,subprocess.SubprocessError) as e:print(str(e),file=__import__('sys').stderr);return 1
    except KeyboardInterrupt:return 130
    print('UZANIM Tayyor.',flush=True);return 0
if __name__=='__main__':raise SystemExit(main())
