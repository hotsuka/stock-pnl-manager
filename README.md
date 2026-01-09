# Stock P&L Manager

株式・ETF・投資信託の損益管理アプリケーション

## 概要

SBI証券の取引履歴CSVを基に、保有銘柄の損益を自動計算・可視化するWebアプリケーションです。

## 機能

- SBI証券取引履歴のCSVインポート
- 未実現損益・確定損益の自動計算
- 配当データの取得と管理
- 損益推移のグラフ表示（日次・月次）
- ポートフォリオ構成の可視化
- 株式評価指標の表示（時価総額、PER、PBR、Beta等12種類）
- リターン指標の自動計算（YTD、1年リターン）
- タブUIによる情報切替表示

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

### 完了済み Phase

- [x] **Phase 0: 開発環境準備**
  - Python 3.14, Flask 3.0環境構築
  - 依存パッケージのセットアップ

- [x] **Phase 1: プロジェクト基盤構築**
  - Flaskアプリケーション構造の設計
  - Blueprint、サービス層の実装

- [x] **Phase 2: データベース実装**
  - SQLiteデータベースのスキーマ設計
  - Transaction, Holding, Dividend, RealizedPnLモデルの実装

- [x] **Phase 3: CSV取り込み機能**
  - SBI証券CSVパーサーの実装
  - 取引データの自動インポート機能

- [x] **Phase 4: データ取得機能**
  - yfinanceを使った株価データの取得
  - 為替レート（USD/JPY, KRW/JPY）の自動更新
  - 配当データの取得と管理

- [x] **Phase 5: 損益計算エンジン**
  - 平均取得単価の計算（加重平均法）
  - 未実現損益の計算（保有銘柄）
  - 実現損益の計算（売却済み銘柄）
  - 配当金の集計機能

- [x] **Phase 6: REST API実装**
  - 保有銘柄API (`/api/holdings`)
  - 取引履歴API (`/api/transactions`)
  - 実現損益API (`/api/realized-pnl`)
  - 配当金API (`/api/dividends`)
  - 株価更新API (`/api/stock-price/update-all`)
  - 損益推移API (`/api/performance/history`)
  - 損益詳細API (`/api/performance/detail`)

- [x] **Phase 7: フロントエンド実装（基本機能）**
  - ダッシュボードページ（サマリー表示）
  - 保有銘柄ページ（一覧・詳細表示）
  - 取引履歴ページ（検索・フィルタ機能）
  - 実現損益ページ（売却済み銘柄の損益）
  - 配当金ページ（配当履歴の表示）
  - レスポンシブデザイン（Bootstrap 5）

- [x] **Phase 8: グラフ・可視化**
  - Plotly.jsによる損益推移グラフ
  - 日次・月次の損益チャート
  - 保有損益・実現損益・配当金の分類表示
  - インタラクティブな詳細ブレークダウン機能
  - ポートフォリオ構成の視覚化

- [x] **Phase 9: 機能強化・バグ修正**
  - [x] 為替換算ロジックの修正（日本株が米ドル扱いされるバグの解消）
  - [x] 損益詳細ブレークダウン機能（日次損益の銘柄別内訳表示）
  - [x] 取引データ編集機能（履歴の個別修正とバリデーション）
  - [x] ユニットテストの実装（モデル層100%カバレッジ達成）
  - [x] パフォーマンス最適化（データベースインデックス、バッチ処理）
  - [x] エラーハンドリングの強化（カスタムエラークラス、ロギング、バリデーション）
  - [x] 損益推移ページのパフォーマンス最適化（sessionStorageキャッシュ、遅延ロード）

- [x] **Phase 10: 株式評価指標表示機能**
  - [x] StockMetricsモデルの実装（12種類の財務指標）
  - [x] Yahoo Financeからの評価指標取得（時価総額、PER、PBR等）
  - [x] YTD・1年リターンの自動計算
  - [x] タブUIによる切替表示（基本情報・評価指標）
  - [x] 日次キャッシュ機能と遅延ロード
  - [x] 株価更新との自動連携
  - [x] ユニットテスト実装（5件全てpass）

### 今後の予定

- [ ] **Phase 11: 高度な分析機能**
  - [ ] セクター別分析
  - [ ] リスク指標の計算（シャープレシオ、ボラティリティ）
  - [ ] ベンチマーク比較機能

- [ ] **Phase 12: ドキュメント・デプロイ**
  - [ ] APIドキュメントの整備
  - [ ] ユーザーガイドの作成
  - [ ] Dockerコンテナ化
  - [ ] 本番環境デプロイ手順の確立

## ライセンス

MIT License

## 作成者

Generated with Claude Code
