# Stock P&L Manager

株式・ETF・投資信託の損益管理アプリケーション

## 概要

SBI証券の取引履歴CSVを基に、保有銘柄の損益を自動計算・可視化するWebアプリケーションです。

## 機能

- SBI証券取引履歴のCSVインポート
- 未実現損益・確定損益の自動計算
- 配当データの取得と管理
- 損益推移のグラフ表示
- ポートフォリオ構成の可視化
- ヒートマップによる銘柄分析

## 技術スタック

- **Backend**: Python 3.14, Flask 3.0
- **Database**: SQLite
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly
- **Financial Data**: yfinance

## セットアップ

### 1. リポジトリのクローン
```bash
git clone <repository-url>
cd stock-pnl-manager
```

### 2. 仮想環境の作成と有効化
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

### 4. 環境変数の設定
`.env`ファイルを編集して必要な環境変数を設定してください。

### 5. データベースの初期化
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 6. アプリケーションの起動
```bash
python run.py
```

ブラウザで `http://localhost:5000` にアクセスしてください。

## プロジェクト構造

```
stock-pnl-manager/
├── app/
│   ├── __init__.py           # アプリケーションファクトリ
│   ├── models/               # データモデル
│   ├── services/             # ビジネスロジック
│   ├── routes/               # ルーティング
│   ├── templates/            # HTMLテンプレート
│   ├── static/               # CSS/JS/画像
│   └── utils/                # ユーティリティ
├── tests/                    # テストコード
├── data/                     # ローカルデータ
│   └── uploads/              # CSVアップロード
├── config.py                 # 設定ファイル
├── requirements.txt          # 依存パッケージ
├── run.py                    # 起動スクリプト
└── README.md
```

## 開発状況

- [x] Phase 0: 開発環境準備
- [x] Phase 1: プロジェクト基盤構築
- [x] Phase 2: データベース実装
- [x] Phase 3: CSV取り込み機能
- [x] Phase 4: データ取得機能
- [x] Phase 5: 損益計算エンジン
- [x] Phase 6: REST API実装
- [x] Phase 7: フロントエンド実装 (基本機能)
- [/] Phase 8: グラフ・可視化
- [/] Phase 9: テスト・最適化
- [ ] Phase 10: ドキュメント・デプロイ

## ライセンス

MIT License

## 作成者

Generated with Claude Code
