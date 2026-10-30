import { useState, type FC } from 'react';
import type { PublicRegistrationResponse, PublicEventDetails } from '../../api/types';
import { Card, CardHeader, CardBody } from '../common/Card';
import { Alert } from '../common/Alert';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { IconCheckCircle, IconCopy, IconCheck, IconPrinter } from '../common/Icons';
import { PublicPassDisplay } from './PublicPassDisplay';
import { useToast } from '../common/Toast';

interface RegistrationConfirmationProps {
  registration: PublicRegistrationResponse;
  event: PublicEventDetails;
  onReset: () => void;
}

export const RegistrationConfirmation: FC<RegistrationConfirmationProps> = ({
  registration,
  event,
  onReset,
}) => {
  const isTeam = registration.registration_type === 'team';
  const [copiedCode, setCopiedCode] = useState(false);
  const { showToast } = useToast();

  const handleCopyConfirmation = async () => {
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(registration.confirmation_code);
        setCopiedCode(true);
        showToast('success', 'Confirmation Code Copied', registration.confirmation_code);
        setTimeout(() => setCopiedCode(false), 2000);
      }
    } catch {
      // Ignore
    }
  };

  const handlePrintAll = () => {
    window.print();
  };

  return (
    <div>
      <Card>
        <CardHeader
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span>Registration Confirmed</span>
              <Badge variant="success" icon={<IconCheckCircle size={14} />}>
                Confirmed
              </Badge>
            </div>
          }
          subtitle={`Event: ${event.event_name}`}
          action={
            <div style={{ display: 'flex', gap: 8 }} className="no-print">
              <Button
                variant="secondary"
                size="sm"
                onClick={handlePrintAll}
                leftIcon={<IconPrinter size={14} />}
              >
                Print Passes
              </Button>
            </div>
          }
        />
        <CardBody>
          <Alert variant="success" title="Admission Passes Issued">
            Your registration has been successfully processed by CampusOps. Below are the individual admission passes for each registered participant. Please screenshot or save these passes for event-day entry.
          </Alert>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: 16,
              margin: '20px 0',
              padding: '18px',
              backgroundColor: 'var(--co-bg-subtle)',
              borderRadius: 'var(--co-radius-lg)',
              border: '1px solid var(--co-border-subtle)',
            }}
          >
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Confirmation Code
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                <div style={{ fontFamily: 'var(--co-font-mono)', fontSize: '1.25rem', fontWeight: 700, color: 'var(--co-primary-600)' }}>
                  {registration.confirmation_code}
                </div>
                <button
                  type="button"
                  className="co-btn co-btn-ghost co-btn-sm no-print"
                  onClick={handleCopyConfirmation}
                  title="Copy confirmation code"
                  style={{ padding: '2px 6px' }}
                >
                  {copiedCode ? <IconCheck size={14} style={{ color: 'var(--co-success-600)' }} /> : <IconCopy size={14} />}
                </button>
              </div>
            </div>
            {isTeam && (
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Team Name
                </span>
                <div style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: 4 }}>{registration.team_name}</div>
              </div>
            )}
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Pass Count
              </span>
              <div style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: 4 }}>
                {registration.passes.length} {registration.passes.length === 1 ? 'Attendee' : 'Attendees'}
              </div>
            </div>
          </div>

          <Alert variant="info" title="Important Event-Day Attendance Notice">
            <strong>Individual Check-In Rule:</strong> Every participant must present their individual pass at the registration desk. Arriving together as a team does not automatically mark all team members as present.
          </Alert>

          {/* List of Passes */}
          <div style={{ marginTop: 24 }}>
            <h4 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', fontWeight: 600 }}>
              {isTeam ? 'Team Member Admission Passes' : 'Your Digital Admission Pass'}
            </h4>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: registration.passes.length > 1 ? 'repeat(auto-fit, minmax(320px, 1fr))' : '1fr',
                gap: 20,
              }}
            >
              {registration.passes.map((pass) => (
                <PublicPassDisplay
                  key={pass.participant_id}
                  pass={pass}
                  eventName={event.event_name}
                  isTeam={isTeam}
                  teamName={registration.team_name}
                />
              ))}
            </div>
          </div>

          <div style={{ textAlign: 'center', marginTop: 32 }} className="no-print">
            <Button variant="secondary" onClick={onReset}>
              Register Another Attendee / Team
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
};
