#!/usr/bin/env bash
# scripts/weekly_analysis.sh
#
# 週次ポートフォリオ分析オーケストレーションスクリプト
#
# 使用例:
#   bash scripts/weekly_analysis.sh
#   bash scripts/weekly_analysis.sh --skip-screener --cash 500000
#   bash scripts/weekly_analysis.sh --preset high_dividend --cash 300000
#
# 環境変数:
#   SCREENER_PRESET: スクリーナープリセット（デフォルト: growth_value）
#   CASH_JPY: 余剰現金額（省略可能）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PNL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ANALYZER_ROOT="$(cd "${PNL_ROOT}/../stock_analyzer" && pwd)"
LOG_DIR="${PNL_ROOT}/logs"
REPORT_DIR="${PNL_ROOT}/reports"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
LOG_FILE="${LOG_DIR}/weekly_analysis_${TIMESTAMP}.log"

# デフォルト値
SKIP_SCREENER=false
SKIP_STAGE_A=false
CASH_JPY="${CASH_JPY:-}"
SCREENER_PRESET="${SCREENER_PRESET:-growth_value}"

# 引数パース
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-screener) SKIP_SCREENER=true ;;
    --skip-stage-a)  SKIP_STAGE_A=true ;;
    --cash)          CASH_JPY="$2"; shift ;;
    --preset)        SCREENER_PRESET="$2"; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

mkdir -p "${LOG_DIR}" "${REPORT_DIR}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"; }

# 利用可能な Python を決定する
# venv の .py ソースが欠損している環境では、ユーザーパッケージ入りのシステム Python を使う
find_python() {
  local root="$1"
  # venv Python でパッケージが正常にインポートできるか検証
  for candidate in \
    "${root}/venv/Scripts/python.exe" \
    "${root}/venv/Scripts/python" \
    "${root}/venv/bin/python"; do
    if [[ -f "${candidate}" ]]; then
      if "${candidate}" -c "from flask import Flask" &>/dev/null 2>&1; then
        echo "${candidate}"; return
      fi
    fi
  done
  echo "python"
}

PNL_PYTHON=$(find_python "${PNL_ROOT}")
ANALYZER_PYTHON=$(find_python "${ANALYZER_ROOT}")

log "=== 週次ポートフォリオ分析 開始 ==="
log "プリセット   : ${SCREENER_PRESET}"
log "余剰現金     : ${CASH_JPY:-未指定}"
log "screener skip: ${SKIP_SCREENER}"
log "stage_a skip : ${SKIP_STAGE_A}"

# ────────────────────────────────────────────────────────────────
# Step 0.5: stock_analyzer Stage A 実行（マクロ・セクターローテーション）
#  保有銘柄リストを stock-pnl-manager から抽出して --stocks に渡す
#  失敗時は既存の analyzer.db.weekly_reports を使う
# ────────────────────────────────────────────────────────────────
if [[ "${SKIP_STAGE_A}" == "false" ]] && [[ -d "${ANALYZER_ROOT}" ]]; then
  log "--- Step 0.5: stock_analyzer Stage A（マクロ・セクター分析） ---"
  HOLDINGS_TICKERS=$("${PNL_PYTHON}" -c "
from app import create_app
from app.models.holding import Holding
app = create_app()
with app.app_context():
    print(','.join(h.ticker_symbol for h in Holding.query.filter(Holding.total_quantity > 0).all()))
" 2>/dev/null) || HOLDINGS_TICKERS=""

  if [[ -n "${HOLDINGS_TICKERS}" ]]; then
    log "Stage A 対象銘柄: $(echo ${HOLDINGS_TICKERS} | tr ',' '\n' | wc -l) 銘柄"
    (cd "${ANALYZER_ROOT}" && \
      "${ANALYZER_PYTHON}" main.py \
        --mode weekly \
        --stocks "${HOLDINGS_TICKERS}" \
        --no-notify \
        2>&1 | tee -a "${LOG_FILE}") \
      || log "WARNING: Stage A 失敗（既存 analyzer.db で継続）"
  else
    log "WARNING: 保有銘柄取得失敗。Stage A をスキップ"
  fi
else
  log "--- Step 0.5: Stage A スキップ ---"
fi

# ────────────────────────────────────────────────────────────────
# Step 1: stock_analyzer スクリーニング実行
# ────────────────────────────────────────────────────────────────
if [[ "${SKIP_SCREENER}" == "false" ]]; then
  if [[ -d "${ANALYZER_ROOT}" ]]; then
    log "--- Step 1: stock_analyzer スクリーニング (${SCREENER_PRESET}) ---"
    (cd "${ANALYZER_ROOT}" && \
      "${ANALYZER_PYTHON}" main.py \
        --mode screen \
        --preset "${SCREENER_PRESET}" \
        2>&1 | tee -a "${LOG_FILE}") \
      || log "WARNING: screener 実行失敗（処理を継続します）"
  else
    log "WARNING: stock_analyzer が見つかりません (${ANALYZER_ROOT})"
  fi
else
  log "--- Step 1: スクリーニングスキップ ---"
fi

# ────────────────────────────────────────────────────────────────
# Step 2: stock-pnl-manager 価格・指標データ更新
# ────────────────────────────────────────────────────────────────
log "--- Step 2: 価格・指標データ更新 ---"
(cd "${PNL_ROOT}" && \
  "${PNL_PYTHON}" scripts/update_all_data.py \
    2>&1 | tee -a "${LOG_FILE}") \
  || log "WARNING: データ更新失敗（処理を継続します）"

# ────────────────────────────────────────────────────────────────
# Step 3: 週次レポート生成
# ────────────────────────────────────────────────────────────────
log "--- Step 3: 週次レポート生成 ---"
REPORT_FILE="${REPORT_DIR}/weekly_advisor_${TIMESTAMP}.html"
CASH_ARG=""
if [[ -n "${CASH_JPY}" ]]; then
  CASH_ARG="--cash ${CASH_JPY}"
fi

(cd "${PNL_ROOT}" && \
  "${PNL_PYTHON}" scripts/generate_weekly_report.py \
    --output "${REPORT_FILE}" \
    ${CASH_ARG} \
    2>&1 | tee -a "${LOG_FILE}") || {
  log "ERROR: レポート生成失敗"
  exit 1
}

log "=== 完了 ==="
log "レポート: ${REPORT_FILE}"

# ────────────────────────────────────────────────────────────────
# Step 4: ブラウザでレポートを開く（Windows Git Bash）
# ────────────────────────────────────────────────────────────────
WIN_REPORT=$(cygpath -w "${REPORT_FILE}" 2>/dev/null || echo "${REPORT_FILE}")
if command -v cmd.exe &>/dev/null 2>&1; then
  cmd.exe /c start "" "${WIN_REPORT}" 2>/dev/null || true
fi

echo ""
echo "レポートが生成されました:"
echo "  ${REPORT_FILE}"
echo ""
echo "Flaskサーバーが起動中なら http://localhost:5000/advisor/ でも確認できます。"
