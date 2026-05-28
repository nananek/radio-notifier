# radio-notifier

平日の昼休憩に聴きたい声優ラジオ / 法律系ラジオを Discord に通知する小さな bot。

曜日ごとに番組を固定で割り当て、RSS から最新エピソードの URL を Discord Webhook に投げる。木曜のみ複数チャンネルから 1 本をローテーションで選ぶ。

## 動作環境

- Python 3.11 以上
- Linux + systemd（user timer 駆動）
- Discord Webhook URL

## セットアップ

```sh
git clone <this-repo> ~/repos/radio-notifier
cd ~/repos/radio-notifier
python -m venv .venv
.venv/bin/pip install -e '.[dev]'

mkdir -p ~/.config/radio-notifier
cp config.example.toml ~/.config/radio-notifier/config.toml
$EDITOR ~/.config/radio-notifier/config.toml   # webhook_url と channel_id を埋める
```

## 使い方

```sh
radio-notifier list                              # 設定の番組一覧
radio-notifier dry-run                           # 今日の picks を stdout に
radio-notifier dry-run --date 2026-06-04        # 任意の日付で picks を確認
radio-notifier run                               # 実際に Discord 通知 (state 更新)
```

## systemd 常駐化（ネイティブ）

```sh
mkdir -p ~/.config/systemd/user
cp systemd/radio-notifier.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now radio-notifier.timer
systemctl --user list-timers radio-notifier.timer

# ログ
journalctl --user -u radio-notifier -f
```

サーバ的に常時起動していない PC では `loginctl enable-linger $USER` も実行する。

## Docker でのデプロイ

別マシンで動かすときは Docker 経由で。`git clone` → `docker build` → systemd user timer の流れ。

### 1. ターゲットマシンで準備

```sh
sudo pacman -S docker docker-rootless-extras git   # Arch の例。rootless 推奨
systemctl --user enable --now docker.socket
loginctl enable-linger $USER                       # 不在時もタイマー動くように
```

### 2. リポジトリ取得 + イメージビルド

```sh
git clone <this-repo> ~/repos/radio-notifier
cd ~/repos/radio-notifier
docker build -t radio-notifier:latest .
```

### 3. 設定とステートの置き場を用意

```sh
mkdir -p ~/.config/radio-notifier ~/.local/state/radio-notifier
# ayaka などから持ってくる場合:
#   scp ayaka:~/.config/radio-notifier/config.toml ~/.config/radio-notifier/
#   scp ayaka:~/.local/state/radio-notifier/state.json ~/.local/state/radio-notifier/  # 任意（履歴引継ぎ）
```

### 4. 動作確認

```sh
docker run --rm \
  -e TZ=Asia/Tokyo \
  -v ~/.config/radio-notifier:/config/radio-notifier:ro \
  -v ~/.local/state/radio-notifier:/state/radio-notifier \
  radio-notifier:latest list

docker run --rm \
  -e TZ=Asia/Tokyo \
  -v ~/.config/radio-notifier:/config/radio-notifier:ro \
  -v ~/.local/state/radio-notifier:/state/radio-notifier \
  radio-notifier:latest dry-run
```

### 5. systemd user timer に組み込む

```sh
mkdir -p ~/.config/systemd/user
cp systemd/radio-notifier.docker.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now radio-notifier.docker.timer
systemctl --user list-timers radio-notifier.docker.timer
journalctl --user -u radio-notifier.docker -f
```

### 注意

- **rootless docker / podman**: コンテナ内 root が host のユーザーにマップされるので
  `--user` を指定しない。同梱の `radio-notifier.docker.service` はこの前提。
- **rootful docker**: bind mount のファイルが root 所有になってしまうので、
  `radio-notifier.docker.service` の `ExecStart` に `--user %U:%G` を足す。
- ホスト側 `~/.local/state/radio-notifier/state.json` が翌週以降の重複通知防止に
  使われるので、再構築時は消さない。

## 設計メモ

- 状態は `~/.local/state/radio-notifier/state.json`（番組 ID ごとに `last_video_id`, `last_notified_at`）
- 木曜は「未通知の新着がある中で、最終通知が最も古いチャンネル」を選ぶ
- メンバー限定動画は YouTube 公開 RSS には本来含まれないが、保険でタイトル/説明のキーワードフィルタを通す
