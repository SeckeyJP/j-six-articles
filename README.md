# J-SIX Articles

J-SIX プロジェクトの Qiita / Zenn 記事を管理するリポジトリです。

## 仕組み

- 記事は **Zenn CLI 形式**（`articles/` 配下の Markdown）で執筆
- `main` ブランチに push すると **GitHub Actions** が自動で：
  - Zenn に記事を公開
  - Qiita 形式に変換して Qiita にも同時公開
- 変換には [zenn-qiita-sync](https://github.com/C-Naoki/zenn-qiita-sync) を使用

## ディレクトリ構成

```
.
├── .github/workflows/
│   └── publish.yml          # Zenn/Qiita 同時公開 Workflow
├── articles/                # Zenn 形式の記事（ここで執筆）
│   ├── j-six-00-overview.md
│   ├── j-six-01-sdd.md
│   ├── ...
├── images/                  # 記事で使用する画像
├── qiita/public/            # Qiita 形式（自動生成・手動編集不要）
└── package.json             # Zenn CLI 用
```

## セットアップ

### 1. Zenn CLI インストール

```bash
npm install
```

### 2. 記事の作成

```bash
npx zenn new:article --slug j-six-00-overview --title "J-SIX — Claude Code で日本のSI開発プロセスを再定義する"
```

### 3. プレビュー

```bash
npx zenn preview
```

ブラウザで `http://localhost:8000` を開いてプレビューを確認。

### 4. 公開

```bash
git add -A
git commit -m "記事を追加: J-SIX 概要編"
git push origin main
```

push すると GitHub Actions が Zenn / Qiita に自動公開します。

## 事前設定（初回のみ）

### Zenn 連携

1. [Zenn](https://zenn.dev) にログイン
2. [GitHub連携](https://zenn.dev/dashboard/deploys) でこのリポジトリを連携

### Qiita 連携

1. [Qiita トークン発行](https://qiita.com/settings/tokens/new)（`read_qiita` + `write_qiita` スコープ）
2. このリポジトリの Settings > Secrets and variables > Actions で `QIITA_TOKEN` を登録

## 記事一覧

| # | slug | タイトル | 状態 |
|---|---|---|---|
| #0 | j-six-00-overview | J-SIX 概論 | 下書き |
| #1 | j-six-01-sdd | V字モデルの前提崩壊と SDD の台頭 | 予定 |
| #2 | j-six-02-3layer-doc | 3層ドキュメント戦略 | 予定 |
| #3 | j-six-03-tdd-cc | TDD × Claude Code | 予定 |
| #4 | j-six-04-claude-md | CLAUDE.md 実践ガイド | 予定 |
| #5 | j-six-05-migration | V字モデルからの段階的移行 | 予定 |

## 関連リポジトリ

- **[j-six](https://github.com/SeckeyJP/j-six)** — J-SIX プロセス本体（ドキュメント・テンプレート）

## 著者

H.Sekita
