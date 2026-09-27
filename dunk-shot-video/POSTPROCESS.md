# 4K / 60fps 仕上げ手順

生成モデルの出力（例: 1080p 24fps、5 秒）を、指定の **3840×2160 / 60fps / 4 秒** に仕上げる手順です。

## 手順の全体像

1. 生成動画を 4 秒にトリム
2. フレーム補間で 60fps 化
3. アップスケールで 4K 化
4. H.264 / H.265 で書き出し

補間とアップスケールの順番は「補間 → アップスケール」を推奨します。低解像度のうちに補間したほうが処理が速く、補間アーティファクトも目立ちにくいためです。

## A. GUI ツールで行う場合（推奨・最も画質が良い）

**Topaz Video AI** を使うと 2〜3 を一括でできます。

- Frame Interpolation: Apollo または Chronos、出力 60fps
- Enhancement: Proteus（実写向け）、出力 3840×2160
- 出力コーデック: H.265 Main10 または ProRes 422 HQ（編集用）

代替: **DaVinci Resolve Studio** の Optical Flow（Speed Warp）でリタイム 60fps ＋ Super Scale 2x。

## B. コマンドラインで行う場合（無料）

前提: `ffmpeg`、`rife-ncnn-vulkan`、`realesrgan-ncnn-vulkan` がインストール済み。

### 1. 4 秒にトリム（開始位置は内容を見て調整）

```bash
ffmpeg -ss 0.5 -i input.mp4 -t 4 -c:v libx264 -crf 12 -preset slow -an trim.mp4
```

### 2. 60fps 化

**簡易版（ffmpeg のみ、動き補間）**

```bash
ffmpeg -i trim.mp4 -vf "minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1" \
  -c:v libx264 -crf 12 -preset slow -an fps60.mp4
```

**高品質版（RIFE）**

```bash
mkdir -p frames_in frames_60
ffmpeg -i trim.mp4 frames_in/%06d.png
# 24fps -> 60fps は 2.5 倍。rife-ncnn-vulkan はターゲット枚数指定で対応
N_IN=$(ls frames_in | wc -l)
N_OUT=$(( N_IN * 60 / 24 ))
rife-ncnn-vulkan -i frames_in -o frames_60 -n "$N_OUT" -m rife-v4.6
```

### 3. 4K 化（Real-ESRGAN、2 倍）

```bash
mkdir -p frames_4k
realesrgan-ncnn-vulkan -i frames_60 -o frames_4k -n realesr-animevideov3 -s 2
# 実写向けにより自然な仕上がりにしたい場合は -n realesrgan-x4plus -s 4 で 4 倍にし、
# 最後の ffmpeg で 3840x2160 にスケールダウンする
```

### 4. 書き出し

```bash
# H.264（互換性重視）
ffmpeg -framerate 60 -i frames_4k/%08d.png -vf "scale=3840:2160:flags=lanczos,format=yuv420p" \
  -c:v libx264 -crf 16 -preset slow -movflags +faststart dunk_4k60.mp4

# H.265（容量重視）
ffmpeg -framerate 60 -i frames_4k/%08d.png -vf "scale=3840:2160:flags=lanczos,format=yuv420p10le" \
  -c:v libx265 -crf 18 -preset slow -tag:v hvc1 -movflags +faststart dunk_4k60_hevc.mp4
```

### 5. 確認

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate,duration -of default=noprint_wrappers=1 dunk_4k60.mp4
```

期待値: `width=3840` `height=2160` `r_frame_rate=60/1` `duration≈4.0`

## 音について

依頼にないため無音で書き出しています。必要なら体育館の環境音（シューズのスキール音、ドリブル音、リムの金属音、ネットの音）を別トラックで足すと実写感が上がります。
