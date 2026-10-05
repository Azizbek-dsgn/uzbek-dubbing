"""Original UzScribe motion recipes; shared geometry/keyframes for AE and FFmpeg."""
import math
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageFilter

# motion, automatic layout, automatic background, accent
RECIPES = {
    'saas': ('rise', 'line', 'card', '#A6A0FF'),
    'apple': ('float', 'line', 'none', '#FFFFFF'),
    'bounce': ('bounce', 'line', 'word', '#BEF264'),
    'elastic': ('elastic', 'split', 'pill', '#FFC6A8'),
    'typewriter': ('reveal', 'line', 'none', '#A5E5FF'),
    'editorial': ('rise', 'hero', 'underline', '#EBC8A0'),
    'kinetic': ('slam', 'stack', 'none', '#E8FF70'),
    'neon': ('bounce', 'line', 'outline', '#71F5DC'),
    'cinematic': ('float', 'quote', 'none', '#E2D7C7'),
    'sticker': ('elastic', 'split', 'tag', '#FFD670'),
    'marker': ('rise', 'line', 'word', '#FF90B3'),
    'minimal': ('fade', 'line', 'none', '#FFFFFF'),
}
MIGRATION = {'karaoke':'saas','pop':'bounce','pill':'marker','reveal':'typewriter','slide':'apple','emphasis':'editorial'}
LAYOUTS = {'auto','line','hero','stack','split','stair','quote'}
SHAPES = {'auto','none','card','pill','word','underline','outline','tag'}

def number(theme, key, default, low, high):
    value=float(theme.get(key,default))
    if not math.isfinite(value) or not low<=value<=high:raise ValueError('Uslub sozlamasi noto‘g‘ri: '+key)
    theme[key]=value;return value

def prepare(theme, color, font_path, postscript_name):
    theme['preset']=MIGRATION.get(theme.get('preset'),theme.get('preset','saas'))
    if theme['preset'] not in RECIPES:raise ValueError('Animatsiya presetini tekshiring.')
    motion,layout,shape,accent=RECIPES[theme['preset']]
    theme['motion']=motion
    theme['layout']=theme.get('layout','auto');theme['shape']=theme.get('shape','auto')
    if theme['layout'] not in LAYOUTS or theme['shape'] not in SHAPES:raise ValueError('Dizayn yoki fon shaklini tekshiring.')
    if theme['layout']=='auto':theme['layout']=layout
    if theme['shape']=='auto':theme['shape']=shape
    theme['active']=color(theme.get('active',accent));theme['shapeColor']=color(theme.get('shapeColor',accent if theme['shape'] in {'word','underline','outline','tag'} else '#20212A'))
    channels=[int(theme['shapeColor'][i:i+2],16) for i in (1,3,5)]
    theme['highlightText']='#15151B' if sum(v*w for v,w in zip(channels,[.2126,.7152,.0722]))>145 else '#FFFFFF'
    theme['sweepColor']=color(theme.get('sweepColor','#FFFFFF'))
    for k,d,lo,hi in [('shapeOpacity',88,0,100),('radius',24,0,100),('padding',18,0,80),
                       ('textSweepIntensity',55,0,100),('shapeSweepIntensity',35,0,100),
                       ('sweepDuration',.7,.15,3),('sweepWidth',35,5,100),('sweepAngle',-20,-80,80),('stroke',0,0,8)]:number(theme,k,d,lo,hi)
    theme['textSweep']=bool(theme.get('textSweep',False));theme['shapeSweep']=bool(theme.get('shapeSweep',False))
    # Regular + bold installed system fonts; no Apple font redistribution.
    primary=theme['font'];regular=primary.replace('Arial Bold.ttf','Arial.ttf').replace('arialbd.ttf','arial.ttf').replace('DejaVuSans-Bold.ttf','DejaVuSans.ttf')
    theme['accentFont']=font_path(theme.get('accentFont','') or primary)
    theme['bodyFont']=font_path(regular if not theme.get('font') or primary==font_path() else primary)
    if not Path(regular).is_file():theme['bodyFont']=primary
    theme['accentPostscript']=postscript_name(theme['accentFont'],theme['fontPostscript'])
    theme['bodyPostscript']=postscript_name(theme['bodyFont'],theme['fontPostscript'])

@lru_cache(maxsize=256)
def font(path,size):return ImageFont.truetype(path,max(8,int(size)))

def layout(cue,theme,width,height,lexical):
    runs=cue['runs'];style=theme['layout'];base=cue['size']
    marked=[i for i,r in enumerate(runs) if r['emphasis']]
    hero=marked[0] if marked else max(range(len(runs)),key=lambda i:len(lexical(runs[i]['text'])))
    for i,r in enumerate(runs):
        featured=r['emphasis'] or i==hero
        factor=(1.55 if featured else .78) if style=='hero' else (1.2 if i%2==0 else .82) if style in {'stack','stair'} else (1.25 if featured else .86) if style=='split' else 1
        r.update(size=max(8,round(base*factor)),font=theme['accentFont'] if featured and style!='line' else theme['bodyFont'] if style in {'hero','quote','split'} else theme['font'],featured=featured)
        r['fontPostscript']=theme['accentPostscript'] if r['font']==theme['accentFont'] else theme['bodyPostscript'] if r['font']==theme['bodyFont'] else theme['fontPostscript']
    def measure():
        for r in runs:
            f=font(r['font'],r['size']);r['width']=float(f.getlength(r['text']));r['height']=float(f.getbbox(r['text'],anchor='lt')[3]);r['gap']=max(3,float(f.getlength(' ')))
    measure()
    longest=max(r['width'] for r in runs)
    if longest>width*.72:
        for r in runs:r['size']=max(8,int(r['size']*width*.72/longest))
        measure()
    lines=[];line=[];explicit=set();n=0
    for part in cue['text'].splitlines()[:-1]:n+=len(part.split());explicit.add(n)
    for i,r in enumerate(runs):
        break_now=i in explicit or (style=='hero' and (i==hero or i==hero+1)) or (style=='stack' and len(line)>=2) or (style=='stair' and len(line)>=2) or (style=='split' and i==math.ceil(len(runs)/2))
        if line and (break_now or sum(w['width']+w['gap'] for w in line)+r['width']>width*.74):lines.append(line);line=[]
        line.append(r)
    if line:lines.append(line)
    gap=max(4,base*.32);total=sum(max(r['height'] for r in row)+gap for row in lines)-gap
    if total>height*.5:
        factor=height*.5/total
        for r in runs:r['size']=max(8,int(r['size']*factor))
        measure();gap=max(3,base*.32*factor);total=sum(max(r['height'] for r in row)+gap for row in lines)-gap
    if total>height*.58:raise ValueError('Matn ko‘p. Subtitrni bir necha qatorga bo‘ling.')
    bottom=height*(.74 if theme['safe'] and height>width else .87)
    y={'top':height*.15,'center':(height-total)/2,'bottom':bottom-total}[theme['position']]
    y=max(height*.1,min(y,height*.9-total))
    for row_index,row in enumerate(lines):
        row_w=sum(r['width'] for r in row)+sum(r['gap'] for r in row[:-1]);row_h=max(r['height'] for r in row)
        x=width*.14+(row_index%3)*base*.3 if style=='stair' else width*.14 if style=='quote' else (width-row_w)/2
        x=min(x,width*.9-row_w)
        for r in row:r.update(x=round(x,3),y=round(y+row_h-r['height'],3),row=row_index);x+=r['width']+r['gap']
        y+=row_h+gap
    cue['bounds']=[min(r['x'] for r in runs),min(r['y'] for r in runs),max(r['x']+r['width'] for r in runs),max(r['y']+r['height'] for r in runs)]
    cue['wordLayers']=style!='line' or any(r['fontPostscript']!=theme['fontPostscript'] for r in runs)
    for r in runs:
        r.pop('gap',None);r['motion']=motion_keys(cue,r,theme)
    cue['shapes']=shape_specs(cue,theme,height)

def motion_keys(cue,run,t):
    a,b=cue['start'],cue['end'];on=run['start'];speed=min(t['speed'],(b-a)/3);kind=t['motion'];keys=[]
    def add(time,dx=0,dy=0,scale=1,opacity=1,rotation=0):
        keys.append({'time':round(time,6),'dx':dx,'dy':dy,'scale':scale,'opacity':opacity,'rotation':rotation})
    delta=run['size']*.4
    if kind in {'reveal','slam','elastic'}:
        if on>a:add(a,opacity=0)
        add(on,dy=delta if kind!='reveal' else 0,scale=.76 if kind!='reveal' else 1,opacity=0)
        if kind=='reveal':add(min(b,on+speed),opacity=1)
        else:
            d=min(speed,max(.001,b-on));add(on+d*.55,dy=-delta*.1,scale=1.1,rotation=-3 if kind=='elastic' else 0);add(on+d,scale=1)
    elif kind=='bounce':
        add(a);d=min(speed,max(.001,b-on));add(on);add(on+d*.35,dy=-delta*.22,scale=1.14);add(on+d*.72,scale=.97);add(on+d)
    else:
        add(a,dy=delta if kind in {'rise','float'} else 0,scale=.97 if kind=='float' else 1,opacity=0)
        add(a+speed)
    exit_start=max(a+speed,b-speed)
    # Do not overwrite late word entrance or bounce keyframes.
    if exit_start>keys[-1]['time']:add(exit_start)
    add(b,dy=-delta*.15 if kind=='float' else 0,opacity=0)
    unique={k['time']:k for k in keys};return [unique[k] for k in sorted(unique)]

def shape_specs(cue,t,height):
    kind=t['shape'];pad=t['padding']*height/1080;result=[]
    def spec(bounds,target=-1):
        x,y,right,bottom=bounds;w=right-x;h=bottom-y
        if kind=='underline':y=bottom+max(2,pad*.3);h=max(2,cue['size']*.065);x-=pad*.2;w+=pad*.4
        else:x-=pad;y-=pad;w+=pad*2;h+=pad*2
        result.append({'x':x,'y':y,'width':w,'height':h,'radius':min(h/2,t['radius']*height/1080) if kind not in {'underline','tag'} else 0,'outline':kind=='outline','target':target,'color':t['shapeColor'],'opacity':t['shapeOpacity']/100})
    if kind in {'word','underline'}:
        for i,r in enumerate(cue['runs']):spec([r['x'],r['y'],r['x']+r['width'],r['y']+r['height']],i)
    elif kind!='none':spec(cue['bounds'])
    if kind=='pill':
        for s in result:s['radius']=s['height']/2
    return result

def state(keys,time):
    if time<=keys[0]['time']:return keys[0]
    for left,right in zip(keys,keys[1:]):
        if time<=right['time']:
            p=(time-left['time'])/max(1e-9,right['time']-left['time'])
            return {k:left[k]+(right[k]-left[k])*p for k in ['dx','dy','scale','opacity','rotation']}
    return keys[-1]

def sweep(image,time,cue,t,intensity):
    if intensity<=0:return image
    bbox=image.getbbox()
    if not bbox:return image
    # Only the alpha mask is lit; nothing spills onto the original footage.
    import numpy as np
    x,y,right,bottom=bbox;patch=image.crop(bbox);pixels=np.array(patch,dtype=np.float32)
    duration=min(t['sweepDuration'],cue['end']-cue['start']);progress=(time-cue['start'])/duration
    if not 0<=progress<=1:return image
    beam=max(2,(right-x)*t['sweepWidth']/100);center=-beam+(right-x+beam*2)*progress
    yy,xx=np.ogrid[:bottom-y,:right-x]
    strength=np.maximum(0,1-np.abs(xx+(yy-(bottom-y)/2)*math.tan(math.radians(t['sweepAngle']))-center)/beam)**2*intensity/100
    rgb=[int(t['sweepColor'][i:i+2],16) for i in (1,3,5)]
    for c in range(3):pixels[:,:,c]+=(rgb[c]-pixels[:,:,c])*strength
    image.paste(Image.fromarray(pixels.astype('uint8'),'RGBA'),(x,y));return image

def frame(plan,time):
    image=Image.new('RGBA',(plan['width'],plan['height']))
    cue=next((c for c in plan['cues'] if c['start']<=time<c['end']),None)
    if not cue:return image
    t=plan['theme'];shapes=Image.new('RGBA',image.size);draw=ImageDraw.Draw(shapes)
    fade=min(1,max(0,(time-cue['start'])/t['speed']),max(0,(cue['end']-time)/t['speed']))
    for s in cue['shapes']:
        if s['target']>=0:
            r=cue['runs'][s['target']]
            if not r['start']<=time<r['end']:continue
        box=(s['x'],s['y'],s['x']+s['width'],s['y']+s['height']);fill=s['color']+f"{round(s['opacity']*255*fade):02x}"
        draw.rounded_rectangle(box,radius=s['radius'],fill=None if s['outline'] else fill,outline=fill if s['outline'] else None,width=max(1,round(cue['size']/25)))
    if t['shapeSweep']:shapes=sweep(shapes,time,cue,t,t['shapeSweepIntensity'])
    image.alpha_composite(shapes)
    text=Image.new('RGBA',image.size)
    for r in cue['runs']:
        m=state(r['motion'],time);f=font(r['font'],r['size']);stroke=round(t['stroke']*plan['height']/1080)
        pad=max(3,stroke+2);glyph=Image.new('RGBA',(math.ceil(r['width'])+pad*2,math.ceil(r['height'])+pad*2))
        active=r['start']<=time<r['end'];fill=t['active'] if (active and t['preset'] in {'bounce','neon','saas','elastic'}) or r['emphasis'] or (r['featured'] and t['layout'] in {'hero','split','stack'}) else t['color']
        if t['shape']=='tag' or (t['shape']=='word' and active):fill=t['highlightText']
        ImageDraw.Draw(glyph).text((pad,pad),r['text'],font=f,fill=fill,anchor='lt',stroke_width=stroke,stroke_fill='#000000')
        if m['scale']!=1:glyph=glyph.resize((max(1,round(glyph.width*m['scale'])),max(1,round(glyph.height*m['scale']))),Image.Resampling.BICUBIC)
        if m['rotation']:glyph=glyph.rotate(m['rotation'],resample=Image.Resampling.BICUBIC,expand=True)
        glyph.putalpha(glyph.getchannel('A').point(lambda a:round(a*min(1,max(0,m['opacity'])))))
        px=round(r['x']+r['width']/2+m['dx']-glyph.width/2);py=round(r['y']+r['height']/2+m['dy']-glyph.height/2)
        text.alpha_composite(glyph,(px,py))
    if t['textSweep']:text=sweep(text,time,cue,t,t['textSweepIntensity'])
    if t['preset']=='neon':
        glow=text.filter(ImageFilter.GaussianBlur(max(1,cue['size']*.09)));glow.putalpha(glow.getchannel('A').point(lambda a:a//3));image.alpha_composite(glow)
    image.alpha_composite(text);return image
