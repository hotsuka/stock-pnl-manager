"""セクター構成分析サービス

保有銘柄の現状セクター比率と、stock_analyzer Stage A の
マクロ・セクターローテーション分析結果を突き合わせて、
トップダウンのリバランス提案を生成する。

主要ロジック:
1. holdings を GICS セクターでグルーピング → 現状ウエイト算出
2. Stage A 結果（bullish/bearish_sectors, macro_sentiment）を読み込み
3. 動的ターゲット = S&P500 ベースライン ± Stage A tilt
   - bullish_sectors: +5%
   - bearish_sectors: -3%
4. delta = current - target
5. action 判定:
   - delta > +3%: DECREASE（オーバーウエイト圧縮）
   - delta < -3%: INCREASE（アンダーウエイト拡大）
   - それ以外: HOLD
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.models.holding import Holding
from app.models.stock_metrics import StockMetrics
from app.services.sector_mapping import (
    ETF_CATEGORY,
    GICS_SECTORS,
    SP500_SECTOR_WEIGHTS,
)
from app.services.stage_a_reader import StageAReader, StageAResult

logger = logging.getLogger(__name__)

# 提案発火しきい値（current vs target の乖離が ±この値%以上で INCREASE/DECREASE）
TILT_THRESHOLD_PCT = 3.0

# Stage A に応じた tilt 量
BULLISH_TILT_PCT = 5.0
BEARISH_TILT_PCT = -3.0

# 未マッピング（StockMetrics にセクター無しまたは GICS マッピング失敗）の集約先
UNMAPPED_LABEL = "未分類"


# ──────────────────────────────────────────────
# データクラス
# ──────────────────────────────────────────────


@dataclass
class SectorPosition:
    """セクター単位の現状・目標・乖離"""

    sector: str  # GICS セクター名 or "Index/ETF" or "未分類"
    current_weight_pct: float  # 現状の構成比率（%）
    target_weight_pct: float  # 動的ターゲット比率（%）
    delta_pct: float  # current - target
    holdings_value_jpy: float  # セクター内合計評価額（JPY）
    holding_tickers: List[str]  # 該当ティッカー一覧
    direction_signal: str  # "BULLISH" / "BEARISH" / "NEUTRAL"


@dataclass
class TopDownProposal:
    """セクター単位のリバランス提案"""

    sector: str
    action: str  # "INCREASE" / "DECREASE" / "HOLD"
    delta_pct: float  # 推奨調整幅（target - current の絶対値）
    current_weight_pct: float
    target_weight_pct: float
    rationale: str  # 根拠文
    candidate_holding_tickers: List[
        str
    ]  # 減らすなら保有銘柄、増やすなら ETF/screener候補
    direction_signal: str


@dataclass
class SectorAnalysisResult:
    """セクター構成分析の最終結果"""

    available: bool  # Stage A データ取得可否
    week_end: Optional[str] = None  # Stage A の参照週
    macro_sentiment: Optional[str] = None  # "強気"/"中立"/"弱気"
    macro_score: Optional[int] = None  # 0-100
    bullish_sectors: List[str] = field(default_factory=list)
    bearish_sectors: List[str] = field(default_factory=list)
    positions: List[SectorPosition] = field(default_factory=list)
    top_down_proposals: List[TopDownProposal] = field(default_factory=list)
    total_value_jpy: float = 0.0
    note: Optional[str] = None  # データ欠落時のメッセージ


# ──────────────────────────────────────────────
# サービス本体
# ──────────────────────────────────────────────


class SectorCompositionService:

    def __init__(self, stage_a_reader: StageAReader):
        self.stage_a_reader = stage_a_reader

    def analyze(self, holdings: Optional[List[Holding]] = None) -> SectorAnalysisResult:
        """セクター構成分析を実行する。

        Args:
            holdings: 保有銘柄リスト。None の場合は DB から取得。

        Returns:
            SectorAnalysisResult
        """
        if holdings is None:
            holdings = Holding.query.filter(Holding.total_quantity > 0).all()

        if not holdings:
            return SectorAnalysisResult(
                available=False,
                note="保有銘柄がありません",
            )

        # 1. 各銘柄のセクター情報を取得
        tickers = [h.ticker_symbol for h in holdings]
        metrics_map: Dict[str, StockMetrics] = {
            m.ticker_symbol: m
            for m in StockMetrics.query.filter(
                StockMetrics.ticker_symbol.in_(tickers)
            ).all()
        }

        # 2. セクター別に集計
        sector_groups: Dict[str, Dict] = {}
        total_value = 0.0
        for h in holdings:
            value = float(h.current_value) if h.current_value else 0.0
            total_value += value

            m = metrics_map.get(h.ticker_symbol)
            sector = m.sector if m and m.sector else UNMAPPED_LABEL
            grp = sector_groups.setdefault(sector, {"value": 0.0, "tickers": []})
            grp["value"] += value
            grp["tickers"].append(h.ticker_symbol)

        if total_value <= 0:
            return SectorAnalysisResult(
                available=False,
                note="ポートフォリオ評価額が 0 です（株価未取得の可能性）",
            )

        # 3. Stage A 結果を取得
        stage_a = self.stage_a_reader.get_latest()
        if stage_a is None:
            # Stage A データが無い場合: positions だけ返し、提案はなし
            positions = self._build_positions_no_stage_a(sector_groups, total_value)
            return SectorAnalysisResult(
                available=False,
                positions=positions,
                total_value_jpy=total_value,
                note="Stage A 分析結果が見つかりません。stock_analyzer の weekly モードを実行してください。",
            )

        # 4. 各セクターの target を算出（ベースライン + Stage A tilt）
        bullish = set(stage_a.bullish_sectors)
        bearish = set(stage_a.bearish_sectors)

        # GICSセクター + 実際に保有しているセクター（ETF/未分類含む）の和集合を全分析対象に
        all_sectors = set(GICS_SECTORS) | set(sector_groups.keys())

        positions: List[SectorPosition] = []
        for sector in sorted(all_sectors):
            grp = sector_groups.get(sector, {"value": 0.0, "tickers": []})
            cur_w = grp["value"] / total_value * 100.0

            # ターゲット算出
            base = SP500_SECTOR_WEIGHTS.get(sector, 0.0)
            tilt = 0.0
            direction = "NEUTRAL"
            if sector in bullish:
                tilt = BULLISH_TILT_PCT
                direction = "BULLISH"
            elif sector in bearish:
                tilt = BEARISH_TILT_PCT
                direction = "BEARISH"

            target_w = max(0.0, base + tilt)

            # 全く保有していないセクターは Stage A シグナルがない場合スキップ
            # （ただし bullish なセクターは「新規組入候補」として残す）
            if cur_w == 0 and direction == "NEUTRAL":
                continue
            # ETF/未分類カテゴリで Stage A シグナルなしならスキップ可（情報量少）
            if sector in (ETF_CATEGORY, UNMAPPED_LABEL) and direction == "NEUTRAL":
                # ETF/未分類は target 0 として保有比率だけ見せる
                target_w = 0.0

            positions.append(
                SectorPosition(
                    sector=sector,
                    current_weight_pct=round(cur_w, 2),
                    target_weight_pct=round(target_w, 2),
                    delta_pct=round(cur_w - target_w, 2),
                    holdings_value_jpy=round(grp["value"], 0),
                    holding_tickers=grp["tickers"],
                    direction_signal=direction,
                )
            )

        # 5. トップダウン提案を生成
        proposals = self._build_proposals(positions, stage_a)

        return SectorAnalysisResult(
            available=True,
            week_end=stage_a.week_end,
            macro_sentiment=stage_a.macro_sentiment,
            macro_score=stage_a.macro_score,
            bullish_sectors=stage_a.bullish_sectors,
            bearish_sectors=stage_a.bearish_sectors,
            positions=sorted(positions, key=lambda p: -p.current_weight_pct),
            top_down_proposals=proposals,
            total_value_jpy=round(total_value, 0),
        )

    # ──────────────────────────────────────────
    def _build_positions_no_stage_a(
        self, sector_groups: Dict, total_value: float
    ) -> List[SectorPosition]:
        """Stage A データ無しの場合のポジション一覧（情報表示のみ）"""
        positions = []
        for sector, grp in sector_groups.items():
            cur_w = grp["value"] / total_value * 100.0
            base = SP500_SECTOR_WEIGHTS.get(sector, 0.0)
            positions.append(
                SectorPosition(
                    sector=sector,
                    current_weight_pct=round(cur_w, 2),
                    target_weight_pct=round(base, 2),
                    delta_pct=round(cur_w - base, 2),
                    holdings_value_jpy=round(grp["value"], 0),
                    holding_tickers=grp["tickers"],
                    direction_signal="NEUTRAL",
                )
            )
        return sorted(positions, key=lambda p: -p.current_weight_pct)

    def _build_proposals(
        self, positions: List[SectorPosition], stage_a: StageAResult
    ) -> List[TopDownProposal]:
        """ポジション一覧から TopDownProposal を生成"""
        # Stage A の reason を セクター単位の根拠として使う
        reasons_by_gics: Dict[str, str] = {}
        for sig in stage_a.sector_signals:
            if sig.gics_sector and sig.gics_sector not in reasons_by_gics:
                reasons_by_gics[sig.gics_sector] = sig.reason

        proposals: List[TopDownProposal] = []
        for p in positions:
            # ETF/未分類は提案対象外
            if p.sector in (ETF_CATEGORY, UNMAPPED_LABEL):
                continue

            # 判定ロジック
            action = "HOLD"
            rationale_parts = []

            if p.direction_signal == "BULLISH":
                if p.delta_pct < -TILT_THRESHOLD_PCT:
                    action = "INCREASE"
                    rationale_parts.append(
                        f"Stage A 強気シグナル + 現状 {p.current_weight_pct:.1f}% は目標 {p.target_weight_pct:.1f}% を {abs(p.delta_pct):.1f}pt 下回る"
                    )
                elif p.delta_pct > TILT_THRESHOLD_PCT:
                    action = "HOLD"
                    rationale_parts.append(
                        f"強気セクターで既に十分なエクスポージャー（{p.current_weight_pct:.1f}%）"
                    )
                else:
                    action = "HOLD"
                    rationale_parts.append("強気セクターで概ね目標水準")
            elif p.direction_signal == "BEARISH":
                if p.delta_pct > TILT_THRESHOLD_PCT:
                    action = "DECREASE"
                    rationale_parts.append(
                        f"Stage A 弱気シグナル + 現状 {p.current_weight_pct:.1f}% は目標 {p.target_weight_pct:.1f}% を {p.delta_pct:.1f}pt 超過"
                    )
                else:
                    action = "HOLD"
                    rationale_parts.append("弱気セクターだが既に低エクスポージャー")
            else:
                # NEUTRAL: ベースラインからの大きな乖離のみ提案
                if p.delta_pct > TILT_THRESHOLD_PCT * 2:
                    action = "DECREASE"
                    rationale_parts.append(
                        f"S&P500 ベースラインから +{p.delta_pct:.1f}pt 偏在"
                    )
                elif p.delta_pct < -TILT_THRESHOLD_PCT * 2:
                    action = "INCREASE"
                    rationale_parts.append(
                        f"S&P500 ベースラインから {p.delta_pct:.1f}pt 不足"
                    )
                else:
                    continue  # NEUTRAL かつ乖離小さい場合は提案しない

            # Stage A の reason を追加
            if p.sector in reasons_by_gics:
                rationale_parts.append(f"Stage A: {reasons_by_gics[p.sector]}")

            proposals.append(
                TopDownProposal(
                    sector=p.sector,
                    action=action,
                    delta_pct=round(abs(p.target_weight_pct - p.current_weight_pct), 2),
                    current_weight_pct=p.current_weight_pct,
                    target_weight_pct=p.target_weight_pct,
                    rationale=" / ".join(rationale_parts),
                    candidate_holding_tickers=p.holding_tickers,
                    direction_signal=p.direction_signal,
                )
            )

        # 並び順: INCREASE → DECREASE → HOLD、内側は乖離絶対値の大きい順
        action_order = {"INCREASE": 0, "DECREASE": 1, "HOLD": 2}
        proposals.sort(key=lambda x: (action_order.get(x.action, 99), -x.delta_pct))
        return proposals
