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
    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
    : isFail
    ? 'bg-red-500/10 text-red-400 border-red-500/20'
    : 'bg-amber-500/10 text-amber-400 border-amber-500/20';

  const indicatorColor = isSuccess ? 'bg-emerald-500' : isFail ? 'bg-red-500' : 'bg-amber-500';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-indigo-500/50 transition-all shadow-lg hover:shadow-indigo-500/10 relative overflow-hidden group">
      
      {/* Side Status Indicator */}
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${indicatorColor}`}></div>

      <div className="flex justify-between items-start mb-5 pl-2">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path></svg>
            {repoName}
          </h2>
          <div className="text-sm text-slate-400 mt-2 flex items-center gap-3 font-mono">
            <span className="bg-slate-950 px-2.5 py-1 rounded-md border border-slate-800 text-indigo-300 flex items-center gap-1">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2"></path></svg>
              {branch}
            </span>
            <span className="text-slate-600">•</span>
            <span>{timestamp}</span>
          </div>
        </div>
        
        <div className={`px-4 py-1.5 rounded-full text-sm font-bold shadow-sm uppercase tracking-wide border ${statusColor}`}>
          {outcome}
        </div>
      </div>

      <div className="pl-2 mb-5">
        <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-2">Commit Message</p>
        <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-3 text-sm text-slate-300 font-medium italic">
          "{commitMessage}"
        </div>
      </div>

      <div className="pl-2">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center justify-center gap-2 text-sm font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-4 py-2.5 rounded-lg hover:bg-indigo-600 hover:text-white hover:border-indigo-600 transition-all duration-300"
        >
          <span>{isExpanded ? 'Hide AI Risk Summary' : 'View AI Risk Summary'}</span>
          <svg className={`w-4 h-4 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {isExpanded && (
          <div className="mt-4 bg-slate-950 p-5 rounded-lg border border-slate-800/80 shadow-inner overflow-x-auto">
            <h3 className="text-xs uppercase text-slate-500 font-bold mb-3 tracking-wider">Multi-Agent Review</h3>
            <pre className="text-sm text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">
              {llmSummary}
            </pre>
          </div>
        )}
      </div>

    </div>
  );
}