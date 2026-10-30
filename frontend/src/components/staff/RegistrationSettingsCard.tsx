import { useState, type FC, type FormEvent } from 'react';
import type { EventRegistrationSettingsResponse, RegistrationFormat } from '../../api/types';
import { updateRegistrationSettings } from '../../api/staffOperations';
import { ApiError } from '../../api/client';
import { Card, CardHeader, CardBody } from '../common/Card';
import { TextInput, SelectInput } from '../common/Input';
import { Button } from '../common/Button';
import { Alert } from '../common/Alert';
import { Badge } from '../common/Badge';
import { IconCheckCircle, IconAlertTriangle, IconCheck } from '../common/Icons';
import { useToast } from '../common/Toast';

interface RegistrationSettingsCardProps {
  orgId: string;
  eventId: string;
  settings: EventRegistrationSettingsResponse | null;
  authToken?: string | null;
  onUpdateSuccess: (updated: EventRegistrationSettingsResponse) => void;
}

export const RegistrationSettingsCard: FC<RegistrationSettingsCardProps> = ({
  orgId,
  eventId,
  settings,
  authToken,
  onUpdateSuccess,
}) => {
  const [isOpen, setIsOpen] = useState(settings?.is_open ?? true);
  const [format, setFormat] = useState<RegistrationFormat>(settings?.registration_format ?? 'both');
  const [capacity, setCapacity] = useState(settings?.capacity_limit ?? 100);
  const [minTeam, setMinTeam] = useState(settings?.team_size_min ?? 2);
  const [maxTeam, setMaxTeam] = useState(settings?.team_size_max ?? 4);
  const [rotateKey, setRotateKey] = useState(false);

  const [isSaving, setIsSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const { showToast } = useToast();

  if (!settings) return null;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);

    if (capacity < 1) {
      setErrorMsg('Capacity limit must be at least 1.');
      return;
    }
    if (minTeam < 1 || maxTeam < minTeam) {
      setErrorMsg('Invalid team sizing bounds: Max team size must be >= min team size.');
      return;
    }

    setIsSaving(true);
    try {
      const updated = await updateRegistrationSettings(
        orgId,
        eventId,
        {
          is_open: isOpen,
          registration_format: format,
          capacity_limit: Number(capacity),
          team_size_min: Number(minTeam),
          team_size_max: Number(maxTeam),
          rotate_registration_key: rotateKey,
        },
        { authToken },
      );
      setSuccessMsg('Registration settings updated successfully.');
      showToast('success', 'Settings Saved', 'Registration settings and capacity bounds updated.');
      setRotateKey(false);
      onUpdateSuccess(updated);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMsg(err.detail);
        showToast('error', 'Update Failed', err.detail);
      } else {
        setErrorMsg('Failed to update registration settings.');
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader
        title="Event Registration & Capacity Settings"
        subtitle="Configure registration status, capacity bounds, and public registration keys."
      />
      <CardBody>
        {successMsg && (
          <Alert variant="success" title="Success">
            {successMsg}
          </Alert>
        )}

        {errorMsg && (
          <Alert variant="danger" title="Update Error">
            {errorMsg}
          </Alert>
        )}

        {/* Current status display */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 16,
            padding: 16,
            backgroundColor: 'var(--co-bg-subtle)',
            borderRadius: 'var(--co-radius-lg)',
            border: '1px solid var(--co-border-subtle)',
            marginBottom: 24,
            fontSize: '0.875rem',
          }}
        >
          <div>
            <span style={{ color: 'var(--co-text-muted)', display: 'block', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Status
            </span>
            <div style={{ marginTop: 4 }}>
              <Badge
                variant={settings.is_open ? 'success' : 'danger'}
                icon={settings.is_open ? <IconCheckCircle size={12} /> : <IconAlertTriangle size={12} />}
              >
                {settings.is_open ? 'Accepting Registrations' : 'Registration Closed'}
              </Badge>
            </div>
          </div>
          <div>
            <span style={{ color: 'var(--co-text-muted)', display: 'block', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Current Headcount
            </span>
            <strong style={{ display: 'block', marginTop: 4 }}>
              {settings.current_confirmed_count} / {settings.capacity_limit} confirmed
            </strong>
          </div>
          <div>
            <span style={{ color: 'var(--co-text-muted)', display: 'block', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Format
            </span>
            <strong style={{ textTransform: 'capitalize', display: 'block', marginTop: 4 }}>
              {settings.registration_format}
            </strong>
          </div>
          <div>
            <span style={{ color: 'var(--co-text-muted)', display: 'block', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Shareable Registration Key
            </span>
            <code style={{ fontSize: '0.8rem', color: 'var(--co-primary-600)', fontFamily: 'var(--co-font-mono)', display: 'block', marginTop: 4 }}>
              {settings.public_registration_key || '(Active Key Hidden)'}
            </code>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontWeight: 600, fontSize: '0.95rem' }}>
              <input
                type="checkbox"
                checked={isOpen}
                onChange={(e) => setIsOpen(e.target.checked)}
                disabled={isSaving}
              />
              <span>Registration Open (Accepting Submissions)</span>
            </label>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
            <SelectInput
              id="settings-format"
              label="Registration Format"
              value={format}
              onChange={(e) => setFormat(e.target.value as RegistrationFormat)}
              options={[
                { value: 'both', label: 'Both Individual & Team' },
                { value: 'solo', label: 'Individual Only' },
                { value: 'team', label: 'Team Only' },
              ]}
              disabled={isSaving}
            />

            <TextInput
              id="settings-capacity"
              type="number"
              min={1}
              label="Venue Capacity Limit (Human Bodies)"
              value={capacity}
              onChange={(e) => setCapacity(Number(e.target.value))}
              required
              disabled={isSaving}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
            <TextInput
              id="settings-min-team"
              type="number"
              min={1}
              label="Minimum Team Size"
              value={minTeam}
              onChange={(e) => setMinTeam(Number(e.target.value))}
              disabled={isSaving || format === 'solo'}
            />

            <TextInput
              id="settings-max-team"
              type="number"
              min={minTeam}
              label="Maximum Team Size"
              value={maxTeam}
              onChange={(e) => setMaxTeam(Number(e.target.value))}
              disabled={isSaving || format === 'solo'}
            />
          </div>

          <div
            style={{
              padding: 14,
              marginTop: 16,
              border: '1px solid var(--co-warning-500)',
              borderRadius: 'var(--co-radius-lg)',
              backgroundColor: 'var(--co-warning-50)',
            }}
          >
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer', fontSize: '0.875rem' }}>
              <input
                type="checkbox"
                checked={rotateKey}
                onChange={(e) => setRotateKey(e.target.checked)}
                disabled={isSaving}
                style={{ marginTop: 2 }}
              />
              <div>
                <strong style={{ color: 'var(--co-warning-800)' }}>Rotate Public Registration Key:</strong>
                <span style={{ color: 'var(--co-warning-700)', display: 'block', marginTop: 2 }}>
                  Immediately invalidates the existing public link and generates a new high-entropy key. Prior issued passes and registrations remain valid.
                </span>
              </div>
            </label>
          </div>

          <div style={{ marginTop: 24, display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              type="submit"
              variant="primary"
              isLoading={isSaving}
              loadingText="Saving Settings..."
              leftIcon={<IconCheck size={16} />}
            >
              Save Settings
            </Button>
          </div>
        </form>
      </CardBody>
    </Card>
  );
};
