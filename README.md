# analyze-music

Compatible with **Codex**, **Claude Code**, **Kimi Code**, and other agents supporting the `SKILL.md` convention.

---

## 中文介绍

**Analyze Music（乐曲深度分析）** 是一个面向音乐学习、创作与研究的 Codex Skill，旨在把"听起来如何"转化为有证据、可复查、可用于创作实践的音乐分析。

它适合音乐爱好者、乐手、词曲作者、编曲师、制作人、音乐专业学生、教师及研究者，可用于单曲拆解、扒谱辅助、作品研究、版本比较、风格辨析、编曲与制作学习、和声验证及创作参考。

该 Skill 以现代录音音乐为重点，主要覆盖流行、R&B、Neo-Soul、嘻哈、摇滚、独立摇滚、朋克、金属、爵士、融合爵士、即兴音乐、电子音乐、舞曲、俱乐部音乐及各类混合子风格，同时兼顾古典音乐、室内乐、管弦乐与其他传统。

分析可基于曲名、音频、视频、总谱、MIDI、MusicXML、和弦谱、Lead Sheet、歌词或用户提供的听音笔记，并根据材料质量明确区分可验证事实、直接观察、分析解释与不确定推断。

### 分析框架涵盖

| 维度 | 内容 |
|------|------|
| 曲式结构 | 段落功能与能量发展 |
| 旋律 | 主题、动机及其变形 |
| 和声 | 调性、调式、和弦进行与声部连接 |
| 节奏 | 节拍、节奏型、groove、swing 与微时值 |
| 织体 | riff、低音、鼓组及伴奏声部的互锁关系 |
| 音色 | 配器、织体、音区与音色设计 |
| 表演 | 演唱、奏法、即兴及乐手互动 |
| 制作 | 录音、混音、空间与制作手法 |
| 文本 | 歌词叙事及音乐与文本的关系 |
| 语境 | 作曲家或音乐人的创作背景、风格来源与文化语境 |

输出支持快速导览、标准分析、学术深度、创作拆解和版本对比等不同层级，并优先使用时间轴、结构表、和弦标记及具体回听点呈现结论。

除文字分析外，它还可以将和弦进行渲染为钢琴近似音色的 WAV 和标准 MIDI，用于试听和声色彩、比较转位与声部连接、验证分析结果或预览再和声方案。

---

## 技术说明

- **Claude Code**、**Kimi Code** 等具备终端能力的 Agent 可以执行钢琴音频脚本；普通网页聊天能否执行，取决于其文件系统和 Python 工具权限。
- Skill 只能指导 AI 分析，不能凭空赋予其听音、联网或读取版权音频的能力；没有音频访问能力时，只能依据曲名、资料或用户提供的乐谱分析。
- 默认钢琴 WAV/MIDI 生成只使用 Python 标准库，跨平台性较好；采样钢琴模式仍需额外安装 FluidSynth 并提供合法 SoundFont。


## English Introduction

**Analyze Music** is a Codex Skill for evidence-based music analysis, creative study, and critical listening. It turns impressions such as "how the music feels" into structured, traceable explanations of how musical materials create form, momentum, style, and expression.

It is designed for music enthusiasts, performers, songwriters, composers, arrangers, producers, students, educators, and researchers. Typical use cases include song breakdowns, transcription support, composition study, arrangement and production analysis, version comparison, genre identification, harmonic verification, and creative reference.

The Skill focuses primarily on modern recorded music, covering pop, R&B, neo-soul, hip-hop, rock, indie rock, punk, metal, jazz, fusion, improvised music, electronic music, dance and club genres, as well as their many hybrid subgenres. It also supports classical music, chamber music, orchestral repertoire, and other musical traditions.

Analyses may be based on a named work, audio, video, score, MIDI, MusicXML, chord chart, lead sheet, lyrics, timestamps, or listening notes. Claims are explicitly separated into verified facts, direct observations, analytical interpretations, and uncertain inferences.

### Analytical Framework

| Dimension | Coverage |
|-----------|----------|
| Form | Sectional function and energy development |
| Melody | Themes, motives, and transformation |
| Harmony | Tonality, modality, chord progressions, and voice leading |
| Rhythm | Meter, rhythmic patterns, groove, swing, and microtiming |
| Texture | Interactions among riffs, bass, drums, and accompaniment |
| Timbre | Instrumentation, texture, register, orchestration, and timbre |
| Performance | Vocal delivery, articulation, improvisation, and performer interaction |
| Production | Recording, mixing, spatial design, and production techniques |
| Text | Lyrics, narrative, prosody, and text–music relationships |
| Context | Creative background, stylistic lineage, and cultural context |

The Skill supports quick overviews, standard analyses, academic-level studies, composition-oriented breakdowns, and comparative analyses. Results emphasize timelines, structural maps, consistent chord notation, concrete evidence, and actionable listening cues.

#### It can also render chord progressions as piano-like WAV audio and standard MIDI, making it possible to audition harmonic colors, compare inversions and voicings, verify an analysis, or preview reharmonization ideas.
---

## Technical Notes

- **Claude Code**, **Kimi Code**, and other terminal-capable agents can execute the piano audio script. Web chat execution depends on filesystem and Python tool access.
- This Skill guides analysis; it does not grant the AI the ability to hear audio, access the internet, or read copyrighted material. Without audio access, analysis relies on titles, references, or user-provided scores.
- Default piano WAV/MIDI generation uses only the Python standard library for cross-platform compatibility. Sampled piano mode requires FluidSynth and a legally obtained SoundFont.

---

## License

MIT
