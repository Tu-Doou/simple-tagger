---
name: simple-tagger
description: 辅助书写 AI 绘画提示词。中文需求 ➔ 词表内的 Danbooru tag（必要时补几句直白 NL）；图片 ➔ 打标后由助手看图按置信度精选 tag；多角色画面走以 NL 为主的多角色模式。NL 风格与 token 预算按模型档案切换，tag 词表可按模型更新。当用户要写/改提示词、发图要反推 tag、要拼多角色提示词、说「更新词表到 xx 模型」或「我用的是 xx 模型」时使用。
---

# simple-tagger

## 先定模型

每次任务开始先读 `references/模型档案.md`：

- 用户在本次请求里**点名**某个模型（「用 xx 写」「这张给 xx 用」）➔ 本次对话按该模型的档案写，**不改档案**；
- 用户表达了**长期切换**（「我接下来都用 xx」「我用的是 xx 模型」「默认改成 xx」）➔ 修改档案的「默认模型」块，再按它写；
- 都没有 ➔ 用档案里的默认模型。

档案里没有用户点名的模型 ➔ 先查该模型的官方提示词说明，按档案末尾的模板新增一节，告诉用户新增了什么，再继续任务。用户在使用中补充了某模型的写法，同样写进档案。

## 选模式

| 用户给了什么 | 走哪个模式 | 读哪份指南 |
|---|---|---|
| 中文（或任意语言）的画面需求，单个主体 | **创作** | `references/创作分支.md` |
| 图片（附件、本地路径、「照着这张反推」） | **反推** | `references/反推分支.md` |
| 两个及以上角色同框，或用户发来多个角色的触发词/外观 | **多角色** | `references/多角色模式.md` |
| 「更新词表到 xx 模型」「换个词表」 | **词表维护** | `references/词表维护.md` |

格式与禁则以 `references/格式规范.md` 为准，所有模式都要遵守。

---

## 核心原则

1. **注意力放在服装、姿势、构图**。角色穿什么、摆什么姿势、从什么视角画，是用户最常要改的部分，选词要准、要全；场景和光影只写需求里提到的或画面成立必需的。
2. **不主动写质量词和人物 tag**。质量串因模型而异，人物 tag 用户会自己去 Danbooru 查或用 LoRA，这两类交给用户。用户自己给的角色名、触发词、质量串原样保留（校验时放进 `--user-tags`）。
3. **tag 必须在词表内**。写 tag 前用 `tools/tag_vocab.py search` 查词，交付前由校验器逐个比对；词表外的 tag 换成词表里的近义词，或改用 NL 表达。
4. **NL 只补 tag 说不清的东西**。tag 已经能描述的画面就不写 NL，剩下交给抽卡；只有用户要求了 tag 无法准确表达的细节（「她左眼下有颗痣」「她坐在桌子上」「A 把伞递给 B」）才写 NL。NL 不复述 tag。
5. **NL 直白**。一句只说一件事，主语 + 动作/位置；只留能区分画面的形容词（颜色、左右、大小），不写「暖洋洋」「宽阔无比」这类修辞。具体写法以模型档案为准。
6. **多角色以 NL 为主**。用户发来角色触发词与外观，助手负责把动作、姿势、位置和互动拼成 NL；tag 只放人数、触发词与全局构图。
7. **只写画面里看得见的东西**。不写镜头外的设备与拍摄说明、看不见的心理与因果，也不写「画面里没有××」这类负向句。

---

## 工具

### 环境

```powershell
$SKILL = "<本项目根目录的绝对路径>"
$PY    = "$SKILL\.venv-pixai-gpu\Scripts\python.exe"   # Linux: $SKILL/.venv-pixai-gpu/bin/python；已激活环境可直接用 python
python "$SKILL\tools\setup.py"           # 首次部署：建 venv、装依赖、拉取打标模型
python "$SKILL\tools\setup.py" --check   # 体检，就绪返回 0
```

有 CUDA 时用 PixAI 原版 GPU 推理（BF16，可选 FP32），否则用 ONNX CPU，缺的文件会自动下载；`--device cpu` 强制 CPU。国内网络可先设 `$env:HF_ENDPOINT = "https://hf-mirror.com"`。临时文件统一放 `$SKILL\.work\`。

### 词表

```powershell
& $PY "$SKILL\tools\tag_vocab.py" info                          # 当前词表的来源、日期、对应模型
& $PY "$SKILL\tools\tag_vocab.py" search pleated skirt          # 查词（名字或别名包含全部关键词，按帖子数排序）
& $PY "$SKILL\tools\tag_vocab.py" search sitting --limit 40     # 默认只列 general 类、帖子数 ≥ 50
& $PY "$SKILL\tools\tag_vocab.py" check "1girl, pleated skirt"  # 单独校验一串 tag
```

### 打标（反推）

```powershell
& $PY "$SKILL\tools\pixai_tagger.py" "<图片路径>" --json | Out-File "$SKILL\.work\run.json" -Encoding utf8
```

默认阈值 general 0.17、character 0.27；JSON 里带每个 tag 的置信度，供看图精选时参考。

### 交付前校验（必须跑）

```powershell
& $PY "$SKILL\tools\anima_validate.py" --tags "<完整 tag 串>" --nl "<NL，没有就省略>" --token-limit <档案规定值> --user-tags "<用户给的触发词/角色名/质量串>"
```

校验器负责：小写、下划线转空格、去重、上位词折叠、槽位冲突、词表比对（词表外、别名、人物/作品/画师/元数据类）、质量词、NL 句号、按 T5 精确计数。退出码 0 才交付；为 1 时按 problems 修改后重跑。
