# 運用サーバーへの radio-notifier デプロイ指示書

このリポジトリ (https://github.com/nananek/radio-notifier) を本機にデプロイし、平日 11:30 JST に Discord 通知を送る systemd user timer を組むためのチェックリスト。Claude Code が本機（デプロイ先）で読み、上から順に実行することを想定しています。

## 前提

- Linux + systemd
- インターネット接続あり
- 開発機 `ayaka` (`ayaka.tail2c8c7.ts.net`, Tailscale) から `config.toml` と `state.json` を `scp` で持ってこられる
- sudo が使える

## ゴール

`systemctl --user list-timers radio-notifier.docker.timer` で次回発火時刻が「次の平日 11:30 (Asia/Tokyo)」に表示される状態にすること。発火すると Docker コンテナ内で `python -m radio_notifier run` が動き、Discord webhook に当日の番組（YouTube / radiko / QloveR）の URL を embed として投稿する。

## やること

### 1. Docker (rootless 推奨) と git を入れる

Arch:
```sh
sudo pacman -Syu --needed docker docker-rootless-extras git
systemctl --user enable --now docker.socket
loginctl enable-linger $USER
```

Debian / Ubuntu:
```sh
sudo apt update
sudo apt install -y docker.io docker-ce-rootless-extras git uidmap
dockerd-rootless-setuptool.sh install
systemctl --user enable --now docker.socket
sudo loginctl enable-linger $USER
```

確認:
```sh
docker info 2>&1 | grep -iE 'rootless|root dir'
# Rootless と /home/$USER/.local/share/docker が見えれば OK
```

> **rootless / rootful の差**: 同梱の `radio-notifier.docker.service` は rootless 前提（コンテナ内 root が host のユーザーにマップされるので `--user` を渡さない）。**rootful docker を使う場合は手順 6 で `--user %U:%G` を `ExecStart` に追加してください**。

### 2. リポジトリを clone してイメージをビルド

```sh
git clone https://github.com/nananek/radio-notifier ~/repos/radio-notifier
cd ~/repos/radio-notifier
docker build -t radio-notifier:latest .
docker images radio-notifier
```

### 3. ayaka から `config.toml` と `state.json` を持ってくる

```sh
mkdir -p ~/.config/radio-notifier ~/.local/state/radio-notifier
scp ayaka.tail2c8c7.ts.net:~/.config/radio-notifier/config.toml ~/.config/radio-notifier/
scp ayaka.tail2c8c7.ts.net:~/.local/state/radio-notifier/state.json ~/.local/state/radio-notifier/ || true
chmod 600 ~/.config/radio-notifier/config.toml
```

- `state.json` はあれば翌週以降の重複通知を防ぐ用途。なくても初回から動く（最初の数日間は「未通知扱い」で当日の最新動画を 1 本送る）。
- `config.toml` には **Discord webhook URL が含まれる**。git / pastebin / 公開 Slack 等に絶対に出さないこと。

### 4. コンテナ単体で動作確認

各曜日の `dry-run` を流して、想定の番組が出ることを確認:

```sh
for d in 2026-06-01 2026-06-02 2026-06-03 2026-06-04 2026-06-05; do
  echo "=== $d ==="
  docker run --rm -e TZ=Asia/Tokyo \
    -v ~/.config/radio-notifier:/config/radio-notifier:ro \
    -v ~/.local/state/radio-notifier:/state/radio-notifier \
    radio-notifier:latest dry-run --date $d
done
```

期待結果:
- 月 (06-01): 鈴原希実の明日はなんしちょっと?
- 火 (06-02): radiko タイムフリー URL + QloveR の番組ページ
- 水 (06-03): #ゆいしょ！ 〜小倉唯といっしょ！〜
- 木 (06-04): ゆうきとねき / ことのはNOTE / ゆうひかく のうちどれか1つ（`last_notified_at` が最も古いチャンネル）
- 金 (06-05): 伊藤真の元気が出る憲法アップデート

「未通知の新着なし」の場合は `no picks` と出る。`state.json` を持ち込んでいる場合は通常そうなる。**何も出ない曜日があっても異常ではない**。

### 5. Discord に実際の投稿テスト (任意)

ayaka 側ですでに金曜の伊藤塾は通知済み (`state.json` の `fri-itoh.last_video_id`) なので、`run` を流しても重複しない。動作確認のために実投稿したい場合:

```sh
# 一時的に state を退避して 1 日分強制発火
mv ~/.local/state/radio-notifier/state.json ~/.local/state/radio-notifier/state.json.bak
docker run --rm -e TZ=Asia/Tokyo \
  -v ~/.config/radio-notifier:/config/radio-notifier:ro \
  -v ~/.local/state/radio-notifier:/state/radio-notifier \
  radio-notifier:latest run
# Discord で届いたことを確認したら元に戻す
mv ~/.local/state/radio-notifier/state.json.bak ~/.local/state/radio-notifier/state.json
```

### 6. systemd user timer を仕込む

```sh
mkdir -p ~/.config/systemd/user
cp systemd/radio-notifier.docker.{service,timer} ~/.config/systemd/user/
```

**rootful docker を使う場合のみ** `~/.config/systemd/user/radio-notifier.docker.service` の `ExecStart` 行に `--user %U:%G` を追加（rootless ならそのまま）。

```sh
systemctl --user daemon-reload
systemctl --user enable --now radio-notifier.docker.timer
systemctl --user list-timers radio-notifier.docker.timer
```

### 7. 最終確認

```sh
# 次回発火が「次の平日 11:30 (Asia/Tokyo)」になっているか
systemctl --user list-timers radio-notifier.docker.timer

# 手動発火させて pipeline が通ることを確認
systemctl --user start radio-notifier.docker.service
journalctl --user -u radio-notifier.docker --since "1 minute ago"
# "INFO radio_notifier: done" まで出れば成功
```

### 8. ayaka 側の timer を無効化

二重発火を避けるため、ayaka 側に同名のサービスを enable していないことを確認:
```sh
ssh ayaka.tail2c8c7.ts.net 'systemctl --user list-timers | grep radio-notifier'
# 何も返ってこなければ OK
```

## トラブルシュート

| 症状 | 確認すること |
| --- | --- |
| `PermissionError: ... state.json` | rootless docker なら `--user` を **外す**。rootful なら `--user %U:%G` を **入れる** |
| `config file not found` | `~/.config/radio-notifier/config.toml` が存在するか、bind mount path が `/config/radio-notifier` に出ているか |
| `discord.webhook_url is required` | config.toml の `[discord] webhook_url` が `REPLACE_ME` のままになっていないか |
| YouTube fetch が空 | チャンネル ID 変更や title_filter のミスマッチ。`docker run ... dry-run -v` で詳細を |
| timer が動かない | `loginctl show-user $USER --property=Linger` が `yes` か。`systemctl --user status radio-notifier.docker.timer` |
| Discord に同じ動画が二回 | 別の host (ayaka など) で timer が同時 enable されていないか |

## アーキテクチャ要点

詳しくは README.md と src/ 配下を参照。要点だけ:

- 番組構成 (曜日割り当て / 木曜ローテーション / タイトルフィルタ) は `config.toml` で完結。コードを触らずに番組を増減できる
- 木曜の「3つから1本選ぶ」は `rotation_group = "thursday"` というラベルでグループ化しているだけで、`"thursday"` は単なる文字列。任意のラベルで任意の曜日にローテーションを組める
- 状態は `~/.local/state/radio-notifier/state.json` の 1 ファイル。番組 ID ごとに `last_video_id` と `last_notified_at` を保持。同じ動画は二度送らない
- メンバー限定動画は YouTube の公開 RSS には原則含まれないが、`src/radio_notifier/filters.py` でタイトル / 説明のキーワードによる二重チェックをかけている
