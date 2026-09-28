import { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppShell from './components/AppShell';
import LandingPage from './pages/LandingPage';
import AnalyzeMode from './pages/AnalyzeMode';
import ResearchMode from './pages/ResearchMode';

function App() {
  const [repository, setRepository] = useState<string | null>(null);

  return (
    <BrowserRouter>
      <Routes>
        <Route 
          path="/" 
          element={
            repository ? (
              <Navigate to="/analyze" replace />
            ) : (
              <LandingPage onSelectRepository={setRepository} />
            )
          } 
        />
        <Route 
          path="/" 
          element={<AppShell repository={repository} onClearRepository={() => setRepository(null)} />}
        >
          <Route path="analyze" element={<AnalyzeMode repository={repository} />} />
          <Route path="research" element={<ResearchMode />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
