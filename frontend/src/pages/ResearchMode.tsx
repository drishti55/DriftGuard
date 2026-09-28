import { FlaskConical } from 'lucide-react';
import './AnalyzeMode.css'; // Reusing styles for now

export default function ResearchMode() {
  return (
    <div className="analyze-container">
      <header className="analyze-header">
        <div>
          <h2 className="page-title">Research Laboratory</h2>
          <p className="page-subtitle text-muted font-mono">EXPERIMENTATION & EVALUATION</p>
        </div>
      </header>

      <div className="analyze-content">
        <div className="empty-state-large">
          <FlaskConical size={48} className="text-muted mb-4" />
          <h3>Research Mode Coming Soon</h3>
          <p className="text-secondary">
            Configure experiments, benchmark models, and evaluate RAG pipelines.
          </p>
        </div>
      </div>
    </div>
  );
}
