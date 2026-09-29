import type { EvaluationResult } from "../types/api";

export function ScoreCard({ evaluation }: { evaluation: EvaluationResult }) {
  const dimensions = [["相关性", evaluation.relevance], ["忠实性", evaluation.faithfulness], ["完整性", evaluation.completeness]] as const;
  return <section className="score-card panel"><div className="score-big"><span>总体可信度</span><strong>{evaluation.overall}</strong><em>/ 100</em></div><div className="score-bars">{dimensions.map(([name, value]) => <div className="score-line" key={name}><label>{name}<b>{value}</b></label><span><i style={{ width: `${value}%` }} /></span></div>)}</div><p className="score-reason">“{evaluation.reason}”</p></section>;
}
