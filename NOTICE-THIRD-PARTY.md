# Third-party notices

UzScribe uses display names for upstream models; the models are not trained or owned by Meyor Vision.

- **UzScribe Global** is [Whisper large-v3](https://huggingface.co/Systran/faster-whisper-large-v3), a CTranslate2 conversion of OpenAI Whisper. OpenAI releases Whisper code and weights under MIT. See bundled `WHISPER-LICENSE.txt`. The installer pins revision `edaa852ec7e145841d8ffdb056a99866b5f0a478`.
- **UzScribe Uzbek** is [GigaAM Uzbek 600M](https://huggingface.co/rustam1221/uzbek-asr-gigaam), downloaded by the installer with a pinned revision and checkpoint checksum. Its model card lists MIT; the base architecture is [ai-sage/GigaAM-Multilingual](https://huggingface.co/ai-sage/GigaAM-Multilingual). The installer downloads these models; the buyer ZIP does not redistribute them. Review upstream training-data provenance before selling a release.
- **UzScribe Uzbek Studio**, when already installed, is [NavAI Whisper medium Uzbek](https://huggingface.co/navai-uz/whisper-medium-uzbek), Apache-2.0. Retain its LICENSE, NOTICE and model-card corpus attributions if redistributing it. The installer now downloads and converts it locally, retaining LICENSE, NOTICE and the model card.

Python dependencies are obtained through pip/uv; their license texts are in installed package metadata. Faster-whisper includes a Silero VAD speech detector. Adobe Premiere Pro, After Effects and Animation Composer are separate products and are not included. Adobe WAV presets are read from the customer's Adobe installation and are not redistributed.

The podcast editor was implemented independently. AutoPod's documented workflow, Podcut (MIT) and Auto-Editor (Unlicense) were research references; their code is not bundled or copied. See `docs/PODCAST-RESEARCH.md` and `docs/REELS-RESEARCH.md`. Reels references also include declip (MIT), OpenCut and Tribe Video Cleaner; their code is not copied or bundled.

Caption animations are independently implemented with Pillow and imageio-ffmpeg; no Remotion runtime or external preset source is bundled. Research and output limitations: `docs/ANIMATIONS.md`.

- **Speaker ONNX** uses sherpa-onnx 1.13.8 (Apache-2.0), publicly distributed
  pyannote segmentation-3.0 ONNX (MIT; its LICENSE is downloaded alongside the
  model), and the 3D-Speaker ERes2Net embedding model (Apache-2.0). Source model
  URLs/revisions and SHA-256 are pinned in `subtitles/model_assets.py`. Upstream:
  https://github.com/k2-fsa/sherpa-onnx and https://github.com/modelscope/3D-Speaker.
  No upstream example implementation is copied; the Python API is used locally.
- **Rubai transcript corrector** is downloaded locally from
  https://huggingface.co/islomov/rubai-corrector-transcript-uz at pinned revision
  4a9b7f6dfdf0b2b251135dd7d6d5d3d817f6590e. Authors: Sardor Islomov and Davron
  Ibrokhimov; derived from ByT5. Its model card currently does not declare a
  license. No Rubai weights are redistributed in the buyer ZIP; commercial
  redistribution rights are not asserted. Preserve the downloaded model card.
