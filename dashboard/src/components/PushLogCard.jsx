import React, { useState } from 'react';

export default function PushLogCard({ report }) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Field mapping with fallbacks to prevent UI crashes
  const repoName = report.repo_id || report.popup?.repo_name || 'Unknown Repository';
  const branch = report.branch || 'main';
  const outcome = report.decision || report.outcome || 'UNKNOWN';
  const commitMessage = report.popup?.commit_message || report.commit_message || 'Commit details unavailable';
  const llmSummary = report.popup?.summary || report.detailed_md || 'No AI analysis available for this push.';
  const timestamp = report.timestamp ? new Date(report.timestamp).toLocaleString() : 'Just now';

  // Styling logic based on risk decision
  const isSuccess = outcome.toLowerCase() === 'pass' || outcome === 'SUCCESS';
  const isFail = outcome.toLowerCase() === 'fail';

  const statusColor = isSuccess
    ? 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/25'
    : isFail
    ? 'bg-rose-500/10 text-rose-400 ring-rose-500/25'
    : 'bg-amber-500/10 text-amber-400 ring-amber-500/25';

  const indicatorColor = isSuccess ? 'bg-emerald-500' : isFail ? 'bg-rose-500' : 'bg-amber-500';

  const panelId = `review-${report.id ?? repoName}`;

  return (
    <article className="relative overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/50 transition-colors hover:border-zinc-700">
      {/* Side status indicator */}
      <div className={`absolute inset-y-0 left-0 w-[3px] ${indicatorColor}`} aria-hidden="true"></div>

      <div className="p-5 pl-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            {/* Commit message is the primary thing people scan for */}
            <h2 className="truncate text-base font-semibold text-white" title={commitMessage}>
              {commitMessage}
            </h2>

            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm text-zinc-400">
              <span className="inline-flex items-center gap-1.5 font-medium text-zinc-300">
                <svg className="h-4 w-4 text-zinc-500" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                {repoName}
              </span>

              <span className="inline-flex items-center gap-1.5 rounded-md border border-zinc-800 bg-zinc-950 px-2 py-0.5 font-mono text-xs text-indigo-300">
                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 3v12m0 0a3 3 0 103 3 3 3 0 00-3-3zm12-6a3 3 0 10-3-3 3 3 0 003 3zm0 0a9 9 0 01-9 9" />
                </svg>
                {branch}
              </span>

              <span className="inline-flex items-center gap-1.5 text-zinc-500">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6l4 2m5-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {timestamp}
              </span>
            </div>
          </div>

          <span
            className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold uppercase ring-1 ring-inset ${statusColor}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${indicatorColor}`}></span>
            {outcome}
          </span>
        </div>

        <button
          onClick={() => setIsExpanded(!isExpanded)}
          aria-expanded={isExpanded}
          aria-controls={panelId}
          className="mt-4 inline-flex items-center gap-1.5 rounded-md text-sm font-medium text-indigo-400 transition-colors hover:text-indigo-300"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456Z" />
          </svg>
          <span>{isExpanded ? 'Hide AI risk summary' : 'View AI risk summary'}</span>
          <svg
            className={`h-4 w-4 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
            fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {isExpanded && (
          <div id={panelId} className="mt-4 animate-reveal overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950">
            <div className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900/60 px-4 py-2.5">
              <h3 className="text-sm font-medium text-zinc-300">Multi-agent review</h3>
              <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-semibold uppercase ring-1 ring-inset ${statusColor}`}>
                {outcome}
              </span>
            </div>
            <div className="max-h-96 overflow-auto p-4">
              <pre className="whitespace-pre-wrap break-words font-mono text-[13px] leading-relaxed text-zinc-300">
                {llmSummary}
              </pre>
            </div>
          </div>
        )}
      </div>
    </article>
  );
}
