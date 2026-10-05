# UzScribe 0.5.1: captions and animation

## Panel

Choose one of six presets: **Karaoke**, **Soft Pop**, **Moving Highlight**, **Word Reveal**, **Slide + Fade**, **Keyword Emphasis**. The panel shows a looping sample. In review, **Tanlangan subtitr animatsiyasini ko‘rish** renders the selected caption with the same planner/font/layout engine used for MOV export. The transparent animated PNG preview preserves aspect ratio, downsizes to at most 400×320, runs at up to 12 fps and loops the first six seconds. It previews caption graphics, without source footage or audio. Theme/caption changes hide the previous rendered preview until regenerated. Exact full-resolution output is computed from the active sequence/composition dimensions.

Under **Uslub va joylashuv**, choose a locally installed TTF/OTF font, reference font size at 1080p, text/highlight colors, position, animation duration and Reels safe placement. Portrait safe mode keeps lower captions above the bottom 23% and uses 80% of frame width; inspect the final video for your platform's current UI. Save named styles locally; styles and models retain their upstream identity.

Review tools:

- ↶ / ↷ provide 40 steps of Undo/Redo, including text, word timing and speaker metadata.
- The last valid review is saved locally in `exports/review-draft.json`. After reopening the panel, **Oxirgi tahrirni davom ettirish** restores it only on the same sequence/composition, dimensions and frame rate. The temporary audio may have been removed by the OS; caption editing still works, while recognition then needs a fresh export. Finishing/importing or saving SRT clears the draft.

- **Keyingisi bilan birlashtirish** merges the current and next captions.
- Put the text cursor before a word, then **Kursordan bo‘lish**. The split uses that word's existing start time. Overlapping/mismatched words require correction first.
- **So‘z vaqtlari va urg‘u** allows editing each word's text, start and end in seconds. Save applies these words to the selected caption. ★ adds that word to the emphasis list.
- **Whisper bilan vaqtni tekshirish** re-recognizes the exported audio with the installed Global model and updates matching words only. It requires at least 80% agreement, keeps the original text, and rejects conflicting timings. This is a second recognition pass, not forced alignment; Giga/Nav model accuracy is unchanged.
- Actual ASR fragments such as `Wi` + `-Fi` are joined only when they match the caption tokenization, using their original timing envelope. Explicit separate-fragment captions remain separate. Word animations reject text/timing mismatches instead of silently inventing evenly spaced timestamps. Punctuation changes are allowed. Slide + Fade supports edited captions without word timings.

## Adobe output

**After Effects:** editable native text layers, one layer per word; Moving Highlight also creates a native rounded shape. Changes are in an undo group. Large transcripts create many layers. Existing Animation Composer handoff is still available as a separate choice and needs the user's installation of Composer.

**Premiere:** an offline Python/Pillow renderer makes an alpha-channel QuickTime MOV (qtrle/argb). It is imported into an existing video track that is empty over the whole selected range. Create a free video track if needed. Source media is not replaced. The MOV is editable as a clip; its text is baked. SRT remains separately editable. Large/high-resolution timelines can take time and create large MOV files.

**MOGRT:** in an already saved AE project, export a separate template per caption. The word Source Text controls are exposed to Essential Graphics. Export creates comps and a manifest beside the MOGRT files. In Premiere, enter that manifest's absolute path under **Animatsiya fayllari**, then import onto a free video track. Exported manifests use template paths relative to their folder. Copy the whole MOGRT folder when moving computers; existing absolute-path manifests are still supported. A failed MOGRT import can leave already inserted clips; its error reports the count. Verify the timeline before retrying. Template word timing is baked; changing word count requires regeneration.

An AE animation import error removes the layers created by that attempt. Animation work can be canceled while the Python process runs; cancellation preserves the review and edited text. Synchronous Adobe imports/exports finish before the panel can respond; cancellation is disabled during those calls. SRT, plan, and rendered files remain under `exports` for reuse.

## Implementation and research

The planner, renderer and Adobe layer code are our own implementation. No Remotion runtime or third-party preset code is bundled.

Research references:

- [remotion-captions-kit](https://github.com/Fats403/remotion-captions-kit), MIT, for word-driven motion ideas.
- [auto-caption](https://github.com/sebetancurch/auto-caption), MIT, for readable word highlight/pop conventions.
- [OpenCut](https://github.com/SysAdminDoc/OpenCut), for available caption style approaches.
- [Remotion licensing](https://www.remotion.dev/docs/license), considered when choosing our independent renderer.
- [AE text match names](https://ae-scripting.docsforadobe.dev/matchnames/layer/textlayer/), [CompItem MOGRT methods](https://ae-scripting.docsforadobe.dev/item/compitem/), [Premiere track methods](https://ppro-scripting.docsforadobe.dev/sequence/track/).
- [OpenType naming table](https://learn.microsoft.com/en-us/typography/opentype/spec/name), for resolving the PostScript font name used by AE.

Pillow is installed with runtime requirements on macOS Apple Silicon/Intel and Windows. Fonts are read from the customer's OS; font files are not redistributed. FFmpeg comes from imageio-ffmpeg. Both retain their installed package/license metadata.

## Verification limits

Automated checks cover real transparent MOV generation/decoding for every preset, timing/text validation, safe placement, saved styles, split/merge, failure and cancellation, empty-track protection, and mocked Adobe scripting dispatch. They do not prove live AE/Premiere rendering or MOGRT import on every Adobe release. Live Adobe output remains a release gate; no universal error-free guarantee is made.

## After Effects · 0.6.2

Har bir subtitr bloki (cue) faol kompozitsiyada bitta tahrirlanadigan text layer bo‘ladi. Ikki vizual qatorli cue ham bitta layerda saqlanadi. `UzScribe 001 · matn` nomi, startTime/inPoint/outPoint va Work Area offset bilan timeline’da joylashtiriladi. Karaoke/pop/reveal/emphasis text animator va range selector orqali so‘zlarni shu layer ichida boshqaradi; slide butun cue’ni animatsiyalaydi. Pill presetida har cue uchun bitta text layer va unga parent qilingan bitta highlight shape yordamchi layer bor. Animation Composer oddiy cue layerlarini tanlab beradi. MOGRT eksportining ichki so‘z layerlari alohida eksport kompozitsiyasida qoladi.

UzCaption rasmiy [plugin sahifasi](https://caption.uz/plugin) AE qo‘llovini ko‘rsatadi; ochiq sahifada AE ichki layer tuzilishi yoki manba kodi berilmagan. Ushbu o‘zgarish foydalanuvchi so‘ragan cue-per-layer ish jarayoni va Adobe text animator API asosida yozildi.

Mahalliy Node host testlari layer soni, butun matn, range indekslari (paragraph break hisoblanmaydi), offset, yordamchi shape, Composer va xatoda rollbackni tekshiradi. Ushbu o‘zgarishning haqiqiy Adobe host sinovi hali tasdiqlanmagan.

## After Effects: selected video (0.6.3)

Select exactly one video layer with audio in the composition timeline. Automatic/full range uses that layer’s visible in/out range; Work Area mode uses its intersection with the selected layer. Only the selected layer’s audio is rendered from a disposable composition copy. The original audio, solo, lock and guide settings are preserved; native rendering keeps stretch, time remapping and audio effects. Captions appear in the original composition at the corresponding timeline times, with one editable text layer per cue.
