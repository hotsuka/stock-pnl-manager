# Stock P&L Manager - フォルダ構成

## ルートディレクトリ
\`\`\`
stock-pnl-manager/
├── .github/workflows/      # CI/CD設定
│   ├── test.yml           # 自動テスト
│   └── docker.yml         # Docker自動ビルド
├── app/                   # アプリケーション本体
│   ├── models/           # データモデル
│   ├── routes/           # ルーティング
│   ├── services/         # ビジネスロジック
│   ├── templates/        # HTMLテンプレート
│   └── utils/            # ユーティリティ
├── data/                  # データファイル（.gitignoreで除外）
│   ├── sample_transactions.csv
│   ├── sample_transactions_en.csv
│   └── uploads/          # CSVアップロード先
├── docs/                  # ドキュメント
│   ├── dev/              # 開発履歴ドキュメント
│   ├── API_REFERENCE.md  # API仕様書
│   ├── DEPLOYMENT.md     # デプロイガイド
│   ├── DEVELOPER_GUIDE.md # 開発者ガイド
│   ├── FAQ.md            # よくある質問
│   ├── MONITORING.md     # 監視ガイド
│   ├── USER_GUIDE.md     # ユーザーマニュアル
│   ├── openapi.yaml      # OpenAPI仕様
│   └── README.md         # ドキュメント目次
├── migrations/            # データベースマイグレーション
│   └── versions/         # マイグレーションファイル
├── scripts/               # 運用スクリプト
│   ├── backup_database.py      # バックアップ
│   ├── cleanup_old_data.py     # クリーンアップ
│   ├── init_db.py              # DB初期化
│   ├── recalculate_all.py      # 再計算
│   ├── restore_database.py     # リストア
│   ├── start_production.bat    # 起動（Windows）
│   ├── start_production.sh     # 起動（Linux/macOS）
│   ├── update_all_data.py      # 全データ更新
│   ├── update_dividends.py     # 配当更新
│   ├── update_metrics_returns.py # 評価指標更新
│   ├── update_prices_manual.py # 株価更新
│   └── README.md               # スクリプト説明
├── tests/                 # テストコード
│   ├── test_api.py
│   ├── test_models.py
│   ├── test_services.py
│   └── conftest.py
├── .dockerignore          # Dockerビルド除外設定
├── .env.example           # 環境変数サンプル
├── .gitignore             # Git除外設定
├── config.py              # アプリケーション設定
├── DOCKER.md              # Docker利用ガイド
├── docker-compose.yml     # Docker開発環境
├── docker-compose.prod.yml # Docker本番環境
├── Dockerfile             # Dockerイメージ定義
├── pytest.ini             # pytest設定
├── README.md              # プロジェクト概要
├── requirements.txt       # 依存パッケージ
└── run.py                 # アプリケーション起動
\`\`\`

## 除外されるディレクトリ（.gitignoreで除外）
- \`venv/\` - Python仮想環境
- \`__pycache__/\` - Pythonキャッシュ
- \`data/*.db\` - データベースファイル
- \`logs/\` - ログファイル
- \`backups/\` - バックアップファイル
- \`.pytest_cache/\` - pytestキャッシュ

## 本番デプロイ時に必要なファイル
- \`app/\` - アプリケーション本体（必須）
- \`migrations/\` - DBマイグレーション（必須）
- \`config.py\` - 設定ファイル（必須）
- \`requirements.txt\` - 依存パッケージ（必須）
- \`run.py\` - 起動スクリプト（必須）
- \`.env\` - 環境変数（本番環境で作成）

## 本番デプロイ時に不要なファイル
- \`tests/\` - テストコード（オプション）
- \`docs/dev/\` - 開発履歴ドキュメント
- \`pytest.ini\` - pytest設定
