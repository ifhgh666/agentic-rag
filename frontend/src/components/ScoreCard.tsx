import { useId } from "react";
import type { VerificationResult } from "../types/api";

export function ScoreCard({ verification }: { verification: VerificationResult }) {
  const headingId = useId();
  const labels: Record<string, string> = { found: "已取得证据", insufficient: "证据不足", verified: "已核验", issue_found: "存在问题", not_applicable: "不适用", not_evaluated: "未评估" };
  const dimensions = [["检索证据", verification.evidence_status], ["引文定位", verification.citation_status], ["数值条件", verification.numeric_status], ["步骤完整性", verification.completeness_status]] as const;
  return <section className="verification-card panel secondary-result-card" aria-labelledby={headingId}>
    <div className="panel-heading"><div><span className="eyebrow">核验 / 状态</span><h3 id={headingId}>证据核验</h3></div><span className="subheading">仅展示实际核验项</span></div>
    <dl className="verification-grid">{dimensions.map(([name, status]) => <div key={name}><dt>{name}</dt><dd className={`verification-badge ${status}`}>{labels[status]}</dd></div>)}</dl>
    <p className="verification-reason">{verification.reason}</p>
    <p className="verification-limit">来源可定位不等于事实正确或答案完整；离线评估不在本次问答中运行。</p>
  </section>;
}
