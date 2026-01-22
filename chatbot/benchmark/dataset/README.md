# Dataset Structure

100 healthcare dialogue samples for the memory-citation benchmark.

## Layout
```
dataset/
├── generate_speech.py       # create query.wav from text
├── sample_processing.py     # TTS → emotion/personality → context/prompt
└── samples/{id}/
    ├── sample.json          # dialogue + memory + must_use_keys
    ├── query.wav            # TTS of last user turn
    ├── context.json         # fused emotion/personality + preferences
    └── prompt.md            # ready-to-send prompt
```

## Process Data
```bash
python generate_speech.py                       # generate missing audio
python sample_processing.py                     # build context.json + prompt.md for all samples
python sample_processing.py --sample-id 001 --force-tts \
  --speech-weight 0.7 --text-weight 0.3         # customize a single sample
```

## Notes
- 100 samples (IDs 001-100), ~7-12 turns each, 4-8 memory keys; must-use keys are listed in each `sample.json`.
- Default emotion fusion: 60% speech / 40% text.
- Requires `OPENAI_API_KEY`; deps: `torch`, `transformers`, `openai`, `requests`, `numpy`, `pandas`.
