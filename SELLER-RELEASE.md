# Commercial release gate

The current ZIP is a **beta** installer for macOS and Windows. Before taking payment for a final release:

1. Add the seller identity and contact details to buyer documentation and purchase terms. The product name in the panel is UzScribe.
2. Sign the static CEP panel as ZXP with the seller's certificate using Adobe `ZXPSignCmd` through `tools/sign_panel.py`; verify the signature. Ship the signed ZXP in the buyer ZIP. Keep the private `.p12` and password outside the repository. Test the signed ZXP independently on macOS and Windows; Adobe documents a cross-platform signing issue with some CEP packages.
3. Test clean macOS Apple Silicon, macOS Intel and Windows x64 machines with the supported Premiere Pro and After Effects versions. Verify panel loading, full and In/Out audio export, captions import, After Effects text layers, the installer, uninstall/reinstall and a media file with Uzbek speech. Windows, Intel Mac and Apple Silicon installer CI was previously verified; live Adobe integration and the new podcast workflow require host testing.
4. Confirm the Whisper MIT license and optional NavAI Apache-2.0 notice are included and review third-party training-data attribution. Do not include Rubai weights until its license is clarified. Check GigaAM training-data provenance before bundling its weights commercially.
5. Prepare actual purchase license, refund/support policy, privacy page and payment delivery in the chosen sales channel. This package contains no license-key enforcement or payment integration.
6. Plan a UXP migration. Adobe says CEP will be removed from its flagship desktop apps from December 2029; Premiere already supports UXP, while After Effects UXP public beta is planned for November 2026. Explain the supported Adobe versions and update policy to buyers.

The release builder accepts `--signed-zxp path/to/UzScribe.zxp` once the panel is signed. Build the ZIP with:

```text
python3 tools/build_release.py --model-dir models/navai-small --output UzScribe.zip --signed-zxp UzScribe.zxp
```

Adobe's [CEP packaging guide](https://github.com/Adobe-CEP/Getting-Started-guides/blob/master/Package%20Distribute%20Install/readme.md) describes signing and verification. Its [signing issue note](https://github.com/Adobe-CEP/CEP-Resources/blob/master/ZXPSignCMD/KnownIssue2024.md) recommends testing on both platforms.
