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

The assistant focuses on clothing, pose, and composition, which are what users edit most. Quality tags vary by model and character tags come from Danbooru or a LoRA, so both are left to the user; anything the user supplies is kept verbatim. Tags come from a per-model vocabulary that can be updated: the assistant looks tags up before writing and checks each one before delivery instead of relying on memory.

NL is written only for what tags cannot express ("She has a mole under her left eye.", "She sits on the desk."), in plain sentences without stacked adjectives. When tagging an image, the assistant checks the tagger's long scored list against the image and keeps only what matters, so the user reviews a short list. Multi-character prompts have their own NL-first mode: the user provides trigger words and appearance, and the assistant writes positions, actions, and interaction. Each model's style and token limit live in `references/模型档案.md` (model profiles), maintained by the assistant.

## Modes

| Input | Mode | Guide |
|---|---|---|
| Text request, single subject | Creation | [创作分支](references/创作分支.md) |
| Image | Reverse | [反推分支](references/反推分支.md) |
| Several characters / trigger words and appearance | Multi-character | [多角色模式](references/多角色模式.md) |
| "Update the vocabulary to model X" | Vocabulary | [词表维护](references/词表维护.md) |

Format rules: [格式规范](references/格式规范.md).

**Switching models**: naming a model in a request applies only to that conversation; saying "from now on I use X" / "I'm using X" changes the default in the profile file.

## Install

Requires Python 3.11+. With NVIDIA CUDA, the original PixAI model runs on GPU (PyTorch 2.8.0 cu128); otherwise PixAI ONNX runs on CPU (no PyTorch needed).

```powershell
git clone https://github.com/Tu-Doou/simple-tagger.git
cd simple-tagger
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

- `SKILL.md`: Agent Skill entry
- `references/`: mode guides, format rules, and model profiles
- `tools/`: tagging, vocabulary, validation, and setup scripts
- `vocab/`: tag vocabulary and its source record
- `models/`: T5 tokenizer; tagger weights are downloaded by setup and not tracked

## Troubleshooting

- **`+unk` warning**: the prompt contains characters the T5 vocabulary cannot represent (e.g. Chinese). Use English.
- **Over the token limit**: drop optional NL sentences first, then minor scene tags, keeping what the user explicitly asked for. The limit comes from the model profile.
- **"Tag not in vocabulary"**: use the validator's suggested near match or move the idea into NL; put user-supplied trigger words in `--user-tags`.

## License

[MIT License](./LICENSE). Third-party assets: [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).
