import type { FC } from 'react';
import type { PublicEventDetails } from '../../api/types';
import { Card, CardBody } from '../common/Card';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { IconCalendar, IconMapPin, IconUsers, IconSearch, IconCheckCircle, IconAlertTriangle } from '../common/Icons';
import { formatDate, formatTimezone } from '../../utils/formatters';

interface EventOverviewProps {
  event: PublicEventDetails;
  onOpenLookup?: () => void;
}

export const EventOverview: FC<EventOverviewProps> = ({ event, onOpenLookup }) => {
  const getStatusBadge = () => {
    switch (event.registration_status) {
      case 'open':
        return (
          <Badge variant="success" icon={<IconCheckCircle size={12} />}>
            Registration Open
          </Badge>
        );
      case 'closed':
        return (
          <Badge variant="danger" icon={<IconAlertTriangle size={12} />}>
            Registration Closed
          </Badge>
        );
      case 'not_yet_open':
        return (
          <Badge variant="warning" icon={<IconAlertTriangle size={12} />}>
            Opens Soon
          </Badge>
        );
      case 'ended':
        return <Badge variant="neutral">Event Concluded</Badge>;
      default:
        return <Badge variant="neutral">{event.registration_status}</Badge>;
    }
  };

  const getFormatLabel = () => {
    switch (event.registration_format) {
      case 'solo':
        return 'Individual Registration Only';
      case 'team':
        return `Team Registration Only (${event.team_size_min}–${event.team_size_max} members)`;
      case 'both':
        return `Individual or Team (${event.team_size_min}–${event.team_size_max} members)`;
    }
  };

  return (
    <Card className="co-event-overview">
      <CardBody>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              {getStatusBadge()}
              {event.capacity_available ? (
                <Badge variant="primary" dot>
                  Capacity Available
                </Badge>
              ) : (
                <Badge variant="warning" dot>
                  At Full Capacity
                </Badge>
              )}
            </div>
            <h1 style={{ margin: '0 0 8px 0', fontSize: '2rem', fontWeight: 700, color: 'var(--co-text-main)', letterSpacing: '-0.02em' }}>
              {event.event_name}
            </h1>
            {event.description && (
              <p style={{ margin: '0 0 16px 0', color: 'var(--co-text-muted)', fontSize: '0.95rem', maxWidth: 720, lineHeight: 1.6 }}>
                {event.description}
              </p>
            )}
          </div>
          {onOpenLookup && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={onOpenLookup}
              leftIcon={<IconSearch size={14} />}
              aria-label="Look up existing registration"
            >
              Look Up My Registration
            </Button>
          )}
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 16,
            paddingTop: 16,
            borderTop: '1px solid var(--co-border-subtle)',
            fontSize: '0.875rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <span style={{ color: 'var(--co-primary-600)', marginTop: 2 }}>
              <IconCalendar size={18} />
            </span>
            <div>
              <span style={{ color: 'var(--co-text-muted)', display: 'block', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Event Schedule
              </span>
              <strong style={{ color: 'var(--co-text-main)' }}>
                {formatDate(event.event_date)}
                {event.event_end_date && event.event_end_date !== event.event_date && ` – ${formatDate(event.event_end_date)}`}
              </strong>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <span style={{ color: 'var(--co-primary-600)', marginTop: 2 }}>
              <IconMapPin size={18} />
            </span>
            <div>
              <span style={{ color: 'var(--co-text-muted)', display: 'block', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Venue & Timezone
              </span>
              <strong style={{ color: 'var(--co-text-main)' }}>
                {event.venue || 'Campus Venue TBD'} ({formatTimezone(event.timezone)})
              </strong>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <span style={{ color: 'var(--co-primary-600)', marginTop: 2 }}>
              <IconUsers size={18} />
            </span>
            <div>
              <span style={{ color: 'var(--co-text-muted)', display: 'block', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Registration Policy
              </span>
              <strong style={{ color: 'var(--co-text-main)' }}>{getFormatLabel()}</strong>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};
