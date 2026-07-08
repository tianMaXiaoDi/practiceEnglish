# Practice English

Practice English 是一个本地优先的英语学习项目，核心素材来自真实英文视频。

这个项目的目标不是做一个“看英语视频”的播放器，而是把一个英文视频转换成可练习的学习场景，让学习者可以：

- 看中英双语字幕视频
- 按句子反复听原声
- 开口进行影子跟读
- 录下自己的跟读声音
- 对比自己的表达和原句
- 复习自己读不准、听不清的句子

## 产品方向

第一版定位为个人本地工具，不做公开平台，也不做抖音/微信小程序。

这样可以把成本降到最低，先验证最核心的学习闭环：

```text
听原句 -> 开口跟读 -> 录音 -> 转写 -> 对比 -> 复习
```

等本地版本真正好用，再根据实际使用效果和公开视频的流量反馈，决定是否继续做小程序、移动端或平台化能力。

## MVP 范围

第一版需要从 YouTube 链接或本地 MP4 生成一个本地学习包：

```text
projects/
  video-name/
    source.mp4
    practice.mp4
    bilingual.mp4
    segments.json
    study.tsv
    anki.csv
    practice.html
    attempts.json
    recordings/
```

核心流程：

1. 导入视频。
2. 生成英文字幕、中文字幕和逐句时间戳。
3. 打开本地练习页面。
4. 按句播放原声。
5. 录音跟读。
6. 转写自己的录音。
7. 对比自己的转写结果和原句。
8. 保存分数、错词和需要复习的句子。

## 当前起点

`tools/make_bilingual_youtube.py` 是已经验证过的第一条视频处理流水线，支持：

- YouTube 链接或本地视频输入
- 使用 `yt-dlp` 下载视频
- 支持 Cookie 和代理处理 YouTube 访问限制
- 使用 `ffmpeg` 处理音视频
- 使用 `whisper.cpp` 生成英文转写
- 生成英文 + 中文 `.ass` 字幕
- 输出烧录双语字幕的 MP4 视频
- 输出练习页使用的干净 MP4 视频

现在这条流水线已经开始扩展为学习包生成器，额外输出：

- `segments.json`：逐句时间戳、英文、中文
- `practice.mp4`：练习页播放的视频，字幕由页面实时叠加
- `bilingual.mp4`：可单独观看或发布的烧录双语字幕视频
- `study.tsv`：逐句学习表
- `anki.csv`：可导入 Anki 的句子卡片
- `practice.html`：本地跟读练习页面

## 本地运行

生成一个学习包：

```powershell
python tools\make_bilingual_youtube.py `
  --input C:\path\to\source.mp4 `
  --start 694 `
  --output-dir projects\demo `
  --project-title demo
```

如果使用 YouTube 链接，把 `--input` 换成 `--url`：

```powershell
python tools\make_bilingual_youtube.py `
  --url "https://www.youtube.com/watch?v=..." `
  --output-dir projects\demo `
  --project-title demo
```

启动本地练习服务：

```powershell
python tools\serve_practice.py projects\demo
```

然后打开终端输出的本地地址，一般是：

```text
http://127.0.0.1:8765/
```

如果 `ffmpeg` 或 `whisper.cpp` 没有在默认位置，需要显式传入：

```powershell
python tools\serve_practice.py projects\demo `
  --ffmpeg C:\path\to\ffmpeg.exe `
  --whispercpp-dir C:\path\to\whispercpp
```

## 第一版不做什么

第一版暂时不做：

- 登录注册
- 云同步
- 小程序
- 社交互动
- 排行榜
- 付费系统
- 专业音素级发音评分

第一版只关注一个问题：这个工具能不能让我每天更容易地开口练英语。

## 仓库规则

不要提交生成产物和个人数据，包括：

- 视频文件
- 音频文件
- 录音文件
- YouTube Cookie
- Whisper 模型文件
- 下载的二进制工具
- 临时项目目录
- 日志文件

Git 仓库只保存：

- 源代码
- 产品文档
- 页面模板
- 小型确定性测试样例

## 计划路线

详细路线见：

- `docs/product-spec.md`
- `docs/roadmap.md`
- `docs/commit-policy.md`
