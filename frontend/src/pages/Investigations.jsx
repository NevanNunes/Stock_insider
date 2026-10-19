import { FolderOpen } from 'lucide-react';
import InvestigationTracker from '../components/InvestigationTracker';

export default function Investigations() {
  return (
    <div>
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <FolderOpen size={22} color="var(--accent-purple)" />
            <h1 className="page-title">Investigation Cases</h1>
          </div>
          <p className="page-subtitle">Compliance case management & PDF report generation</p>
        </div>
      </div>
      <InvestigationTracker />
    </div>
  );
}
