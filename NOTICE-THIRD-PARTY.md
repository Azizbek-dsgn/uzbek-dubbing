# Third-party notices

UzScribe uses display names for upstream models; the models are not trained or owned by Meyor Vision.

- **UzScribe Global** is [Whisper large-v3](https://huggingface.co/Systran/faster-whisper-large-v3), a CTranslate2 conversion of OpenAI Whisper. OpenAI releases Whisper code and weights under MIT. See bundled `WHISPER-LICENSE.txt`. The installer pins revision `edaa852ec7e145841d8ffdb056a99866b5f0a478`.
- **UzScribe Uzbek** is [GigaAM Uzbek 600M](https://huggingface.co/rustam1221/uzbek-asr-gigaam), downloaded by the installer with a pinned revision and checkpoint checksum. Its model card lists Apache-2.0; the base architecture is [ai-sage/GigaAM-Multilingual](https://huggingface.co/ai-sage/GigaAM-Multilingual). The installer downloads these models; the buyer ZIP does not redistribute them. Review upstream training-data provenance before selling a release.
- **UzScribe Uzbek Studio**, when already installed, is [NavAI Whisper medium Uzbek](https://huggingface.co/navai-uz/whisper-medium-uzbek), Apache-2.0. Retain its LICENSE, NOTICE and model-card corpus attributions if redistributing it. The default installer does not download it.

Python dependencies are obtained through pip/uv; their license texts are in installed package metadata. Faster-whisper includes a Silero VAD speech detector. Adobe Premiere Pro, After Effects and Animation Composer are separate products and are not included. Adobe WAV presets are read from the customer's Adobe installation and are not redistributed.

The podcast editor was implemented independently. AutoPod's documented workflow, Podcut (MIT) and Auto-Editor (Unlicense) were research references; their code is not bundled or copied. See `docs/PODCAST-RESEARCH.md`.
