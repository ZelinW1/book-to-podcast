# Episode script format

The Markdown file is both the human deliverable and the TTS source. Keep the syntax simple:

```markdown
# 第 01 期：问题从哪里开始

<!-- language: Chinese -->

## 旁白
<!-- source: c0001,c0002 -->
今天我们先看一个问题：人怎样判断自己的认识可靠？

## 旁白
<!-- source: c0003 -->
这里说的“经验”，有一个严格的含义。我们先把它讲清楚。
```

- The `#` heading is the episode title.
- Each `##` heading is a speaker role and starts one coherent speech turn. Keep turn text as plain paragraphs. The same role may occur repeatedly. Split for a meaningful rhetorical transition; let the TTS adapter choose reliable synthesis chunks within a turn.
- `<!-- language: ... -->` is optional. The TTS command's `--language` overrides it.
- `<!-- source: ... -->` names source chunk IDs used for that turn; it is never spoken. Use an empty `source` only for an original introduction, transition, or clearly signaled example.
- Do not put stage directions, pronunciations, or citations in the spoken paragraphs. Put them in adaptation notes or TTS configuration.
- Distinct roles in a two-person episode must map to distinct voices. The Qwen adapter takes repeated `--voice ROLE=VOICE` arguments.

The included synthesizer splits a turn at sentence boundaries when needed. Timing IDs refer to those split pieces, while `turn` points back to the Markdown heading order. These boundaries do not provide word-accurate subtitle timing.
