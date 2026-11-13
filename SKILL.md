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
2. **选模式**，把该行列出的文件**在同一轮并行读完**，表外的文件不要提前读：

   | 用户给了什么 | 模式 | 读 |
   |---|---|---|
   | 画面需求，单个主体 | 创作 | `references/创作.md`、`references/通用规则.md`、`references/工具.md` |
   | 图片（附件、本地路径、「照着这张反推」） | 仔细反推 | `references/反推-仔细.md`、`references/通用规则.md`、`references/工具.md` |
   | 两个及以上角色同框，或多个角色的触发词/外观 | 多角色 | `references/多角色.md`、`references/通用规则.md`、`references/工具.md` |
   | 「更新词表到 xx 模型」「换个词表」 | 词表维护 | `references/词表维护.md`、`references/工具.md` |

3. **校验**：按校验器退出码处理：
   - **0** ➔ 交付；
   - **1** ➔ 按 `[待处理]` 逐条修改后重跑：词表外的换它给的近似词或改写进 NL；别名换成规范名；超出 token 上限见通用规则「超出 token 上限」；报无法精确计数的先跑环境体检；
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

## 交付格式

1. 成品整体放进一个 ```text 代码块；说明写在代码块下方，最多两行
2. NL 是完整英文陈述句，英文句号结尾；tag 与 NL 之间空一行

## 环境

```powershell
$SKILL = "<本 skill 目录（SKILL.md 所在目录）的绝对路径>"
$PY    = "$SKILL\.venv-pixai-gpu\Scripts\python.exe"   # Linux: $SKILL/.venv-pixai-gpu/bin/python
```

临时文件放 `$SKILL\.work\`（不存在先建）；国内网络先设 `$env:HF_ENDPOINT = "https://hf-mirror.com"`。

| 用途 | 命令 | 说明 |
|---|---|---|
| 环境体检 | `python "$SKILL\tools\setup.py" --check` | 用系统 Python 跑，因为 venv 可能还不存在。退出码非 0 时去掉 `--check` 再跑一次完成部署 |
| 交付前校验 | `& $PY "$SKILL\tools\anima_validate.py" --tags "<tag 串>" --nl "<NL，没有就省略>" --token-limit <token-limit> --user-tags "<用户给的全部内容>"` | 必须执行。负责规范化、去重、上位词折叠、槽位冲突、词表比对（词表外/别名/人物/作品/画师/元数据类）、质量词、NL 句号、T5 计数 |
