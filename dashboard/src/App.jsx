import { useState, useEffect } from 'react';
import { collection, query, orderBy, getDocs, limit } from 'firebase/firestore';
import { db } from './firebase';

function App() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchReports() {
      try {
        const reportsRef = collection(db, 'reports');
        // Fetch the 50 most recent pushes
        const q = query(reportsRef, orderBy('timestamp', 'desc'), limit(50));
        const querySnapshot = await getDocs(q);
        
        const fetchedReports = querySnapshot.docs.map(doc => ({
          id: doc.id,
          ...doc.data()
        }));
        
        setReports(fetchedReports);
      } catch (error) {
        console.error("Error fetching reports:", error);
      } finally {
        setLoading(false);
      }
    }

    fetchReports();
  }, []);

  // Helper to safely parse the JSON string that Python sent to Firestore
  const parsePopup = (popupData) => {
    if (!popupData) return null;
    if (typeof popupData === 'string') {
      try { return JSON.parse(popupData); } catch (e) { return null; }
    }
    return popupData;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-8 font-sans selection:bg-indigo-500/30">
      <div className="max-w-5xl mx-auto">
        
        {/* Header section */}
        <header className="mb-10 flex items-center justify-between border-b border-slate-800 pb-6">
          <div>
            <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400 tracking-tight">
              Preflight AI
            </h1>
            <p className="text-slate-400 mt-2 font-medium">Real-time Push Analysis & Risk Dashboard</p>
          </div>
          <div className="flex items-center gap-3 bg-slate-900/50 px-4 py-2 rounded-full border border-slate-800">
            <div className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </div>
            <span className="text-sm font-bold text-emerald-500 tracking-wider uppercase">Live Sync</span>
          </div>
        </header>

        {/* Main Content */}
        {loading ? (
          <div className="flex justify-center items-center py-32">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
          </div>
        ) : reports.length === 0 ? (
          <div className="text-center py-32 bg-slate-900/50 rounded-2xl border border-slate-800 shadow-inner">
            <p className="text-slate-400 text-xl font-medium">No push reports found in Firestore.</p>
            <p className="text-slate-500 mt-3">Make a Git commit and push it to see your AI analysis appear here.</p>
          </div>
        ) : (
          <div className="grid gap-6">
            {reports.map((report) => {
              const popupData = parsePopup(report.popup);
              
              return (
                <div key={report.id} className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-indigo-500/50 transition-all shadow-lg hover:shadow-indigo-500/10 relative overflow-hidden group">
                  
                  {/* Left glowing border effect based on decision */}
                  <div className={`absolute left-0 top-0 bottom-0 w-1 ${
                    report.decision === 'pass' ? 'bg-emerald-500' : report.decision === 'fail' ? 'bg-red-500' : 'bg-amber-500'
                  }`}></div>

                  <div className="flex justify-between items-start mb-5 pl-2">
                    <div>
                      <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path></svg>
                        {report.repo_id || 'Unknown Repository'}
                      </h2>
                      <div className="text-sm text-slate-400 mt-2 flex items-center gap-3 font-mono">
                        <span className="bg-slate-950 px-2.5 py-1 rounded-md border border-slate-800 text-indigo-300 flex items-center gap-1">
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2"></path></svg>
                          {report.branch || 'main'}
                        </span>
                        <span className="text-slate-600">•</span>
                        <span>{report.timestamp ? new Date(report.timestamp).toLocaleString() : 'Just now'}</span>
                      </div>
                    </div>
                    
                    {/* Status Badge */}
                    <div className={`px-4 py-1.5 rounded-full text-sm font-bold shadow-sm uppercase tracking-wide border ${
                      report.decision === 'pass' 
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                        : report.decision === 'fail'
                        ? 'bg-red-500/10 text-red-400 border-red-500/20'
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}>
                      {report.decision || 'UNKNOWN'}
                    </div>
                  </div>
                  
                  {/* AI Summary Block */}
                  {popupData && popupData.summary && (
                    <div className="mt-4 bg-slate-950 p-5 rounded-lg border border-slate-800/80 ml-2">
                      <h3 className="text-xs uppercase text-slate-500 font-bold mb-2 tracking-wider">AI Analysis</h3>
                      <p className="text-slate-300 text-sm leading-relaxed">
                        {popupData.summary}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;