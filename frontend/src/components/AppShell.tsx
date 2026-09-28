import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { Shield, LayoutDashboard, Beaker, LogOut } from 'lucide-react';
import './AppShell.css';

interface AppShellProps {
  repository: string | null;
  onClearRepository: () => void;
}

export default function AppShell({ repository, onClearRepository }: AppShellProps) {
  const navigate = useNavigate();

  if (!repository) {
    // If somehow accessed without a repository, don't crash, but typically handled by routing.
    return <Outlet />;
  }

  const handleClear = () => {
    onClearRepository();
    navigate('/');
  };

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <Shield className="logo-icon" size={18} />
          <span className="logo-text">DriftGuard</span>
        </div>
        
        <div className="repo-context">
          <div className="repo-label">TARGET REPOSITORY</div>
          <div className="repo-name font-mono" title={repository}>{repository}</div>
          <button className="change-repo-btn" onClick={handleClear}>
            <LogOut size={12} />
            <span>Change</span>
          </button>
        </div>

        <nav className="nav-menu">
          <div className="nav-group">
            <div className="nav-group-label">WORKSPACE</div>
            <NavLink 
              to="/analyze" 
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              <LayoutDashboard size={14} />
              <span>Analyze</span>
            </NavLink>
            <NavLink 
              to="/research" 
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              <Beaker size={14} />
              <span>Research</span>
            </NavLink>
          </div>
        </nav>
        
        <div className="sidebar-footer">
          <div className="status-indicator">
            <span className="status-dot"></span>
            <span>System Online</span>
          </div>
        </div>
      </aside>
      
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
