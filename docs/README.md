# Stock P&L Manager - ドキュメント

このディレクトリには、Stock P&L Managerの各種ドキュメントが含まれています。

## ドキュメント一覧

### ユーザー向けドキュメント

- **[USER_GUIDE.md](USER_GUIDE.md)** - ユーザーマニュアル
  - インストール方法
  - 基本操作
  - 機能説明
  - トラブルシューティング

- **[FAQ.md](FAQ.md)** - よくある質問
  - 一般的な質問
  - 技術的な質問
  - エラー対処法

### 開発者向けドキュメント

- **[API_REFERENCE.md](API_REFERENCE.md)** - API仕様書
  - 全エンドポイントの詳細
  - リクエスト/レスポンス形式
  - エラーコード一覧

- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** - 開発者ガイド
  - プロジェクト構造
  - アーキテクチャ
  - 開発環境のセットアップ
  - コントリビューション方法

- **[openapi.yaml](openapi.yaml)** - OpenAPI仕様
  - Swagger形式のAPI定義
  - Swagger UIで閲覧可能

### 運用ドキュメント

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - デプロイガイド
  - 環境構築
  - デプロイ手順
  - 本番環境設定

- **[MONITORING.md](MONITORING.md)** - 監視・運用ガイド
  - ログ管理
  - パフォーマンス監視
  - バックアップ手順

## プロジェクトルートのドキュメント

プロジェクトルートにも重要なドキュメントがあります：

- **[../README.md](../README.md)** - プロジェクト概要
- **[../DOCKER.md](../DOCKER.md)** - Docker利用ガイド
- **[../FOLDER_STRUCTURE.md](../FOLDER_STRUCTURE.md)** - フォルダ構成説明

## 開発履歴ドキュメント

各フェーズの実装詳細（`dev/`ディレクトリ）：

- **[dev/PHASE_10_STOCK_METRICS.md](dev/PHASE_10_STOCK_METRICS.md)** - 株式評価指標機能
- **[dev/PHASE_11_BENCHMARK_COMPARISON.md](dev/PHASE_11_BENCHMARK_COMPARISON.md)** - ベンチマーク比較機能
- **[dev/PHASE_12_DOCUMENTATION_DEPLOY.md](dev/PHASE_12_DOCUMENTATION_DEPLOY.md)** - Phase 12実装計画
- **[dev/PHASE_12_SUMMARY.md](dev/PHASE_12_SUMMARY.md)** - Phase 12完了サマリー
- **[dev/ERROR_HANDLING.md](dev/ERROR_HANDLING.md)** - エラーハンドリング
- **[dev/PERFORMANCE_OPTIMIZATION.md](dev/PERFORMANCE_OPTIMIZATION.md)** - パフォーマンス最適化
- その他の技術ドキュメント

## ドキュメントの更新

ドキュメントは常に最新の状態に保つよう心がけてください。

### 更新が必要な場合
- 新機能の追加時
- APIの変更時
- 重要なバグ修正時
- デプロイ手順の変更時

### 更新方法
1. 該当するドキュメントファイルを編集
2. 変更内容を明確に記述
3. 変更日時とバージョンを更新
4. Pull Requestを作成（チーム開発の場合）

## フィードバック

ドキュメントに関するフィードバックや改善提案は、GitHubのIssueで受け付けています。

---

**最終更新**: 2026-01-11
