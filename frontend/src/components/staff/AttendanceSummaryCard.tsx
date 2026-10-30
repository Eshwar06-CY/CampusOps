import type { FC } from 'react';
import type { AttendanceSummaryResponse } from '../../api/types';
import { Card, CardHeader, CardBody } from '../common/Card';
import { Button } from '../common/Button';
import { IconRefresh, IconUsers, IconCheckCircle } from '../common/Icons';

interface AttendanceSummaryCardProps {
  summary: AttendanceSummaryResponse | null;
  isLoading: boolean;
  onRefresh: () => void;
}

export const AttendanceSummaryCard: FC<AttendanceSummaryCardProps> = ({
  summary,
  isLoading,
  onRefresh,
}) => {
  if (!summary) return null;

  const pct = Math.min(100, Math.max(0, summary.attendance_percentage));

  return (
    <Card>
      <CardHeader
        title="Live Attendance & Capacity Summary"
        subtitle="Real-time operational headcounts and team arrival breakdown."
        action={
          <Button
            variant="secondary"
            size="sm"
            onClick={onRefresh}
            isLoading={isLoading}
            leftIcon={<IconRefresh size={14} />}
          >
            Refresh KPIs
          </Button>
        }
      />
      <CardBody>
        {/* KPI Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 16,
            marginBottom: 24,
          }}
        >
          <div style={{ padding: 18, backgroundColor: 'var(--co-bg-subtle)', borderRadius: 'var(--co-radius-lg)', border: '1px solid var(--co-border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>
              Checked-In Attendees
            </span>
            <div style={{ fontSize: '2.25rem', fontWeight: 700, color: 'var(--co-primary-600)', margin: '6px 0', letterSpacing: '-0.02em' }}>
              {summary.current_attended_count}{' '}
              <span style={{ fontSize: '1rem', color: 'var(--co-text-muted)', fontWeight: 500 }}>
                / {summary.current_confirmed_count} Confirmed
              </span>
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--co-text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <IconCheckCircle size={14} style={{ color: 'var(--co-success-600)' }} />
              <strong>{pct.toFixed(1)}% Present</strong>
            </div>
          </div>

          <div style={{ padding: 18, backgroundColor: 'var(--co-bg-subtle)', borderRadius: 'var(--co-radius-lg)', border: '1px solid var(--co-border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>
              Venue Capacity Limit
            </span>
            <div style={{ fontSize: '2.25rem', fontWeight: 700, color: 'var(--co-text-main)', margin: '6px 0', letterSpacing: '-0.02em' }}>
              {summary.capacity_limit}
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--co-text-muted)' }}>
              <strong>{summary.capacity_limit - summary.current_confirmed_count} Slots Remaining</strong>
            </div>
          </div>

          <div style={{ padding: 18, backgroundColor: 'var(--co-bg-subtle)', borderRadius: 'var(--co-radius-lg)', border: '1px solid var(--co-border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>
              Registrations
            </span>
            <div style={{ fontSize: '1.25rem', fontWeight: 600, margin: '10px 0 6px 0', color: 'var(--co-text-main)' }}>
              {summary.total_individual_registrations} Solo · {summary.total_team_registrations} Teams
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--co-text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <IconUsers size={14} />
              <span>{summary.total_participants_registered} Total Registered Bodies</span>
            </div>
          </div>

          <div style={{ padding: 18, backgroundColor: 'var(--co-bg-subtle)', borderRadius: 'var(--co-radius-lg)', border: '1px solid var(--co-border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>
              Team Arrival Status
            </span>
            <div style={{ fontSize: '0.9rem', marginTop: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ color: 'var(--co-text-muted)' }}>Fully Present:</span>
                <strong style={{ color: 'var(--co-success-600)' }}>{summary.teams_fully_attended}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ color: 'var(--co-text-muted)' }}>Partially Present:</span>
                <strong style={{ color: 'var(--co-warning-600)' }}>{summary.teams_partially_attended}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--co-text-muted)' }}>Absent:</span>
                <strong style={{ color: 'var(--co-danger-600)' }}>{summary.teams_absent}</strong>
              </div>
            </div>
          </div>
        </div>

        {/* Progress bar */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: 8 }}>
            <span style={{ fontWeight: 500, color: 'var(--co-text-muted)' }}>Overall Attendance Progress</span>
            <strong style={{ fontFamily: 'var(--co-font-mono)', color: 'var(--co-text-main)' }}>{pct.toFixed(1)}%</strong>
          </div>
          <div
            style={{
              width: '100%',
              height: 10,
              backgroundColor: 'var(--co-bg-muted)',
              borderRadius: 'var(--co-radius-full)',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                width: `${pct}%`,
                height: '100%',
                backgroundColor: pct > 80 ? 'var(--co-success-500)' : 'var(--co-primary-600)',
                transition: 'width 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
              }}
            />
          </div>
        </div>
      </CardBody>
    </Card>
  );
};
