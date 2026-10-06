import { useState } from 'react';
import { Play, FileText, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import './AnalyzeMode.css';

interface AnalyzeModeProps {
  repository: string | null;
}

export default function AnalyzeMode({ repository }: AnalyzeModeProps) {
  const [analyzing, setAnalyzing] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = async () => {
    if (!repository) {
      setError('No repository selected.');
      return;
    }
    setAnalyzing(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:8000/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          repository: repository,
          max_candidates: 5 // Default for fast demo
        })
      });
      const data = await response.json();
      if (data.error) {
        setError(data.error);
      } else {
        setResults(data);
      }
    } catch (err) {
      setError('Failed to connect to analysis engine.');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="analyze-container">
      <header className="analyze-header">
        <div>
          <h2 className="page-title">Analysis Workstation</h2>
          <p className="page-subtitle text-muted font-mono">{repository}</p>
        </div>
        <button 
          className="btn btn-primary" 
          onClick={runAnalysis}
          disabled={analyzing}
        >
          {analyzing ? <Loader2 className="spinner" size={16} /> : <Play size={16} />}
          <span>{analyzing ? 'Analyzing...' : 'Run Analysis'}</span>
        </button>
      </header>

      <div className="analyze-content">
        {!results && !analyzing && !error && (
          <div className="empty-state-large">
            <FileText size={48} className="text-muted mb-4" />
            <h3>No Analysis Results</h3>
            <p className="text-secondary">Run an analysis to detect cross-artifact inconsistencies.</p>
          </div>
        )}

        {analyzing && (
          <div className="loading-state-large">
            <Loader2 className="spinner" size={48} />
            <h3>ANALYZING REPOSITORY</h3>
            <div className="loading-steps">
              <div className="step active">Scanning artifacts...</div>
              <div className="step">Extracting symbols...</div>
              <div className="step">Building relationships...</div>
              <div className="step">Analyzing consistency...</div>
            </div>
          </div>
        )}

        {error && (
          <div className="error-panel">
            <AlertCircle size={24} className="text-danger" />
            <div>
              <h4 className="text-danger">Analysis Failed</h4>
              <p>{error}</p>
            </div>
          </div>
        )}

        {results && !analyzing && (
          <div className="results-panel">
            <div className="metrics-grid">
              <div className="metric-card">
                <span className="metric-label">CANDIDATES</span>
                <span className="metric-value">{results.metrics?.candidates_analyzed || 0}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">DRIFTS DETECTED</span>
                <span className="metric-value text-danger">{results.metrics?.drifts_found || 0}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">STATUS</span>
                <span className="metric-value">{results.status}</span>
              </div>
            </div>

            <div className="drifts-list">
              <h3 className="section-title">Verified Findings</h3>
              {results.drifts && results.drifts.length > 0 ? (
                results.drifts.map((drift: any, i: number) => (
                  <div key={i} className="drift-card">
                    <div className="drift-header">
                      <div className="drift-badge high">HIGH RISK</div>
                      <div className="drift-type">{drift.prediction?.drift_type?.replace(/_/g, ' ').toUpperCase() || 'UNKNOWN'}</div>
                    </div>
                    <div className="drift-artifacts">
                      <div className="artifact font-mono">{drift.artifact_1_path}</div>
                      <div className="connection">↔</div>
                      <div className="artifact font-mono">{drift.artifact_2_path}</div>
                    </div>
                    <div className="drift-evidence">
                      <div className="evidence-label">CONTRADICTION</div>
                      <p>{drift.prediction?.evidence || 'No evidence provided.'}</p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="success-panel">
                  <CheckCircle2 size={24} className="text-success" />
                  <div>
                    <h4 className="text-success">No Drift Found</h4>
                    <p>Repository is consistent across all analyzed candidates.</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
