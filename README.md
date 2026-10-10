<h1 align="center">anima-tagger</h1>

<p align="center">辅助书写 AI 绘画提示词的 Agent Skill。<br>中文需求 ➔ 词表内的 Danbooru tag；图片 ➔ 打标后由助手看图精选 tag；多角色 ➔ 以 NL 为主拼接动作与姿势。</p>

<p align="center">
  <a href="./README.en.md">English</a> | <a href="./README.md">简体中文</a>
</p>

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-22C55E?style=flat-square" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Default-Anima-purple?style=flat-square" alt="Default: Anima">
</p>

`anima-tagger` 既可作为 **Agent Skill**（遵循 [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills) 标准）挂载给 AI 助手，也能在命令行单独使用其中的工具。

## 设计取向

| 取向 | 说明 |
|---|---|
| **重点放在服装、姿势、构图** | 这是用户最常要改的部分，选词要准、要全；场景与光影只写需求里提到的。 |
| **质量词、人物 tag 交给用户** | 质量串因模型而异；人物 tag 可以去 Danbooru 查或用 LoRA。用户给的原样保留。 |
| **tag 来自词表，不靠模型凭记忆捏造** | 写 tag 前查词表，交付前逐个比对；词表可按模型更新。 |
| **NL 只补 tag 说不清的部分** | tag 已经能描述的画面就不写 NL；要写也写得直白（「她左眼下有颗痣」「她坐在桌子上」），不堆形容词。 |
| **图片反推由助手看图精选** | 打标器输出带置信度的长清单，助手对照原图挑出用户真正需要的那一组，用户只需审一份精炼清单。 |
| **多角色单独一个模式** | 用户提供角色触发词与外观，助手用 NL 拼接位置、动作与互动。 |
| **按模型切换写法** | `references/模型档案.md` 记录默认模型与各模型的 tag/NL 写法、token 上限，由助手维护。 |

## 模式

| 输入 | 模式 | 指南 |
|---|---|---|
| 中文画面需求（单主体） | 创作 | [创作分支](references/创作分支.md) |
| 图片 | 反推 | [反推分支](references/反推分支.md) |
| 多个角色 / 角色触发词与外观 | 多角色 | [多角色模式](references/多角色模式.md) |
| 「更新词表到 xx 模型」 | 词表维护 | [词表维护](references/词表维护.md) |

格式与禁则见 [格式规范](references/格式规范.md)。

**切换模型**：在请求里点名模型（「这张给 xx 用」）只对本次生效；说「我接下来都用 xx」「我用的是 xx 模型」才会改档案里的默认模型。

## 示例

<p align="center">
  <img src="./assets/example-input.jpg" alt="示例输入：雨后天台上撑着透明伞的少女" width="420">
</p>

反推上图：

```text
1girl, solo,

short hair, blue hair, blue eyes,

raincoat, see-through clothes, hood, blue shirt, pleated skirt, blue skirt,
hair flower, transparent umbrella, white footwear, sneakers,

standing on one leg, holding umbrella, outstretched arm, light smile, looking at viewer,

full body, from below, dutch angle,

outdoors, rain, puddle, rainbow, backlighting,
```

外貌单独一行，换成自己的角色时整行删掉即可。

## 安装

环境要求：Python 3.11 或更新版本。有 NVIDIA CUDA 时用 PixAI 原版 GPU 推理（PyTorch 2.8.0 cu128），否则用 PixAI ONNX CPU 推理（无需 PyTorch）。

```powershell
git clone https://github.com/Vincent54122/anima-tagger.git anima-tagger
cd anima-tagger
python tools/setup.py          # 建 .venv-pixai-gpu，装依赖，拉取打标模型
python tools/setup.py --check  # 检查环境，退出码 0 即就绪
```

国内网络可先设镜像：`$env:HF_ENDPOINT = "https://hf-mirror.com"`。`--device cpu` 强制按 CPU 部署。

## 命令速查

```powershell
$PY = ".\.venv-pixai-gpu\Scripts\python.exe"   # Linux: ./.venv-pixai-gpu/bin/python
```

| 命令 | 用途 |
|---|---|
| `& $PY tools\tag_vocab.py info` | 当前词表的来源、数据日期、对应模型 |
| `& $PY tools\tag_vocab.py search pleated skirt` | 查词，按帖子数排序 |
| `& $PY tools\tag_vocab.py check "1girl, ..."` | 校验一串 tag 是否都在词表内 |
| `& $PY tools\tag_vocab.py install <url> --model <名> --source-date <日期>` | 安装/更新词表 |
| `& $PY tools\pixai_tagger.py <图片...> --json` | 打标，输出每个 tag 的置信度 |
| `& $PY tools\anima_validate.py --tags "..." --nl "..." --token-limit 512 --user-tags "..."` | 交付前校验：规范化、折叠、冲突、词表、质量词、token 计数 |

## 仓库结构

```text
anima-tagger/
├── SKILL.md                 # Agent Skill 入口
├── references/
│   ├── 模型档案.md          # 默认模型与各模型写法（助手维护）
│   ├── 格式规范.md          # 格式、NL 规则与禁则
│   ├── 创作分支.md          # 中文需求 ➔ tag / NL
│   ├── 反推分支.md          # 图片 ➔ 精选 tag
│   ├── 多角色模式.md        # 以 NL 为主的多角色写法
│   └── 词表维护.md          # 更新词表的流程与已知来源
├── tools/
│   ├── setup.py             # 环境配置与权重下载
│   ├── pixai_tagger.py      # PixAI 打标（CUDA / ONNX CPU）
│   ├── tag_vocab.py         # 词表安装、查词、校验
│   └── anima_validate.py    # 交付前校验与 T5 token 计数
├── vocab/                   # tag 词表与 manifest.json
├── assets/
└── models/
    ├── t5_tokenizer/        # 内置 T5 分词器
    └── pixai-tagger-*/      # 打标权重（setup 自动拉取，不入库）
```

## 常见问题

- **`+unk` 警报**：提示词里有 T5 词表无法表示的字符（如中文），请改用英文。
- **token 超限**：先删 NL 里可有可无的句子，再删次要场景 tag，保护用户明确要求的内容。上限由模型档案决定。
- **「词表外 tag」**：换成校验器给的近似词，或改写进 NL；用户自己给的触发词放进 `--user-tags`。

## 开源协议

基于 [MIT License](./LICENSE) 开源发布。第三方资产说明见 [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)。
