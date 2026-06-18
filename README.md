# 🎵 Discord YouTube 音樂機器人

自架的 Discord 音樂機器人,用 `discord.py` + `yt-dlp` + `FFmpeg`。主打**抗 YouTube 封鎖**——靠住宅 IP 部署、yt-dlp 持續更新、cookies 機制,解決一般機器人「被 YouTube 擋掉就不能播」的痛點。支援 YouTube / SoundCloud、整張播放清單、歌詞、Gemini 自然語言找歌、自動電台、Spotify 匯入。

> 純 slash 指令 · 模組化 cog 架構 · 每首播放當下才解析串流(避免佇列久放網址過期)

## ✨ 功能

- 🎧 **播放**:YouTube / SoundCloud 網址或關鍵字、整張 YouTube 播放清單(無上限)
- 📜 **佇列**:分頁顯示、移除、清空、打亂
- 🎚️ **控制**:投票跳過、暫停/繼續、跳轉(絕對/相對)、音量、單曲/整列循環
- 🔎 **搜尋**:YouTube 與 SoundCloud,下拉選單選曲(SoundCloud 兼作 YT 被擋時的備援來源)
- 🎤 **歌詞**:lrclib 免金鑰歌詞,可選 Gemini 翻譯
- 🤖 **AI(Gemini)**:`/find` 自然語言找歌、`/autoplay` 自動電台續播
- 💾 **歌單**:把佇列存成具名歌單(SQLite),隨時載入
- 🟢 **Spotify**:匯入歌曲/歌單/專輯連結(轉到 YouTube 播放)
- 🛡️ **抗封鎖**:自動偵測 cookies.txt、中途中斷自動續播、閒置自動離開

## 🚀 快速開始

需求:Python 3.10+、FFmpeg(在 PATH 上)。

```bash
git clone <你的repo網址>
cd discord-music-bot
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1   /  macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # 填入你的 DISCORD_TOKEN
python bot.py
```

Windows 使用者可直接雙擊 `start.bat`(第一次會自動建環境、裝套件、啟動)。

### 建立 Discord Bot

1. 到 [Discord Developer Portal](https://discord.com/developers/applications) → New Application。
2. **Bot → Reset Token**,複製後填入 `.env` 的 `DISCORD_TOKEN`(本機 slash 指令版**不需**開任何特權 intent)。
3. **OAuth2 → URL Generator**:scope 勾 `bot` + `applications.commands`,權限勾 `View Channels` / `Connect` / `Speak`,用產生的網址把 bot 邀進伺服器。

> 測試期建議在 `.env` 設 `DEV_GUILD_ID=<你的伺服器ID>`,指令會即時同步;否則全域同步可能要幾分鐘到一小時。

## ⚙️ 設定(.env)

`DISCORD_TOKEN` 必填,其餘選填(沒填則對應功能自動停用,bot 照常運作):

| 變數 | 用途 |
|------|------|
| `DISCORD_TOKEN` | **必填**,bot token |
| `GEMINI_API_KEY` | `/find`、`/autoplay`、歌詞翻譯([免費金鑰](https://aistudio.google.com/apikey)) |
| `SPOTIPY_CLIENT_ID` / `SPOTIPY_CLIENT_SECRET` | `/spotify` 匯入 |
| `COOKIES_FROM_BROWSER` | 改從瀏覽器讀 cookie(`firefox`/`chrome`/`edge`) |
| `DEV_GUILD_ID` | 測試期即時同步指令用 |

## 🛡️ 抗封鎖(cookies)

程式會自動偵測本資料夾的 `cookies.txt`,有就掛上:

1. 瀏覽器裝匯出 cookie 的擴充套件(Chrome/Edge:「Get cookies.txt LOCALLY」;Firefox:「cookies.txt」)。
2. 用**拋棄式 Google 帳號**登入 YouTube(別用主帳號),建議無痕視窗。
3. 在 youtube.com 匯出成 `cookies.txt` 放進本資料夾,重啟即生效。
4. 被擋時:重匯 cookies.txt,或執行 `update-ytdlp.bat` / `pip install -U yt-dlp`。

## 🧩 指令

| 類別 | 指令 |
|------|------|
| 播放 | `/play` `/nowplaying` `/skip`(投票) `/pause` `/resume` `/seek` `/volume` `/loop` `/stop` `/leave` |
| 佇列 | `/queue` `/remove` `/shuffle` |
| 搜尋 | `/search` `/scsearch` |
| 歌詞/AI | `/lyrics` `/find` `/autoplay` |
| 歌單 | `/playlist_save` `/playlist_load` `/playlists` `/playlist_delete` |
| Spotify | `/spotify` |

## 🏗️ 架構

```
bot.py                進入點:載入 cog、同步指令、錯誤處理
music/
  player.py           GuildPlayer:佇列/目前曲目/循環/seek/音量/自動電台/中斷續播
  sources.py          yt-dlp:解析、播放時取串流、YT/SC 搜尋、清單展開
  lyrics.py ai.py spotify.py db.py ui.py format.py
  cogs/               各功能指令(playback / queue / search / lyrics / ai / playlists / spotify)
```

## 📦 部署到 Linux / home server

- 安裝 `ffmpeg` 與 `libopus0`:`apt install ffmpeg libopus0`。
- 建議跑在住宅 IP(家用伺服器),最不易被 YouTube 封鎖。
- 可進一步 Docker 化。

## ⚠️ 免責聲明

本專案僅供**個人學習與自用**。透過此工具存取 YouTube 內容可能違反其服務條款,使用風險請自行承擔,請勿用於商業或大量公開服務。

## 授權

[MIT](LICENSE)
