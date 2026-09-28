import { useState, useEffect } from 'react';
import { Shield, ArrowRight, FolderGit2, Loader2, Search } from 'lucide-react';
import './LandingPage.css';

interface LandingPageProps {
  onSelectRepository: (repo: string) => void;
}

export default function LandingPage({ onSelectRepository }: LandingPageProps) {
  const [localRepos, setLocalRepos] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [repoInput, setRepoInput] = useState('');

  useEffect(() => {
    fetch('http://localhost:8000/api/repositories')
      .then(res => res.json())
      .then(data => {
        setLocalRepos(data.repositories || []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setError('Failed to load local repositories. Backend might be offline.');
        setLoading(false);
      });
  }, []);

  const handleAnalyze = (repo: string) => {
    if (repo.trim()) {
      onSelectRepository(repo.trim());
    }
  };

  return (
    <div className="landing-container">
      <div className="landing-content">
        <div className="brand">
          <Shield className="brand-icon" size={32} />
          <h1 className="brand-title">DRIFTGUARD</h1>
        </div>
        
        <h2 className="landing-subtitle">Cross-artifact consistency intelligence.</h2>
        
        <ul className="landing-features">
          <li>Connect a repository.</li>
          <li>Trace inconsistencies.</li>
          <li>Verify evidence.</li>
        </ul>

        <div className="divider"></div>

        <div className="repo-input-group">
          <div className="input-wrapper">
            <Search className="input-icon text-muted" size={16} />
            <input 
              type="text" 
              placeholder="owner/repository (e.g. tiangolo/fastapi)" 
              value={repoInput}
              onChange={(e) => setRepoInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAnalyze(repoInput)}
            />
          </div>
          <button 
            className="btn btn-primary"
            onClick={() => handleAnalyze(repoInput)}
            disabled={!repoInput.trim()}
          >
            <span>Analyze Repository</span>
            <ArrowRight size={16} />
          </button>
        </div>

        <div className="divider text-divider">or</div>

        <div className="local-repos-section">
          <div className="section-header">
            <FolderGit2 size={16} />
            <h3>Local Repositories</h3>
          </div>
          
          {loading ? (
            <div className="loading-state">
              <Loader2 className="spinner" size={16} />
              <span>Loading workspace...</span>
            </div>
          ) : error ? (
            <div className="error-state text-sm">{error}</div>
          ) : (
            <div className="repo-grid">
              {localRepos.length === 0 ? (
                <div className="empty-state">No repositories found in workspace.</div>
              ) : (
                localRepos.slice(0, 8).map(repo => (
                  <button 
                    key={repo} 
                    className="repo-card"
                    onClick={() => handleAnalyze(repo)}
                  >
                    <span className="font-mono text-sm">{repo}</span>
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
