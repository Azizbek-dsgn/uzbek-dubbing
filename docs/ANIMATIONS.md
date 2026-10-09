# UzScribe 0.8.0 · Caption design studio

## Panel

The six earlier public presets have been replaced with twelve original recipes:

| Recipe | Default design | Motion |
| --- | --- | --- |
| SaaS | Rounded dark card, subtle accent | Rise + fade |
| Apple | Clean typography | Gentle scale and float |
| Bounce | Active word background | Timed bounce |
| Elastic | Two levels in a capsule | Overshoot + settle |
| Typewriter | Clean line | Timed word entrance |
| Editorial | One large featured word | Rise |
| Kinetic | Alternating large/small blocks | Word slam |
| Neon | Glowing text, border | Bounce |
| Cinematic | Left aligned quote | Slow float |
| Sticker | Two sizes on a tag | Tilt + elastic |
| Marker | Active word background | Rise |
| Minimal | Clean line | Fade |

Apple and SaaS are visual style labels, not official third-party products. Existing locally saved styles migrate to the nearest new recipe. Compatibility readers for old native plans remain internal; the old presets are no longer selectable.

Choose **Animatsiya**, then optionally expand **Uslub va joylashuv**. Layout can be overridden with line, featured word, alternating blocks, two levels, staircase or quote. Featured words come from the comma-separated emphasis list; absent a selection, a long word is used as a typographic accent. This is deterministic visual emphasis, not semantic understanding. Caption text/order and actual ASR timings stay unchanged. Fonts are measured locally, long words shrink to fit, and explicit line breaks are respected.

Base font and accent font are independently selectable from installed TTF/OTF fonts. Regular/bold system Arial is the portable fallback. No Apple font files are redistributed. Customer fonts must exist on the target machine. Position, size, safe portrait placement, motion duration and stroke are adjustable.

**Fon shakli va yorug‘lik** combines background and effects into one collapsed group: card, capsule, active-word shape, underline, outline or tag; background color, opacity, corner radius and padding; independent text/shape light sweep toggles and intensities; shared sweep color, width, angle and duration. Text automatically contrasts with active-word/tag backgrounds. No shape means the shape sweep has no target. Every recipe can use any of these shapes and both sweeps.

The looping panel sample is approximate and labeled accordingly. In review, **Animatsiyani ko‘rish** generates the actual caption APNG with the same planner/font/layout engine used for Premiere MOV export, preserving aspect ratio (maximum 400×320, up to 12fps, first six seconds). Any theme/edit change invalidates that image. Preview shows caption graphics without source video/audio.

## Adobe output

**After Effects:** native editable text, shape, text animator and transform keyframes. Simple uniform lines retain one text layer per cue when that mode is selected; designed layouts and mixed fonts require editable word layers automatically, announced in the panel. Word layers retain the whole cue's in/out window and their planned positions. Both manual layer modes remain. Text and shape get independent native **CC Light Sweep** effects. Neon uses native Glow. If a requested built-in effect is unavailable, import reports it and removes the attempted layers. Reinstall Adobe's bundled effects or disable the effect; nothing is silently skipped. A single Undo group covers each import. Animation Composer remains a separate handoff requiring its own installation.

**Premiere:** Python/Pillow/FFmpeg generates a transparent qtrle/argb QuickTime overlay on an empty video track. Original footage is not rendered/replaced. Caption motion and alpha-clipped text/shape sweeps are baked into the overlay; they are not editable Premiere effects. Native Cycore and software sweep/glow kernels differ visually. Change the panel style and regenerate to edit; SRT is retained. Long/high-resolution exports consume time and disk space.

**MOGRT:** saved AE projects can export editable Source Text controls per word, one template per cue, plus a relative-path manifest. Copy the complete template folder to Premiere and import onto an empty track. Original timing/geometry is retained; changing word count or word length needs regeneration. Export needs AE's scripting file-write permission; the plugin does not change that preference automatically.

Imports roll back created layers on error. Python rendering can be cancelled without losing reviewed text. Native imports are synchronous and finish before the panel responds.

## Research and verification

Reviewed primary GitHub projects: [remotion-captions-kit](https://github.com/Fats403/remotion-captions-kit) for kinetic/editorial and word timing patterns, [pycaps](https://github.com/francozanardi/pycaps) for template separation and independently styled caption elements, and [auto-caption](https://github.com/sebetancurch/auto-caption) for word-focused caption workflows. Their code/runtimes are not bundled; UzScribe's geometry, motion, masks, renderer and Adobe adapter are original. This avoids a Chromium/Remotion installation requirement.

Native API references: [text animator match names](https://ae-scripting.docsforadobe.dev/matchnames/layer/textlayer/), [Adobe Cycore effects](https://helpx.adobe.com/ca/after-effects/desktop/apply-effects-and-animation-presets/list-of-effects/cycore-plugins.html), [Cycore Light Sweep controls](https://www.cycorefx.com/downloads/cfx_hd_std/CycoreFX%20HD%201.8.9%20Manual.pdf).

Verified on current Mac: all twelve recipes make transparent MOVs and animated PNGs; layout/text/time integrity, independent sweep masks, input validation, migration and panel host dispatch tests pass. AE 2026 scratch-comp tests exercised all 12 × 2 layer modes with separate text and shape sweeps. Native range-selector amounts are normalized to AE's -100..100 bounds, and indexed property references are reacquired before edits. Scratch comps were removed and the prior comp restored. Windows dispatch is simulated; native Windows and every Adobe 2020+ release have not been exercised.

## Review tools


- ↶ / ↷ provide 40 steps of Undo/Redo, including text, word timing and speaker metadata.
- The last valid review is saved locally in `exports/review-draft.json`. After reopening the panel, **Oxirgi tahrirni davom ettirish** restores it only on the same sequence/composition, dimensions and frame rate. The temporary audio may have been removed by the OS; caption editing still works, while recognition then needs a fresh export. Finishing/importing or saving SRT clears the draft.

- **Keyingisi bilan birlashtirish** merges the current and next captions.
- Put the text cursor before a word, then **Kursordan bo‘lish**. The split uses that word's existing start time. Overlapping/mismatched words require correction first.
- **So‘z vaqtlari va urg‘u** allows editing each word's text, start and end in seconds. Save applies these words to the selected caption. ★ adds that word to the emphasis list.
- **Whisper bilan vaqtni tekshirish** re-recognizes the exported audio with the installed Global model and updates matching words only. It requires at least 80% agreement, keeps the original text, and rejects conflicting timings. This is a second recognition pass, not forced alignment; Giga/Nav model accuracy is unchanged.
- Actual ASR fragments such as `Wi` + `-Fi` are joined only when they match the caption tokenization, using their original timing envelope. Explicit separate-fragment captions remain separate. Word animations reject text/timing mismatches instead of silently inventing evenly spaced timestamps. Punctuation changes are allowed. Apple, Minimal, Cinematic and SaaS can use cue timing when word metadata does not match.

## Verification limits

Automated checks cover real transparent MOV generation/decoding for every preset, timing/text validation, safe placement, saved styles, split/merge, failure and cancellation, empty-track protection, and mocked Adobe scripting dispatch. They do not prove live AE/Premiere rendering or MOGRT import on every Adobe release. Live Adobe output remains a release gate; no universal error-free guarantee is made.

## After Effects · 0.6.2

Har bir subtitr bloki (cue) faol kompozitsiyada bitta tahrirlanadigan text layer bo‘ladi. Ikki vizual qatorli cue ham bitta layerda saqlanadi. `UzScribe 001 · matn` nomi, startTime/inPoint/outPoint va Work Area offset bilan timeline’da joylashtiriladi. Karaoke/pop/reveal/emphasis text animator va range selector orqali so‘zlarni shu layer ichida boshqaradi; slide butun cue’ni animatsiyalaydi. Pill presetida har cue uchun bitta text layer va unga parent qilingan bitta highlight shape yordamchi layer bor. Animation Composer oddiy cue layerlarini tanlab beradi. MOGRT eksportining ichki so‘z layerlari alohida eksport kompozitsiyasida qoladi.

UzCaption rasmiy [plugin sahifasi](https://caption.uz/plugin) AE qo‘llovini ko‘rsatadi; ochiq sahifada AE ichki layer tuzilishi yoki manba kodi berilmagan. Ushbu o‘zgarish foydalanuvchi so‘ragan cue-per-layer ish jarayoni va Adobe text animator API asosida yozildi.

Mahalliy Node host testlari layer soni, butun matn, range indekslari (paragraph break hisoblanmaydi), offset, yordamchi shape, Composer va xatoda rollbackni tekshiradi. Ushbu o‘zgarishning haqiqiy Adobe host sinovi hali tasdiqlanmagan.

## After Effects: selected video (0.6.3)

Select exactly one video layer with audio in the composition timeline. Automatic/full range uses that layer’s visible in/out range; Work Area mode uses its intersection with the selected layer. Only the selected layer’s audio is rendered from a disposable composition copy. The original audio, solo, lock and guide settings are preserved; native rendering keeps stretch, time remapping and audio effects. Captions appear in the original composition at the corresponding timeline times, with one editable text layer per cue.

## After Effects: layer mode (0.6.4)

“Timeline’ga qo‘shish” offers a whole subtitle text layer (default) or separate editable word layers. Word layers keep the subtitle group’s shared in/out range and measured row positions, including explicit line breaks. This preserves your 3–4 word row settings. Animation and word timing remain independent of subtitle segmentation. Word Reveal uses opacity within the shared range. Plain subtitles and Animation Composer support both modes; Composer selects the imported text layers.

## Matn tools (0.6.5)

In After Effects, open Matn, select one static text layer, and choose “So‘zlarni alohida layer qilish”. A ten-word layer produces ten separately selectable text layers. Native copies retain paragraph wrapping, character styles, transforms, parenting and timing; character opacity selectors isolate each word without text reflow. Each copy deliberately retains the full Source Text so positions stay unchanged. Editing that full text can affect the saved ranges: edit your original and split again after changing wording. The original is disabled only after all copies succeed, remains available, and the entire operation is one Undo group. Source Text expressions/keyframes and track mattes are rejected with an actionable message; partial copies are removed on failure. Adobe rendering has not been verified by the automated mocks.

## Panel design (0.6.6)

The panel shares a monochrome design across Adobe hosts. Premiere shows Subtitr/Podcast/Reels; After Effects shows Subtitr/Matn. Range/audio controls are paired, the speech model is collapsed with the current model shown in its summary, and technical options remain in expandable sections. Account/subscription controls live in the header menu, dismiss on outside click/Escape, and do not consume the main workflow. Primary actions stay visible in the footer. Keyboard arrow/Home/End navigation follows only visible, enabled tabs. Compact styles cover narrow/short panels; reduced motion is respected. Native UI loading/navigation was checked in After Effects 2026 and Premiere Pro 2026 without running media edits or changing project content.
