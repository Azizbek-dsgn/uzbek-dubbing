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

## Native shutdown recovery fix (0.6.7)

A macOS crash report identified ONNX Runtime 1.30’s PosixTelemetry shutdown thread aborting after Reels XML/JSON output had already been written. All local Python processing entry points now set ORT_DISABLE_TELEMETRY=1 before native runtime initialization; the Reels panel also sets it before spawning Python. The panel saves complete stderr and exit code/signal to a per-run .log file and reports a process signal or explicit processing error instead of treating a PyTorch warning as the cause. The affected exported timeline/settings were rerun offline with the installed runtime, native VAD and cached transcript: output was created and Python exited 0. This check does not verify a Premiere XML import or a fresh GigaAM transcription.


## 2026-10-06 · 0.6.8: conservative neural cleanup

Reviewed upstream Silero VAD, WhisperX, TEN VAD and OpenCut. Silero VAD v6
is already bundled by faster-whisper; reuse its local ONNX model rather than
adding another platform-specific runtime. The TEN VAD license has additional
Agora/non-compete restrictions, so it is not bundled. WhisperX forced alignment
requires a suitable language alignment model; Uzbek support has not been
validated and is not claimed. No code/weights from OpenCut or TEN were copied.

Primary sources:
- https://github.com/snakers4/silero-vad
- https://github.com/m-bain/whisperX
- https://github.com/SysAdminDoc/OpenCut
- https://github.com/TEN-framework/ten-vad/blob/main/LICENSE

Implementation:
- Reels uses Silero speech activity independently of RMS threshold. Podcast
  microphone loudness comparison retains its existing behavior.
- Short-pause VAD settings: threshold 0.35, silence 120 ms, speech padding 120 ms.
  500 ms past/future context across decode blocks; bounded gain up to 8x for
  quiet speech detection only (source media/audio is not changed).
- Primary ASR word spans protect silence boundaries with the user's padding.
- Retake matching searches the configured time window, including interrupted
  attempts. Numbers, negation, meaningful word differences remain protected.
- Proposed deletions need independent ASR agreement: Giga uses local NavAI
  when available, otherwise Whisper large-v3. NavAI/Whisper uses Uzbek Giga
  when available; NavAI can fall back to Whisper, Whisper to NavAI. Only candidate-containing runs invoke
  the second model; transcripts are cached using source/weight identities.
- Both models must support the repeated phrase and agree with the primary text.
  Uzbek Cyrillic and Latin are normalized for comparison; long takes with
  up to two minor spelling differences may be nominated, but require strict
  independent confirmation. Missing model, failure, disagreement or empty text preserves the proposed take
  and reports the reason. Review can additionally preserve any confirmed take.

This reuses existing pretrained models, not a newly trained Uzbek model. Model
agreement can still share errors; editorial quality needs real human review.
The first independent verification can take longer on CPU. All processing is
local; no extra paid API or new dependency is required.

Verification on the installed Intel Mac runtime:
- 15 Reels unit/regression tests and 11 Podcast tests passed, including quiet
  speech versus camera RMS, decode block context, model disagreement/failure,
  missing verifier, Uzbek negation, Cyrillic/Latin and In/Out preservation.
- Existing 160-second user export ran offline with native VAD and cached Uzbek
  words, exited 0; removed 8.61 seconds versus the earlier 31.42 seconds. This
  demonstrates changed cut boundaries, not a measured human editing score.
- A private repeated-audio fixture exercised fresh GigaAM, NavAI and Whisper
  inference. The engines disagreed and the candidate was retained. No promise
  of perfect repeat removal: this favors retaining a doubtful take over losing
  speech. These private media/transcripts are not packaged or committed.
- No live Premiere import or Windows native inference test was performed for
  this version. Existing XML/frame and panel tests continue to pass.
