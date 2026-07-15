# 和弦钢琴音频生成

## 快速使用

```bash
python3 scripts/render_chords.py \
  --progression "Fadd9 | FM7 | Gm9 | GmM7 | Am7 | Dm9 | Gm7/C | C7(b9,b13)" \
  --tempo 125 \
  --pattern block \
  --voicing smooth \
  --output /absolute/path/chords.wav \
  --midi-out /absolute/path/chords.mid
```

输出路径必须使用绝对路径或明确的工作区相对路径。脚本不会复制原曲录音，只把和弦符号转成新的钢琴试听。

## 和弦输入

用空格或 `|` 分隔和弦。默认每个和弦持续 `--beats` 拍；在和弦后加 `:拍数` 可覆盖，例如：

```text
Cmaj7:4 | A7(b9):2 | Dm9:2 | G13:4
```

支持：

- 大、小、增、减、挂留：`C`、`Cm`、`Caug`、`Cdim7`、`Csus2`、`Csus4`
- 七、九、十一、十三及附加音：`CM7`、`Cmaj9`、`CmM7`、`C9`、`Cm9`、`C13`、`Cadd9`
- 半减和弦：`Cm7-5`、`Cø7`
- 变化音：`C7(b9,#11,b13)`
- 转位/指定低音：`Gm7/C`、`BbM7/C`
- 休止：`N.C.`、`NC` 或 `rest`

降号和升号可写作 `b/#` 或 `♭/♯`。复杂符号来自自动转录时，先人工核对根音、性质、变化音和 slash bass。

## 参数选择

### 织体 `--pattern`

- `block`：整和弦同时弹奏，最适合比较色彩。
- `arpeggio`：从低到高循环八分音符。
- `broken`：低音与中高音交替，适合较长进行。
- `bossa`：低音落在第 1/3 拍，上方和弦在反拍进入。

### 声部连接 `--voicing`

- `smooth`：自动选择距离上一和弦最近的转位，默认首选。
- `root`：右手根位，适合教学和辨认和弦构成。
- `spread`：把部分声部移低八度，获得更宽的音域。

### 真实钢琴采样

默认引擎只依赖 Python 标准库，使用加法合成、击弦瞬态、弦列轻微失谐、音高相关衰减和简易混响生成钢琴近似音色。

若系统已安装 FluidSynth，并且用户提供有权使用的 `.sf2`/`.sf3`：

```bash
python3 scripts/render_chords.py \
  --progression "Dm7 | G7 | Cmaj7 | A7" \
  --soundfont /absolute/path/piano.sf2 \
  --output /absolute/path/real-piano.wav \
  --midi-out /absolute/path/progression.mid
```

不要擅自下载版权或授权不明的 SoundFont。没有 FluidSynth 时保留 MIDI，用户可在 DAW 中加载自己的钢琴音源。

## 验证

生成后执行：

```bash
python3 scripts/render_chords.py --inspect /absolute/path/chords.wav
```

确认声道数、采样率、位深、时长和峰值。再用播放器抽听：

- 低音是否与 slash chord 一致；
- 变化音是否存在；
- 自动转位是否意外跨越过大；
- 音频是否削波；
- 和弦时长是否与节拍设定一致。

需要精确模拟原曲时，除和弦外还需提供节奏、转位、力度、踏板、速度变化与实际小节长度；不要把简化试听称为原曲复刻。
