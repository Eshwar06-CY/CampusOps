import type { FC } from 'react';
import { Card, CardHeader, CardBody } from '../common/Card';
import { Alert } from '../common/Alert';
import { IconShield, IconInfo } from '../common/Icons';

export const AuthUnavailableNotice: FC = () => {
  return (
    <Card>
      <CardHeader
        title="Staff Authentication Required"
        subtitle="Access to staff operations, attendee rosters, and check-in desks is restricted to authorized personnel."
      />
      <CardBody>
        <Alert variant="warning" title="Identity Provider Not Configured (HTTP 401)">
          The upstream authentication provider (e.g. Supabase Auth / OIDC) has not yet been connected to this environment.
          In accordance with the CampusOps fail-closed security boundary, unauthenticated staff API requests are rejected.
        </Alert>

        <div style={{ marginTop: 20, fontSize: '0.9rem', color: 'var(--co-text-muted)', lineHeight: 1.6 }}>
          <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
            <span style={{ color: 'var(--co-primary-600)', marginTop: 2 }}>
              <IconShield size={20} />
            </span>
            <div>
              <strong style={{ color: 'var(--co-text-main)', display: 'block', marginBottom: 2 }}>
                Why am I seeing this?
              </strong>
              <span>
                CampusOps operates on a strict deny-by-default role-based access control (RBAC) model. Staff operations require an authenticated organization membership. No mock logins or hardcoded credentials are permitted in the client application.
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 12 }}>
            <span style={{ color: 'var(--co-info-600)', marginTop: 2 }}>
              <IconInfo size={20} />
            </span>
            <div>
              <strong style={{ color: 'var(--co-text-main)', display: 'block', marginBottom: 2 }}>
                Public Registration is unaffected:
              </strong>
              <span>
                Prospective attendees do not require a staff account and can access self-service event registration directly using the public registration link.
              </span>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};
