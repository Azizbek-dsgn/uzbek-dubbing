# Uzbek speech test fixture

`uzbek-take.wav` is a mono 16 kHz PCM16 conversion of FLEURS Uzbek `dev/6034925341325265160.wav`, sample ID 1554. Original text: “U WiFi eshik qo‘ng‘irog‘ini yasadi, dedi u.” It is used to test six repeated recording takes; it is not a user's private recording.

Source: [Google FLEURS](https://huggingface.co/datasets/google/fleurs), Uzbek `uz_uz` development split. FLEURS: Fleurs: Few-shot Learning Evaluation of Universal Representation of Speech, Conneau et al. License: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/). Changes: float WAV converted to signed PCM16; test script repeats the sample with one-second pauses. Speech fixture is included only in the source/testing repository, not in the buyer release package.
