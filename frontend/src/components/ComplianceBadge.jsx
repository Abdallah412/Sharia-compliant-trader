import { motion, useReducedMotion } from 'framer-motion';
import { Check, AlertTriangle, XCircle } from 'lucide-react';

const SIZE_MAP = {
  sm: 'text-xs px-2 py-0.5',
  md: 'text-sm px-3 py-1',
  lg: 'text-base px-4 py-1.5',
};

const ICON_SIZE = { sm: 12, md: 14, lg: 16 };

const STATUS_CONFIG = {
  HALAL: {
    classes: 'bg-halal-bg text-halal border border-halal/30',
    Icon: Check,
    label: 'Halal',
  },
  DOUBTFUL: {
    classes: 'bg-doubtful-bg text-doubtful border border-doubtful/30',
    Icon: AlertTriangle,
    label: 'Doubtful',
  },
  HARAM: {
    classes: 'bg-haram-bg text-haram border border-haram/30',
    Icon: XCircle,
    label: 'Haram',
  },
};

export default function ComplianceBadge({ status, size = 'md', pulse = false }) {
  const prefersReducedMotion = useReducedMotion();
  const normalized = (status || '').toUpperCase();

  // Map alternative names
  const key =
    normalized === 'COMPLIANT'
      ? 'HALAL'
      : normalized === 'REVIEW'
        ? 'DOUBTFUL'
        : normalized === 'NON_COMPLIANT'
          ? 'HARAM'
          : normalized;

  const config = STATUS_CONFIG[key];
  if (!config) {
    return (
      <span className={`inline-flex items-center gap-1 rounded-full font-semibold ${SIZE_MAP[size]} bg-bg-elevated text-text-muted border border-border-main`}>
        {status || 'N/A'}
      </span>
    );
  }

  const { classes, Icon, label } = config;
  const iconSize = ICON_SIZE[size];

  // Determine animation
  let animateProps = {};
  const shouldAnimate = !prefersReducedMotion;

  if (key === 'DOUBTFUL' && shouldAnimate) {
    // Gentle pulse: always active for doubtful
    animateProps = {
      animate: { opacity: [1, 0.7, 1] },
      transition: { duration: 2, repeat: Infinity, ease: 'easeInOut' },
    };
  } else if (key === 'HARAM' && shouldAnimate) {
    // Urgent fast pulse
    animateProps = {
      animate: { scale: [1, 1.05, 1] },
      transition: { duration: 0.8, repeat: Infinity, ease: 'easeInOut' },
    };
  }

  const Badge = shouldAnimate && (key === 'DOUBTFUL' || key === 'HARAM') ? motion.span : 'span';

  return (
    <Badge
      className={`inline-flex items-center gap-1 rounded-full font-semibold ${SIZE_MAP[size]} ${classes}`}
      {...animateProps}
    >
      <Icon size={iconSize} />
      {label}
    </Badge>
  );
}
