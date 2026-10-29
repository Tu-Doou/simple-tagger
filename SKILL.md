---
name: simple-tagger
description: >
   辅助书写 AI 绘画提示词：把中文需求或图片转成词表内的 Danbooru tag（必要时补英文 NL），并维护 tag 词表与模型档案。
   当用户说「帮我写个提示词 / tag」「改一下这串 tag」「这张图反推一下」「两个角色同框怎么写」「更新词表」「我接下来用 xx 模型写提示词」时使用。
   不负责出图，也不写负面提示词。
---

# simple-tagger

## 流程

1. **定模型**：默认按下方「当前默认模型」写，不必读档案。
   - 本次请求点名了别的模型（「这张给 xx 用」）➔ 读 `references/模型档案.md` 里该模型一节，本次按它写，不改默认；
   - 用户表达长期切换（「我接下来都用 xx」「默认改成 xx」）➔ 把档案里该模型的四项抄进「当前默认模型」块，再按它写；
   - 档案里没有该模型 ➔ 查官方提示词说明，按档案末尾模板新增一节并告诉用户。用户补充的某模型写法也记进档案。
2. **选模式**，只读对应的一份指南，其余指南不要提前读：

   | 用户给了什么 | 模式 | 指南 |
   |---|---|---|
   | 画面需求，单个主体 | 创作 | `references/创作分支.md` |
   | 图片（附件、本地路径、「照着这张反推」） | 反推 | `references/反推分支.md` |
   | 两个及以上角色同框，或多个角色的触发词/外观 | 多角色 | `references/多角色模式.md` |
   | 「更新词表到 xx 模型」「换个词表」 | 词表维护 | `references/词表维护.md` |

3. **写草稿 ➔ `check` 批量查词 ➔ 校验**，命令见「工具」，规则见「通用规则」。按校验器退出码处理：
   - **0** ➔ 交付；
   - **1** ➔ 按 `[待处理]` 逐条修改后重跑：词表外的换它给的近似词或改写进 NL；别名换成规范名；超出 token 上限见「超出 token 上限」；报无法精确计数的先跑「环境体检」；
   - **2** ➔ 命令参数写错，修正命令后重跑。

**完成标准**：校验器对最终交付的那一版返回 0；用户给的内容都在，删改过的已在代码块下方说明。

### 当前默认模型

```text
model:       Anima
input:       Danbooru tag 为主，需要时在 tag 后空一行接英文 NL
token-limit: 512（T5 分词）
tag 顺序:    人数 → 用户给的角色名/触发词 → 外貌 → 服装饰品 → 姿势表情 → 构图视角 → 场景；分组之间换行，行末保留逗号
```

`tag_vocab.py info` 显示的词表对应模型与默认模型不符时，提醒用户「更新词表」。


## 通用规则

### 选词重点

注意力放在**服装、姿势、构图**：穿什么、摆什么姿势、从什么视角画，是用户最常改的部分，要选准、拆细（颜色、款式、长短、材质、视角）。场景和光影只写需求提到的或画面成立必需的；外貌用户没给就不补。

### 用户给的内容

用户给的角色名、触发词、角色 tag 块（含 `"G41" is written on the chest` 这类句子、转义括号、分级词）、质量串，默认原样保留，校验时全部放进 `--user-tags`（否则校验器会把它们当词表外或禁用词报错）。只在两种情况下删改，并在代码块下方说明：

- 与本次需求冲突：需求要光腿，就删 `single thighhigh` 这类腿部服装；
- 本次构图里看不见：`from behind` 时删胸前文字、`name tag`、`covered navel` 等正面特征；头发、耳朵、发饰等背面可见、能认出角色的保留。

### 硬规则

以下规则不约束用户给的内容。大小写、下划线、分隔符由校验器自动规范化，不必手动处理。

1. 括号原样，自己写的不加转义：`hoshino (blue archive)`
2. tag 必须在词表内；词表外的换近义词或改写进 NL
3. NL 是完整英文陈述句，英文句号结尾；tag 与 NL 之间空一行
4. 成品整体放进一个 ```text 代码块；说明写在代码块下方，最多两行
5. 权重语法少用，需要时写 `(tag:1.2)`；`[tag]`、`(tag)1.2` 在 Anima 里不生效

### NL

**只补 tag 说不清的东西**。tag 能描述的就不写 NL；全部能用 tag 表达时只交 tag。

| 适合写 NL | 不写 NL |
|---|---|
| 分左右的局部特征 | tag 里已有的服装、姿势、构图（换个说法也不行） |
| 人与物的具体接触（词表无对应 tag 时） | 氛围、情绪、光影修辞 |
| 哪只手做什么、谁对谁做什么 | |

写法：一句一件事（主语 + 动作/位置 + 对象）；形容词只留颜色、左右、大小、数量；不用比喻、不叠形容词、不加 `gracefully`、`gently` 这类副词；单人用 she/he，多人用名字或稳定指称。

- 「坐着，翘二郎腿」：sitting, crossed legs
- 「坐在桌子上」：sitting, on desk（规范名为 on desk，sitting on desk 为别名）
- 「坐在桌子边缘，腿垂在外面」：sitting, on desk + She sits on the edge of the desk with her legs hanging down.
- 「左眼下有颗痣」：mole under eye + She has a mole under her left eye.（tag 不分左右）
- 「一只手撑着下巴，另一只手拿着笔」：head rest, holding pen + She rests her chin on her left hand and holds a pen in her right hand.
- 「阳光很温暖的草地」：field, sunlight，不写 NL

### 不写的内容

判断标准：**写进去的每样东西，画面上都找得到吗？** 模型会把提示词里的名词尽量画出来，写了看不见的东西就会多出不想要的物体。

- 质量词（`masterpiece`、`score_9`……）：交给用户按自己的习惯加；
- 用户没给的人物 tag、画师名、单独的作品名：会把角色长相或画风拉向特定对象，偏离用户需求；
- 负面提示词、分级标签（`general`、`sensitive`、`questionable`、`explicit`）和负向句（「画面里没有××」会把××画出来）；
- 镜头外的东西：相机、拍摄者、机位（会被画进画面）——视角用 `from above` 等构图 tag 表达；
- 看不见的心理与因果（「她正准备离开」「因为刚下过雨」）；
- 全裸时的任何服装 tag。

### 超出 token 上限

按顺序精简，每改一次重跑校验：① 删 NL 里可有可无的句子、合并句子；② 删次要场景/背景 tag 与同义堆叠；③ 用户明确要求的服装、姿势、构图、外貌、触发词不动，它们本身就超限时问用户保留哪些。


## 工具

```powershell
$SKILL = "<本 skill 目录（SKILL.md 所在目录）的绝对路径>"
$PY    = "$SKILL\.venv-pixai-gpu\Scripts\python.exe"   # Linux: $SKILL/.venv-pixai-gpu/bin/python
```

临时文件放 `$SKILL\.work\`（不存在先建）；国内网络先设 `$env:HF_ENDPOINT = "https://hf-mirror.com"`。

| 用途 | 命令 | 说明 |
|---|---|---|
| 环境体检 | `python "$SKILL\tools\setup.py" --check` | 用系统 Python 跑，因为 venv 可能还不存在。退出码非 0 时去掉 `--check` 再跑一次完成部署 |
| 批量查词 | `& $PY "$SKILL\tools\tag_vocab.py" check "1girl, pleated skirt, ..."` | 写完草稿先用它整串比对 |
| 单个概念查词 | `& $PY "$SKILL\tools\tag_vocab.py" search pleated skirt [--limit 40]` | 名字或别名含全部关键词的词条，按帖子数排序；默认只查 general 类、帖子数 ≥ 50 |
| 词表元信息 | `& $PY "$SKILL\tools\tag_vocab.py" info` | |
| 安装/更新词表 | `& $PY "$SKILL\tools\tag_vocab.py" install "<url>" --model "<模型>" --source-date "<日期>" --note "<来源说明>"` | **先经用户确认来源与日期再执行**：会下载大文件并替换当前生效的词表 |
| 取出粘贴的图片 | `& $PY "$SKILL\tools\opencode_image.py" --out "$SKILL\.work"` | 仅用于剪贴板粘贴、没有本地路径的图片。在项目目录内运行；只读 opencode 数据库，取当前项目最近一条带图消息里的全部图片，打印保存路径。`--list` 只列出，`--nth 2` 取往前第 2 条 |
| 图片打标 | `& $PY "$SKILL\tools\pixai_tagger.py" "<图片...>" --json \| Out-File "$SKILL\.work\run.json" -Encoding utf8` | 输出很长，写进文件再按需读取，不要直接打印；多图一次传入（默认阈值 general 0.17、character 0.27） |
| 裁切放大 | `& $PY "$SKILL\tools\crop.py" "<图片>" --box 左,上,右,下 --out "$SKILL\.work\crop.png"` | `--box` 用 0~1 比例坐标；输出长边放大到 1024 后再看 |
| 交付前校验 | `& $PY "$SKILL\tools\anima_validate.py" --tags "<tag 串>" --nl "<NL，没有就省略>" --token-limit <token-limit> --user-tags "<用户给的全部内容>"` | 必须执行。负责规范化、去重、上位词折叠、槽位冲突、词表比对（词表外/别名/人物/作品/画师/元数据类）、质量词、NL 句号、T5 计数 |
