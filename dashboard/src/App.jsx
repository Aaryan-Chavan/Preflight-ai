import React, { useState, useEffect, createContext, useContext, useMemo } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useSearchParams } from 'react-router-dom';
import { collection, query, where, orderBy, getDocs, limit } from 'firebase/firestore';
import { onAuthStateChanged, signInWithPopup, signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut } from 'firebase/auth';
import { auth, provider, db } from './firebase';
import PushLogCard from './components/PushLogCard';

// --- Auth Context ---
const AuthContext = createContext(null);
const useAuth = () => useContext(AuthContext);

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setLoading(false);
    });
    return unsubscribe;
  }, []);

  if (loading) return <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center">Loading...</div>;
  return <AuthContext.Provider value={{ user }}>{children}</AuthContext.Provider>;
}

// --- Protected Route Wrapper ---
function ProtectedRoute({ children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-200 font-sans">
      <header className="sticky top-0 z-20 border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3.5 sm:px-6">
          <Link to="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500 text-white shadow-lg shadow-indigo-500/20">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" /></svg>
            </div>
            <div className="leading-tight">
              <h1 className="text-base font-semibold tracking-tight text-white">Preflight AI</h1>
              <p className="text-xs text-zinc-500">Workspace</p>
            </div>
          </Link>
          <nav className="flex items-center gap-4 text-sm font-medium">
            <Link to="/" className="text-zinc-400 hover:text-white transition-colors">Logs</Link>
            <Link to="/profile" className="text-zinc-400 hover:text-white transition-colors">Profile</Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-10">{children}</main>
    </div>
  );
}

// --- Pages ---
function Dashboard() {
  const { user } = useAuth();
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchReports() {
      try {
        const reportsRef = collection(db, 'reports');
        // Fetch logs isolated to the currently logged in user
        const q = query(reportsRef, where('userId', '==', user.uid), orderBy('timestamp', 'desc'), limit(50));
        const querySnapshot = await getDocs(q);
        setReports(querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })));
      } catch (error) {
        console.error("Fetch error:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchReports();
  }, [user]);

  // Group reports by project (repository name)
  const groupedReports = useMemo(() => {
    return reports.reduce((acc, report) => {
      const parsed = { ...report, popup: typeof report.popup === 'string' ? JSON.parse(report.popup) : report.popup };
      const repoName = parsed.repo_name || parsed.popup?.repo_name || 'Unknown Project';
      if (!acc[repoName]) acc[repoName] = [];
      acc[repoName].push(parsed);
      return acc;
    }, {});
  }, [reports]);

  if (loading) return <div className="text-center text-zinc-500 py-20">Loading your project logs...</div>;

  return (
    <div>
      <h2 className="text-2xl font-bold text-white mb-6">Your Projects</h2>
      {Object.keys(groupedReports).length === 0 ? (
        <div className="text-center py-20 text-zinc-400">No push logs found for this account. Run a git push!</div>
      ) : (
        Object.entries(groupedReports).map(([repoName, projectReports]) => (
          <div key={repoName} className="mb-10">
            <h3 className="text-lg font-semibold text-indigo-400 mb-4 border-b border-zinc-800 pb-2">{repoName}</h3>
            <div className="grid gap-3">
              {projectReports.map(report => <PushLogCard key={report.id} report={report} />)}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

function Profile() {
  const { user } = useAuth();
  return (
    <div className="max-w-md bg-zinc-900 border border-zinc-800 rounded-xl p-6 shadow-xl">
      <h2 className="text-xl font-bold text-white mb-6">Developer Profile</h2>
      <div className="space-y-4">
        <div>
          <label className="text-xs text-zinc-500 uppercase font-semibold">Name / Github</label>
          <p className="text-white text-lg">{user.displayName || 'Developer'}</p>
        </div>
        <div>
          <label className="text-xs text-zinc-500 uppercase font-semibold">Email Address</label>
          <p className="text-white">{user.email}</p>
        </div>
        <div>
          <label className="text-xs text-zinc-500 uppercase font-semibold">System ID</label>
          <p className="text-zinc-400 font-mono text-sm break-all">{user.uid}</p>
        </div>
        <button onClick={() => signOut(auth)} className="mt-4 w-full py-2 bg-rose-500/10 text-rose-500 rounded-lg hover:bg-rose-500/20 font-semibold transition">
          Sign Out
        </button>
      </div>
    </div>
  );
}

function AuthPage() {
  const { user } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  if (user) return <Navigate to="/" replace />;

  const handleEmailAuth = async (e) => {
    e.preventDefault();
    try {
      if (isLogin) await signInWithEmailAndPassword(auth, email, password);
      else await createUserWithEmailAndPassword(auth, email, password);
    } catch (err) { alert(err.message); }
  };

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
      <div className="max-w-sm w-full bg-zinc-900 border border-zinc-800 p-8 rounded-2xl shadow-2xl">
        <h2 className="text-2xl font-bold text-white text-center mb-6">{isLogin ? 'Welcome Back' : 'Create Account'}</h2>
        <form onSubmit={handleEmailAuth} className="space-y-4">
          <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500" required />
          <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500" required />
          <button type="submit" className="w-full bg-indigo-600 text-white font-bold py-2 rounded-lg hover:bg-indigo-500 transition">{isLogin ? 'Sign In' : 'Sign Up'}</button>
        </form>
        <div className="my-4 flex items-center gap-3"><hr className="flex-1 border-zinc-800"/><span className="text-xs text-zinc-500 uppercase">OR</span><hr className="flex-1 border-zinc-800"/></div>
        <button onClick={() => signInWithPopup(auth, provider)} className="w-full bg-white text-black font-bold py-2 rounded-lg hover:bg-zinc-200 transition">Continue with Google</button>
        <p className="mt-6 text-center text-sm text-zinc-500 cursor-pointer hover:text-zinc-300" onClick={() => setIsLogin(!isLogin)}>
          {isLogin ? "Need an account? Sign up" : "Already have an account? Sign in"}
        </p>
      </div>
    </div>
  );
}

function CliLogin() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const port = searchParams.get('callback_port');

  useEffect(() => {
    if (user && port) {
      user.getIdToken().then(idToken => {
        const refreshToken = user.refreshToken || user.stsTokenManager?.refreshToken || "legacy_token";
        window.location.href = `http://127.0.0.1:${port}?id_token=${idToken}&refresh_token=${refreshToken}&uid=${user.uid}`;
      });
    }
  }, [user, port]);

  if (!user) return <AuthPage />;
  return <div className="min-h-screen bg-zinc-950 flex items-center justify-center text-indigo-400 font-mono text-lg animate-pulse">Authenticating your terminal...</div>;
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<AuthPage />} />
          <Route path="/cli-login" element={<CliLogin />} />
          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}