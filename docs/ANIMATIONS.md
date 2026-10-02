# UzScribe 0.5.0: captions and animation

## Panel

Choose one of six presets: **Karaoke**, **Soft Pop**, **Moving Highlight**, **Word Reveal**, **Slide + Fade**, **Keyword Emphasis**. The panel shows a looping sample. It illustrates the motion; exact wrapping, font metrics and video placement are computed at export using the active sequence/composition dimensions.

Under **Uslub va joylashuv**, choose a locally installed TTF/OTF font, reference font size at 1080p, text/highlight colors, position, animation duration and Reels safe placement. Portrait safe mode keeps lower captions above the bottom 23% and uses 80% of frame width; inspect the final video for your platform's current UI. Save named styles locally; styles and models retain their upstream identity.

Review tools:

- **Keyingisi bilan birlashtirish** merges the current and next captions.
- Put the text cursor before a word, then **Kursordan bo‘lish**. The split uses that word's existing start time. Overlapping/mismatched words require correction first.
- **So‘z vaqtlari va urg‘u** allows editing each word's text, start and end in seconds. Save applies these words to the selected caption. ★ adds that word to the emphasis list.
- **Whisper bilan vaqtni tekshirish** re-recognizes the exported audio with the installed Global model and updates matching words only. It requires at least 80% agreement, keeps the original text, and rejects conflicting timings. This is a second recognition pass, not forced alignment; Giga/Nav model accuracy is unchanged.
- Word animations reject text/timing mismatches instead of silently inventing evenly spaced timestamps. Punctuation changes are allowed. Slide + Fade supports edited captions without word timings.

## Adobe output

**After Effects:** editable native text layers, one layer per word; Moving Highlight also creates a native rounded shape. Changes are in an undo group. Large transcripts create many layers. Existing Animation Composer handoff is still available as a separate choice and needs the user's installation of Composer.

**Premiere:** an offline Python/Pillow renderer makes an alpha-channel QuickTime MOV (qtrle/argb). It is imported into an existing video track that is empty over the whole selected range. Create a free video track if needed. Source media is not replaced. The MOV is editable as a clip; its text is baked. SRT remains separately editable. Large/high-resolution timelines can take time and create large MOV files.

**MOGRT:** in an already saved AE project, export a separate template per caption. The word Source Text controls are exposed to Essential Graphics. Export creates comps and a manifest beside the MOGRT files. In Premiere, enter that manifest's absolute path under **Animatsiya fayllari**, then import onto a free video track. Copy templates too when moving to another computer and update paths in the manifest. A failed MOGRT import can leave already inserted clips; its error reports the count. Verify the timeline before retrying. Template word timing is baked; changing word count requires regeneration.

Animation work can be canceled while the Python process runs. Synchronous Adobe imports/exports finish before the panel can respond; cancellation is disabled during those calls. SRT, plan, and rendered files remain under `exports` for reuse.

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
