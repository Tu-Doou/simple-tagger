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

助手的注意力放在服装、姿势、构图上，这是用户最常要改的部分；质量词因模型而异，人物 tag 可以去 Danbooru 查或用 LoRA，这两类交给用户，用户给的原样保留。tag 来自可按模型更新的词表，写之前查词、交付前逐个比对，不靠模型凭记忆捏造。

NL 只补 tag 说不清的部分（「她左眼下有颗痣」「她坐在桌子上」），而且写得直白，不堆形容词。图片反推时，助手对照原图从打标器的长清单里精选出真正需要的 tag，用户只需审一份精炼清单。多角色单独成一个模式，以 NL 为主：用户提供触发词与外观，助手拼接位置、动作与互动。各模型的写法与 token 上限记录在 `references/模型档案.md`，由助手维护。

## 模式

| 输入 | 模式 | 指南 |
|---|---|---|
| 中文画面需求（单主体） | 创作 | [创作分支](references/创作分支.md) |
| 图片 | 反推 | [反推分支](references/反推分支.md) |
| 多个角色 / 角色触发词与外观 | 多角色 | [多角色模式](references/多角色模式.md) |
| 「更新词表到 xx 模型」 | 词表维护 | [词表维护](references/词表维护.md) |

格式与禁则见 [格式规范](references/格式规范.md)。

**切换模型**：在请求里点名模型（「这张给 xx 用」）只对本次生效；说「我接下来都用 xx」「我用的是 xx 模型」才会改档案里的默认模型。

## 安装

环境要求：Python 3.11 或更新版本。有 NVIDIA CUDA 时用 PixAI 原版 GPU 推理（PyTorch 2.8.0 cu128），否则用 PixAI ONNX CPU 推理（无需 PyTorch）。

```powershell
git clone https://github.com/Tu-Doou/simple-tagger.git
cd simple-tagger
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

- `SKILL.md`：Agent Skill 入口
- `references/`：各模式指南、格式规范与模型档案
- `tools/`：打标、词表、校验与环境配置脚本
- `vocab/`：tag 词表及其来源记录
- `models/`：T5 分词器；打标权重由 setup 下载，不入库

## 常见问题

- **`+unk` 警报**：提示词里有 T5 词表无法表示的字符（如中文），请改用英文。
- **token 超限**：先删 NL 里可有可无的句子，再删次要场景 tag，保护用户明确要求的内容。上限由模型档案决定。
- **「词表外 tag」**：换成校验器给的近似词，或改写进 NL；用户自己给的触发词放进 `--user-tags`。

## 开源协议

基于 [MIT License](./LICENSE) 开源发布。第三方资产说明见 [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)。
