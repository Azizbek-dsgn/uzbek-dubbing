"""Install the feature models used by the public panel, without account tokens."""
from __future__ import annotations
import hashlib
import os
os.environ['ORT_DISABLE_TELEMETRY']='1'
from pathlib import Path
import shutil
import ssl
import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from subtitles.install_storage import (GIB, RESERVE, SPACE_EXIT, InsufficientSpace,
    require_space, navai_download_dir, navai_download_budget, is_disk_full, disk_full_message)
import tempfile
import urllib.request

SEGMENTATION_REVISION = '9403a6902bb58e3d5ae8c7e77c3422de279db2e0'
NAVAI_REVISION = '9c67dea55c8ac11f237d60ca0c32e5dc5a8c3de5'
RUBAI_REVISION = '4a9b7f6dfdf0b2b251135dd7d6d5d3d817f6590e'
SPEAKER_ASSETS = {
    'segmentation.onnx': ('https://huggingface.co/csukuangfj/sherpa-onnx-pyannote-segmentation-3-0/resolve/'+SEGMENTATION_REVISION+'/model.onnx', '220ad67ca923bef2fa91f2390c786097bf305bceb5e261d4af67b38e938e1079'),
    'SEGMENTATION-LICENSE.txt': ('https://huggingface.co/csukuangfj/sherpa-onnx-pyannote-segmentation-3-0/resolve/'+SEGMENTATION_REVISION+'/LICENSE', '14d7016ad68e7394d6e6b78d96cc2ae431c905287b89674cfdf021e79e62b8ba'),
    'embedding.onnx': ('https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx', '1a331345f04805badbb495c775a6ddffcdd1a732567d5ec8b3d5749e3c7a5e4b'),
    'EMBEDDING-LICENSE.txt': ('https://raw.githubusercontent.com/modelscope/3D-Speaker/065629c313eaf1a01c65c640c46d77e61e9607b4/LICENSE', 'c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4'),
}

def checksum(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def fetch(url, destination, expected):
    if destination.is_file() and checksum(destination) == expected:
        return
    import certifi
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix+'.part')
    try:
        with urllib.request.urlopen(url, timeout=90, context=ssl.create_default_context(cafile=certifi.where())) as source, temporary.open('wb') as target:
            shutil.copyfileobj(source, target, 1024*1024)
        if checksum(temporary) != expected:
            raise RuntimeError('Model tekshiruvdan o‘tmadi: '+destination.name)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def whisper_ready(directory):
    return (all((directory/name).is_file() for name in ('config.json','tokenizer.json','preprocessor_config.json','model.bin'))
            and (directory/'model.bin').stat().st_size >= 100_000_000)


def install_features(runtime):
    os.environ.setdefault('HF_HUB_DISABLE_XET','1')
    os.environ.setdefault('HF_HUB_VERBOSITY','error')
    os.environ['HF_MODULES_CACHE']=str(runtime/'models'/'.hf-modules')
    from huggingface_hub import snapshot_download
    models = runtime/'models'
    if not whisper_ready(models/'navai-medium'):
        require_space(runtime, navai_download_budget(runtime)+RESERVE, 'Scribe Nav tayyorlash')
    speaker = models/'speaker-onnx'
    print('So‘zlovchilar modeli tekshirilmoqda/yuklanmoqda…', flush=True)
    for name,(url,digest) in SPEAKER_ASSETS.items():
        fetch(url,speaker/name,digest)
    navai = models/'navai-medium'
    if not whisper_ready(navai):
        print('Scribe Nav modeli yuklanmoqda va tayyorlanmoqda…', flush=True)
        from transformers import AutoTokenizer
        from ctranslate2.converters import TransformersConverter
        with tempfile.TemporaryDirectory(prefix='uzscribe-navai-', dir=runtime) as temporary:
            source=navai_download_dir(runtime);converted=Path(temporary)/'converted'
            if source.is_symlink():
                raise RuntimeError('Nav yuklash papkasi symlink bo‘lishi mumkin emas.')
            source.mkdir(parents=True, exist_ok=True)
            snapshot_download('navai-uz/whisper-medium-uzbek',revision=NAVAI_REVISION,local_dir=source,token=False,
                              allow_patterns=['*.json','*.txt','*.safetensors','LICENSE','NOTICE','README.md'])
            require_space(runtime, int(1.2*GIB)+RESERVE, 'Scribe Nav konvertatsiyasi')
            AutoTokenizer.from_pretrained(str(source),local_files_only=True,use_fast=True).save_pretrained(source)
            TransformersConverter(str(source),copy_files=['tokenizer.json','preprocessor_config.json']).convert(str(converted),quantization='int8')
            if not whisper_ready(converted):
                raise RuntimeError('Scribe Nav konvertatsiyasi to‘liq tugamadi.')
            for name in ('LICENSE','NOTICE','README.md'):
                if (source/name).is_file():shutil.copy2(source/name,converted/name)
            # Rename on the same volume: no second model.bin copy at peak usage.
            if navai.is_symlink():
                raise RuntimeError('Nav model papkasi symlink bo‘lishi mumkin emas.')
            backup=Path(temporary)/'previous'
            if navai.exists():navai.replace(backup)
            try:
                converted.replace(navai)
            except OSError:
                if backup.exists():backup.replace(navai)
                raise
        # Delete only our raw conversion cache, after a validated model is installed.
        shutil.rmtree(source)
    # Retain upstream attributions even when reusing an already converted model.
    snapshot_download('navai-uz/whisper-medium-uzbek',revision=NAVAI_REVISION,local_dir=navai,token=False,
                      allow_patterns=['LICENSE','NOTICE','README.md'])
    print('O‘zbekcha matn va tinish belgisi modeli tekshirilmoqda/yuklanmoqda…', flush=True)
    corrector=models/'rubai-transcript/model.safetensors'
    if not corrector.is_file() or corrector.stat().st_size < 100_000_000:
        require_space(runtime, int(1.6*GIB)+RESERVE, 'Matn modeli yuklash')
    snapshot_download('islomov/rubai-corrector-transcript-uz',revision=RUBAI_REVISION,
                      local_dir=models/'rubai-transcript',token=False,allow_patterns=['*.json','model.safetensors','README.md'])
    require_features(runtime)


def require_features(runtime):
    models=runtime/'models'
    if not whisper_ready(models/'navai-medium'):
        raise RuntimeError('Scribe Nav modeli to‘liq o‘rnatilmagan.')
    corrector=models/'rubai-transcript'
    if not all((corrector/name).is_file() for name in ('model.safetensors','config.json','tokenizer_config.json')):
        raise RuntimeError('Matnni tartiblash modeli to‘liq o‘rnatilmagan.')
    if (corrector/'model.safetensors').stat().st_size < 100_000_000:
        raise RuntimeError('Matn modeli yuklanishi tugamagan.')
    for name,(_,digest) in SPEAKER_ASSETS.items():
        file=models/'speaker-onnx'/name
        if not file.is_file() or checksum(file)!=digest:
            raise RuntimeError('So‘zlovchilar modeli to‘liq o‘rnatilmagan: '+name)


if __name__=='__main__':
    try:
        install_features(Path(sys.argv[1]))
    except Exception as error:
        if not is_disk_full(error):raise
        print(str(error) if isinstance(error, InsufficientSpace) else disk_full_message(), file=sys.stderr, flush=True)
        raise SystemExit(SPACE_EXIT)
