#!/usr/bin/env python
"""週次ポートフォリオレポートをスタンドアロンで生成するスクリプト。

使用法:
    python scripts/generate_weekly_report.py --output reports/report.html
    python scripts/generate_weekly_report.py --output reports/report.html --cash 500000
"""
import argparse
import sys
from pathlib import Path

# プロジェクトルートを sys.path に追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.services.portfolio_advisor_service import PortfolioAdvisorService
from app.services.weekly_review_service import WeeklyReviewService


def build_html(review, advisor) -> str:
    def fmt_pct(v):
        if v is None:
            return "--"
        sign = "+" if v > 0 else ""
        color = "#198754" if v > 0 else ("#dc3545" if v < 0 else "#6c757d")
        return f'<span style="color:{color};font-weight:600">{sign}{v:.2f}%</span>'

    def fmt_jpy(v):
        if v is None:
            return "--"
        return f"¥{int(v):,}"

    def grade_color(g):
        return {"A": "#198754", "B": "#0d6efd", "C": "#6c757d"}.get(g or "C", "#6c757d")

    def quality_color(q):
        return {"Good": "#198754", "Watch": "#ffc107", "要検討": "#dc3545"}.get(
            q, "#6c757d"
        )

    # ── ヘッダー ──────────────────────────────────────────────────
    html_parts = [
        f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>週次ポートフォリオレポート {review.week_end}</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; max-width: 1100px; margin: 0 auto; padding: 20px; color: #333; }}
  h1 {{ color: #0d6efd; border-bottom: 2px solid #0d6efd; padding-bottom: 8px; }}
  h2 {{ color: #495057; margin-top: 2rem; }}
  table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
  th {{ background: #f8f9fa; padding: 8px 12px; text-align: left; border-bottom: 2px solid #dee2e6; font-size: 13px; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #dee2e6; font-size: 13px; }}
  tr:hover td {{ background: #f8f9fa; }}
  .card {{ background: #fff; border: 1px solid #dee2e6; border-radius: 8px; padding: 16px; margin: 8px 0; }}
  .cards {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 1rem 0; }}
  .card-sm {{ flex: 1; min-width: 160px; text-align: center; }}
  .card-sm .label {{ font-size: 12px; color: #6c757d; }}
  .card-sm .value {{ font-size: 24px; font-weight: 700; margin-top: 4px; }}
  .badge {{ padding: 3px 8px; border-radius: 4px; color: #fff; font-size: 12px; font-weight: 600; }}
  .proposal {{ border-left: 4px solid #0d6efd; padding: 12px 16px; margin: 8px 0; background: #f8f9fa; border-radius: 4px; }}
  .proposal.increase {{ border-left-color: #198754; }}
  .proposal.decrease {{ border-left-color: #dc3545; }}
  .proposal.hold {{ border-left-color: #6c757d; }}
  .warn {{ background: #fff3cd; border: 1px solid #ffc107; border-radius: 4px; padding: 8px 12px; margin: 4px 0; font-size: 12px; }}
  .macro-banner {{ background: linear-gradient(135deg, #e7f3ff 0%, #f0f8ff 100%); border-left: 4px solid #0d6efd; padding: 14px 18px; margin: 8px 0 16px; border-radius: 6px; }}
  .macro-banner .sentiment {{ font-size: 18px; font-weight: 700; }}
  .sent-bullish {{ color: #198754; }}
  .sent-bearish {{ color: #dc3545; }}
  .sent-neutral {{ color: #6c757d; }}
  .delta-pos {{ color: #dc3545; font-weight: 600; }}
  .delta-neg {{ color: #198754; font-weight: 600; }}
  .delta-zero {{ color: #6c757d; }}
  .text-end {{ text-align: right; }}
  footer {{ margin-top: 3rem; border-top: 1px solid #dee2e6; padding-top: 8px; font-size: 12px; color: #6c757d; }}
</style>
</head>
<body>
<h1>週次ポートフォリオレポート</h1>
<p>集計期間: {review.week_start} ～ {review.week_end} ／ 生成: {review.generated_at[:16]}</p>
"""
    ]

    # ── サマリーカード ─────────────────────────────────────────
    html_parts.append('<div class="cards">')
    html_parts.append(
        f'<div class="card card-sm"><div class="label">週間リターン</div><div class="value">{fmt_pct(review.portfolio_week_return_pct)}</div></div>'
    )
    html_parts.append(
        f'<div class="card card-sm"><div class="label">対TOPIX α</div><div class="value">{fmt_pct(review.alpha_vs_topix)}</div></div>'
    )
    html_parts.append(
        f'<div class="card card-sm"><div class="label">対S&P500 α</div><div class="value">{fmt_pct(review.alpha_vs_sp500)}</div></div>'
    )
    html_parts.append(
        f'<div class="card card-sm"><div class="label">PF評価額</div><div class="value" style="font-size:18px">{fmt_jpy(review.total_portfolio_value_jpy)}</div></div>'
    )
    html_parts.append(
        f'<div class="card card-sm"><div class="label">週間確定損益</div><div class="value" style="font-size:18px">{fmt_jpy(review.weekly_realized_pnl)}</div></div>'
    )
    html_parts.append(
        f'<div class="card card-sm"><div class="label">週間配当収入</div><div class="value" style="font-size:18px">{fmt_jpy(review.weekly_dividend_income)}</div></div>'
    )
    html_parts.append("</div>")

    # ── ベンチマーク比較 ────────────────────────────────────────
    html_parts.append(
        '<h2>ベンチマーク比較</h2><table><tr><th>指標</th><th class="text-end">週間リターン</th></tr>'
    )
    for b in review.benchmarks:
        html_parts.append(
            f'<tr><td>{b.name}</td><td class="text-end">{fmt_pct(b.week_return_pct)}</td></tr>'
        )
    html_parts.append(
        f'<tr style="font-weight:700"><td>ポートフォリオ</td><td class="text-end">{fmt_pct(review.portfolio_week_return_pct)}</td></tr>'
    )
    html_parts.append("</table>")

    # ── 保有銘柄週間リターン ────────────────────────────────────
    html_parts.append("<h2>保有銘柄 週間リターン</h2>")
    html_parts.append(
        '<table><tr><th>銘柄</th><th class="text-end">週リターン</th><th class="text-end">PF比率</th><th class="text-end">含み損益</th><th>品質</th></tr>'
    )
    for h in review.holdings_perf:
        qcolor = quality_color(h.quality_label)
        html_parts.append(
            f"<tr><td><strong>{h.ticker_symbol}</strong> {h.security_name}</td>"
            f'<td class="text-end">{fmt_pct(h.week_return_pct)}</td>'
            f'<td class="text-end">{h.weight_pct:.1f}%</td>'
            f'<td class="text-end">{fmt_pct(h.unrealized_pnl_pct)}</td>'
            f'<td><span class="badge" style="background:{qcolor}">{h.quality_label}</span></td></tr>'
        )
    html_parts.append("</table>")

    # ── 品質チェック ────────────────────────────────────────────
    html_parts.append("<h2>品質チェック (PER / PBR / 利益率)</h2>")
    html_parts.append(
        '<table><tr><th>銘柄</th><th class="text-end">PER</th><th class="text-end">PBR</th><th class="text-end">利益率</th><th>品質</th><th>評価理由</th></tr>'
    )
    for h in review.holdings_perf:
        qcolor = quality_color(h.quality_label)
        margin_str = (
            f"{h.profit_margin * 100:.1f}%" if h.profit_margin is not None else "-"
        )
        html_parts.append(
            f"<tr><td><strong>{h.ticker_symbol}</strong></td>"
            f'<td class="text-end">{h.pe_ratio or "-"}</td>'
            f'<td class="text-end">{h.pb_ratio or "-"}</td>'
            f'<td class="text-end">{margin_str}</td>'
            f'<td><span class="badge" style="background:{qcolor}">{h.quality_label}</span></td>'
            f'<td><small>{" / ".join(h.quality_reasons)}</small></td></tr>'
        )
    html_parts.append("</table>")

    # ── マクロ環境・セクター構成分析（トップダウン） ─────────────
    sa = getattr(advisor, "sector_analysis", None)
    if sa is not None:
        html_parts.append("<h2>マクロ環境・セクター構成分析（トップダウン）</h2>")
        if not sa.available:
            note = sa.note or "Stage A 分析結果が取得できませんでした"
            html_parts.append(f'<div class="warn">⚠️ {note}</div>')
        else:
            # マクロサマリーバナー
            sent_class = (
                "sent-bullish"
                if "強気" in (sa.macro_sentiment or "")
                else (
                    "sent-bearish"
                    if "弱気" in (sa.macro_sentiment or "")
                    else "sent-neutral"
                )
            )
            html_parts.append(
                f'<div class="macro-banner">'
                f'<div class="sentiment"><span class="{sent_class}">マクロセンチメント: {sa.macro_sentiment}（{sa.macro_score}/100）</span> '
                f'<small style="color:#6c757d">／ 参照週: {sa.week_end}</small></div>'
                f'<p style="margin:6px 0 0;font-size:13px;">'
                f'<strong>強気セクター:</strong> {", ".join(sa.bullish_sectors) or "—"}<br>'
                f'<strong>弱気セクター:</strong> {", ".join(sa.bearish_sectors) or "—"}'
                f"</p></div>"
            )

            # セクター構成テーブル
            html_parts.append(
                '<h3 style="margin-top:1.5rem">セクター別構成（現状 vs 目標）</h3>'
            )
            html_parts.append(
                "<table><tr>"
                "<th>セクター</th>"
                '<th class="text-end">現状%</th>'
                '<th class="text-end">目標%</th>'
                '<th class="text-end">乖離(pt)</th>'
                "<th>シグナル</th>"
                "<th>該当銘柄</th>"
                "</tr>"
            )
            for p in sa.positions:
                # 乖離の色（プラスは過剰=赤、マイナスは不足=緑、ETFや未分類は灰）
                if p.sector in ("Index/ETF", "未分類"):
                    delta_cls = "delta-zero"
                elif p.delta_pct > 0.5:
                    delta_cls = "delta-pos"
                elif p.delta_pct < -0.5:
                    delta_cls = "delta-neg"
                else:
                    delta_cls = "delta-zero"

                sig_label = {
                    "BULLISH": '<span class="badge" style="background:#198754">強気</span>',
                    "BEARISH": '<span class="badge" style="background:#dc3545">弱気</span>',
                    "NEUTRAL": '<span style="color:#6c757d">—</span>',
                }.get(p.direction_signal, "—")

                tickers_str = ", ".join(p.holding_tickers[:6])
                if len(p.holding_tickers) > 6:
                    tickers_str += f" 他{len(p.holding_tickers) - 6}件"
                if not tickers_str:
                    tickers_str = '<span style="color:#6c757d">未保有</span>'

                html_parts.append(
                    f"<tr>"
                    f"<td><strong>{p.sector}</strong></td>"
                    f'<td class="text-end">{p.current_weight_pct:.1f}%</td>'
                    f'<td class="text-end">{p.target_weight_pct:.1f}%</td>'
                    f'<td class="text-end"><span class="{delta_cls}">{p.delta_pct:+.1f}</span></td>'
                    f"<td>{sig_label}</td>"
                    f"<td><small>{tickers_str}</small></td>"
                    f"</tr>"
                )
            html_parts.append("</table>")

            # トップダウン提案カード
            html_parts.append('<h3 style="margin-top:1.5rem">トップダウン提案</h3>')
            if not sa.top_down_proposals:
                html_parts.append(
                    '<p style="color:#6c757d">現時点でセクターレベルの大きな調整提案はありません。</p>'
                )
            else:
                action_meta = {
                    "INCREASE": ("increase", "🟢 INCREASE", "#198754"),
                    "DECREASE": ("decrease", "🔴 DECREASE", "#dc3545"),
                    "HOLD": ("hold", "⚪ HOLD", "#6c757d"),
                }
                for prop in sa.top_down_proposals:
                    cls, label, color = action_meta.get(
                        prop.action, ("hold", prop.action, "#6c757d")
                    )
                    tickers_str = (
                        ", ".join(prop.candidate_holding_tickers[:8]) or "保有銘柄なし"
                    )
                    html_parts.append(
                        f'<div class="proposal {cls}">'
                        f'<strong style="color:{color}">{label}: {prop.sector}</strong> '
                        f"<small>（現状 {prop.current_weight_pct:.1f}% → 目標 {prop.target_weight_pct:.1f}% ／ 調整幅 {prop.delta_pct:.1f}pt）</small>"
                        f"<br><small><strong>根拠:</strong> {prop.rationale}</small>"
                        f"<br><small><strong>該当保有銘柄:</strong> {tickers_str}</small>"
                        f"</div>"
                    )

    # ── 入替提案 ────────────────────────────────────────────────
    html_parts.append("<h2>入替提案</h2>")
    if advisor.warnings:
        for w in advisor.warnings:
            html_parts.append(f'<div class="warn">⚠️ {w}</div>')

    if advisor.replacement_proposals:
        for p in advisor.replacement_proposals:
            html_parts.append(
                f'<div class="proposal">'
                f"<strong>{p.sell.ticker_symbol}</strong>（スコア{p.sell.effective_score:.0f}）"
                f" → <strong>{p.buy.ticker_symbol}</strong>"
                f' <span class="badge" style="background:{grade_color(p.buy.recommendation_grade)}">{p.buy.recommendation_grade}</span>'
                f" スコア{p.buy.composite_score:.0f}"
                f' <span style="color:#198754">（+{p.score_improvement:.1f}pt改善）</span><br>'
                f"<small>{p.rationale}</small>"
                f"</div>"
            )
    else:
        html_parts.append(
            '<p style="color:#6c757d">現時点では入替提案はありません。</p>'
        )

    # ── 余剰現金投資提案 ────────────────────────────────────────
    if advisor.cash_input_jpy and advisor.cash_proposals:
        html_parts.append("<h2>余剰現金投資提案</h2>")
        html_parts.append(
            f"<p>入力現金: {fmt_jpy(advisor.cash_input_jpy)} ／ 残余現金: {fmt_jpy(advisor.remaining_cash_jpy)}</p>"
        )
        html_parts.append(
            '<table><tr><th>銘柄</th><th>グレード</th><th class="text-end">スコア</th><th>エントリー価格帯</th><th class="text-end">推奨金額</th><th class="text-end">推奨株数</th><th class="text-end">投資後比率</th></tr>'
        )
        for c in advisor.cash_proposals:
            warn = " ⚠️10%超" if c.max_position_warning else ""
            html_parts.append(
                f"<tr><td><strong>{c.ticker_symbol}</strong> {c.company_name}{warn}</td>"
                f'<td><span class="badge" style="background:{grade_color(c.recommendation_grade)}">{c.recommendation_grade}</span></td>'
                f'<td class="text-end">{c.composite_score:.0f}</td>'
                f'<td>{c.entry_price_range or "-"}</td>'
                f'<td class="text-end" style="color:#198754;font-weight:600">{fmt_jpy(c.suggested_amount_jpy)}</td>'
                f'<td class="text-end">{c.suggested_quantity}株</td>'
                f'<td class="text-end">{c.position_pct_after:.1f}%</td></tr>'
            )
        html_parts.append("</table>")

    html_parts.append(
        "<footer>Stock P&L Manager – 週次アドバイザー ／ 本レポートは参考情報であり投資助言ではありません。</footer>"
    )
    html_parts.append("</body></html>")
    return "\n".join(html_parts)


def main():
    parser = argparse.ArgumentParser(description="週次ポートフォリオレポート生成")
    parser.add_argument("--output", required=True, help="出力 HTML ファイルパス")
    parser.add_argument("--cash", type=float, default=None, help="余剰現金額（円）")
    parser.add_argument("--env", default="development", help="Flask 環境設定名")
    args = parser.parse_args()

    app = create_app(args.env)
    with app.app_context():
        print("週次振り返りデータを取得中...")
        review = WeeklyReviewService.get_weekly_review()

        screener_db = app.config.get("SCREENER_DB_PATH", "")
        print("ポートフォリオ分析中...")
        service = PortfolioAdvisorService(screener_db)
        advisor = service.analyze(cash_jpy=args.cash)

        print("HTMLレポートを生成中...")
        html = build_html(review, advisor)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
        print(f"レポート生成完了: {output_path}")

        print(f"\n--- サマリー ---")
        print(f"週間リターン : {review.portfolio_week_return_pct}%")
        print(f"対TOPIX α   : {review.alpha_vs_topix}%")
        print(f"売却候補     : {len(advisor.sell_candidates)} 件")
        print(f"入替提案     : {len(advisor.replacement_proposals)} 件")
        if args.cash:
            print(f"現金投資提案 : {len(advisor.cash_proposals)} 件")


if __name__ == "__main__":
    main()
