import { SurfaceTile } from "@/components/ui/primitives";
import { isComplianceAgentOutput, type AgentScoreOutput, type ScoreResponse } from "@/lib/scoring";

function scoringAgentRows(response: ScoreResponse): Array<{ title: string; detail: string; delta: string; tone: "positive" | "neutral" }> {
  const entries = Object.entries(response.agent_outputs).filter(([, output]) => !isComplianceAgentOutput(output));
  return entries.map(([name, output]) => {
    const scoreOutput = output as AgentScoreOutput;
    const title = `${name.charAt(0).toUpperCase()}${name.slice(1)} agent assessed`;
    const detail = `Score ${scoreOutput.score}/100 • confidence ${scoreOutput.confidence}`;
    const delta = `${scoreOutput.score >= 75 ? "+" : scoreOutput.score >= 50 ? "~" : "-"} ${scoreOutput.score} pts`;
    const tone: "positive" | "neutral" = scoreOutput.score >= 75 ? "positive" : "neutral";
    return { title, detail, delta, tone };
  });
}

export function RecentActivity({ response }: { response: ScoreResponse }) {
  const agentActivities = scoringAgentRows(response);
  const flagActivities = response.rbi_flags.slice(0, 2).map((flag) => ({
    title: "Compliance alert generated",
    detail: flag,
    delta: "- review",
    tone: "neutral" as const
  }));
  const items = [...agentActivities, ...flagActivities];

  return (
    <SurfaceTile className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-bold text-white">Recent Activity Signal</h3>
      </div>

      <div className="space-y-3">
        {items.length ? (
          items.map((item, index) => (
            <div key={`${item.title}-${index}`} className="flex items-center justify-between p-4 rounded-xl bg-slate-800/40">
              <div>
                <p className="text-sm font-semibold text-white">{item.title}</p>
                <p className="text-xs text-slate-400">{item.detail}</p>
              </div>
              <p className={`text-sm font-bold ${item.tone === "positive" ? "text-emerald-400" : "text-amber-300"}`}>{item.delta}</p>
            </div>
          ))
        ) : (
          <div className="p-4 rounded-xl bg-slate-800/40">
            <p className="text-sm text-slate-300">No recent backend activity was emitted for this assessment.</p>
          </div>
        )}
      </div>
    </SurfaceTile>
  );
}
