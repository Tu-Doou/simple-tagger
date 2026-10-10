<h1 align="center">anima-tagger</h1>

<p align="center">An Agent Skill that helps write AI image prompts.<br>Chinese request ➔ Danbooru tags from a real vocabulary; image ➔ tagger output curated by the assistant; multi-character ➔ NL-first composition of actions and poses.</p>

<p align="center">
  <a href="./README.en.md">English</a> | <a href="./README.md">简体中文</a>
</p>

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-22C55E?style=flat-square" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Default-Anima-purple?style=flat-square" alt="Default: Anima">
</p>

`anima-tagger` works as an **Agent Skill** (per the [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills) specification), and its tools also run standalone from the command line. The skill instructions are written in Chinese.

## Design

| Principle | Meaning |
|---|---|
| **Focus on clothing, pose, and composition** | These are what users edit most, so tag choice there must be precise and complete. Scene and lighting are written only when requested. |
| **Quality and character tags are left to the user** | Quality strings differ per model; character tags come from Danbooru or a LoRA. Anything the user supplies is kept verbatim. |
| **Tags come from a vocabulary, not from memory** | The assistant looks tags up before writing and the validator checks each one before delivery. The vocabulary can be updated per model. |
| **NL only for what tags cannot say** | If tags already describe the image, no NL is written. When NL is needed it is plain ("She has a mole under her left eye."), without stacked adjectives. |
| **Image tagging curated by the assistant** | The tagger emits a long scored list; the assistant checks it against the image and keeps what matters, so the user reviews a short list. |
| **Separate multi-character mode** | The user provides trigger words and appearance per character; the assistant writes NL for positions, actions, and interaction. |
| **Per-model writing style** | `references/模型档案.md` (model profiles) records the default model and each model's tag/NL style and token limit, maintained by the assistant. |

## Modes

| Input | Mode | Guide |
|---|---|---|
| Text request, single subject | Creation | [创作分支](references/创作分支.md) |
| Image | Reverse | [反推分支](references/反推分支.md) |
| Several characters / trigger words and appearance | Multi-character | [多角色模式](references/多角色模式.md) |
| "Update the vocabulary to model X" | Vocabulary | [词表维护](references/词表维护.md) |

Format rules: [格式规范](references/格式规范.md).

**Switching models**: naming a model in a request applies only to that conversation; saying "from now on I use X" / "I'm using X" changes the default in the profile file.

## Example

<p align="center">
  <img src="./assets/example-input.jpg" alt="Example input: a girl holding a transparent umbrella on a rooftop after rain" width="420">
</p>

Reverse-tagging the image above:

```text
1girl, solo,

short hair, blue hair, blue eyes,

raincoat, see-through clothes, hood, blue shirt, pleated skirt, blue skirt,
hair flower, transparent umbrella, white footwear, sneakers,

standing on one leg, holding umbrella, outstretched arm, light smile, looking at viewer,

full body, from below, dutch angle,

outdoors, rain, puddle, rainbow, backlighting,
```

Appearance tags sit on their own line so they can be dropped when swapping in your own character.

## Install

Requires Python 3.11+. With NVIDIA CUDA, the original PixAI model runs on GPU (PyTorch 2.8.0 cu128); otherwise PixAI ONNX runs on CPU (no PyTorch needed).

```powershell
git clone https://github.com/Vincent54122/anima-tagger.git anima-tagger
cd anima-tagger
python tools/setup.py          # creates .venv-pixai-gpu, installs deps, downloads the tagger
python tools/setup.py --check  # exit code 0 means ready
```

`--device cpu` forces CPU deployment. Set `$env:HF_ENDPOINT = "https://hf-mirror.com"` if Hugging Face is slow.

## Commands

```powershell
$PY = ".\.venv-pixai-gpu\Scripts\python.exe"   # Linux: ./.venv-pixai-gpu/bin/python
```

| Command | Purpose |
|---|---|
| `& $PY tools\tag_vocab.py info` | Source, data date, and model of the active vocabulary |
| `& $PY tools\tag_vocab.py search pleated skirt` | Look up tags, sorted by post count |
| `& $PY tools\tag_vocab.py check "1girl, ..."` | Check that every tag is in the vocabulary |
| `& $PY tools\tag_vocab.py install <url> --model <name> --source-date <date>` | Install or update the vocabulary |
| `& $PY tools\pixai_tagger.py <images...> --json` | Tag images with per-tag confidence |
| `& $PY tools\anima_validate.py --tags "..." --nl "..." --token-limit 512 --user-tags "..."` | Pre-delivery check: normalize, fold, conflicts, vocabulary, quality tags, token count |

## Layout

```text
anima-tagger/
├── SKILL.md                 # Agent Skill entry
├── references/
│   ├── 模型档案.md          # default model and per-model style (maintained by the assistant)
│   ├── 格式规范.md          # format, NL rules, exclusions
│   ├── 创作分支.md          # text request ➔ tags / NL
│   ├── 反推分支.md          # image ➔ curated tags
│   ├── 多角色模式.md        # NL-first multi-character prompts
│   └── 词表维护.md          # vocabulary update flow and known sources
├── tools/
│   ├── setup.py             # environment setup and weight download
│   ├── pixai_tagger.py      # PixAI tagger (CUDA / ONNX CPU)
│   ├── tag_vocab.py         # vocabulary install, search, check
│   └── anima_validate.py    # pre-delivery validator and T5 token count
├── vocab/                   # tag vocabulary and manifest.json
├── assets/
└── models/
    ├── t5_tokenizer/        # bundled T5 tokenizer
    └── pixai-tagger-*/      # tagger weights (downloaded by setup, not tracked)
```

## Troubleshooting

- **`+unk` warning**: the prompt contains characters the T5 vocabulary cannot represent (e.g. Chinese). Use English.
- **Over the token limit**: drop optional NL sentences first, then minor scene tags, keeping what the user explicitly asked for. The limit comes from the model profile.
- **"Tag not in vocabulary"**: use the validator's suggested near match or move the idea into NL; put user-supplied trigger words in `--user-tags`.

## License

[MIT License](./LICENSE). Third-party assets: [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).
