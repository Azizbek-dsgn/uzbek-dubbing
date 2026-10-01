# Reels cleanup research — 2026-10-02

## Primary sources reviewed

- [declip](https://github.com/b2bvic/declip) (MIT): local Whisper on Apple Silicon, sentence similarity in a sliding window, keeps latest retake, configurable dead air, dry run and cached transcript. Its Mac-only stack was not reused for our cross-platform plugin.
- [OpenCut for Premiere](https://github.com/SysAdminDoc/OpenCut): local ASR, repeated-take proposals, transcript timing, staged silence/filler cuts and editable timeline operations. Features described by the repository are not proof of Uzbek accuracy.
- [Tribe Video Cleaner](https://github.com/grafup/Tribe-Video-Cleaner): transcript review and silence/double-take cleanup, using cloud transcription providers. It was a workflow reference, not a dependency.
- [Auto-Editor](https://github.com/WyattBlue/auto-editor): audio activity and editable XML export.

No code from these projects is copied or bundled. UzScribe reuses its own Premiere FCP7 XML bridge and the already installed Uzbek models.

## Implemented workflow

Reels → select speech audio track → Reels’ni tozalash. Local VAD identifies silence separately from ASR. Original source channels/offsets and timeline gaps are streamed into a 16 kHz WAV, then GigaAM Uzbek (default) or the chosen local strong model provides word timing. Whisper's repeat suppression is disabled only for Reels. Sentence/pause boundaries define takes. Neighboring exact repeats and unfinished prefixes are grouped; default keeps the longest complete take, latest on ties. Optional balanced detection allows only minor discourse-filler differences, never arbitrary semantic paraphrases. Numbers/negations and low-confidence text prevent a match. Speech with no recognized text is not deleted as silence.

Cuts are on the sequence frame grid and ripple all audio/video tracks. In/Out preserves the exterior. New XML imports as a separate sequence by default, so one button completes cleanup. Preview-first can be selected. Every removed take can be restored by checkbox and rebuilt using cached ASR. Cache key includes media path/size/mtime, source trims/channels, FPS, analysis range, model ID and local weights' metadata. Cancellation stops before import; errors retain XML/review for retry.

## Verified and limits

Unit cases cover six repeats, interrupted prefixes, complete earlier take versus later fragment, intentional short emphasis, changed words/numbers/negation, confidence, distant repeats, In/Out, overlapping removal ranges and frame synchronization. Panel mocks cover automatic import, failed import retry, restoring a take, preview-first, cancellation, AE restriction and sequence identity. Real integration uses a credited FLEURS Uzbek sample repeated six times, actual GigaAM/VAD/FFmpeg, cached restoration and WAV offset/gap assembly. The initial Windows/local test removed five retakes; Apple Silicon removed three because ASR spelled Wi-Fi differently in the first/last takes. The conservative matcher preserves those unmatched takes. This small sample is not a benchmark of general editing accuracy.

Currently Premiere Pro only. Synchronize audio/video first; flatten nested/multicam; edit before transitions/effects/captions. Source audio is analyzed before mixer effects. Format conversion is center crop, not face tracking. Intentional repetitions can be indistinguishable from retakes; review decisions. No promise of error-free behavior across all voices, recordings or Adobe versions. Live Adobe import remains an outstanding release gate.

## Premiere XML regression fix — 2026-10-02

Premiere-generated Adjustment Layer/Black Video files use `mediaSource=Slug`, not a disk `pathurl`. These definitions and ID references are now resolved as generated video sources. Reels also resolves -1 clip boundaries from adjacent transitions according to [Apple FCP XML timing](https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/FinalCutPro_XML/Elements/Elements.html). Complete transitions are shifted with retained spans; transitions intersected by removed spans are dropped with a panel notice. Podcast retains its strict transition gate. The reported real XML (five video/eight audio tracks) now parses and round-trips ten fades locally. No private XML/media is committed or packaged. Premiere's export report still applies: unsupported adjustment/graphic/custom effects cannot be recovered from XML; inspect the new sequence and keep the original. Native Adobe import is still unverified.

## Audio channel regression — 2026-10-02

Premiere may encode stereo as two `media/audio` components, each with `channelcount=1` and `audiochannel/sourcechannel=1` or `2`. Reading only the first component falsely rejected Audio 2. Shared Podcast/Reels decoding now uses declared source channels and actual PyAV stream/channel metadata, supporting stereo and multiple audio streams. Silent selected inputs may switch only to a paired channel of the identical synchronized source clips; Podcast does this only with a single microphone mapping. Unrelated music and other microphone tracks are never substituted. Silent/no-speech ranges remain protected from cuts. Actual reported MOV: left channel had no detected speech, right channel had 79 voiced windows in an eight-second local VAD check. Test fixtures exercise split mono XML, real stereo WAV/FFmpeg, invalid channels and unrelated-track protection. Private media is not committed.
