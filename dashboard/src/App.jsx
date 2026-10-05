import { useState, useEffect } from 'react';
import { collection, query, orderBy, getDocs, limit } from 'firebase/firestore';
import { db } from './firebase';
import PushLogCard from './components/PushLogCard';

function App() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchReports() {
      try {
        const reportsRef = collection(db, 'reports');
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
              // Parse the embedded JSON securely before passing to the component
              const parsedReport = { ...report, popup: parsePopup(report.popup) };
              return <PushLogCard key={report.id} report={parsedReport} />;
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;