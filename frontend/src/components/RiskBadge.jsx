import { AlertTriangle, TrendingUp, Shield } from 'lucide-react';

const ICONS = {
  HIGH: AlertTriangle,
  MEDIUM: TrendingUp,
  LOW: Shield,
};

/**
 * RiskBadge - displays LOW / MEDIUM / HIGH with color-coded styling
 */
export default function RiskBadge({ level, size = 'md' }) {
  const Icon = ICONS[level] || Shield;
  const cls = size === 'lg'
    ? 'badge badge-' + level + ' badge-lg'
    : 'badge badge-' + level;

  return (
    <span className={cls} style={size === 'lg' ? { fontSize: '0.8rem', padding: '0.3rem 0.9rem' } : {}}>
      <Icon size={size === 'lg' ? 12 : 10} strokeWidth={2.5} />
      {level}
    </span>
  );
}
