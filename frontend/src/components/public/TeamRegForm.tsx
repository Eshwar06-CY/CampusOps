import { useState, useRef, type FC, type FormEvent } from 'react';
import type {
  PublicEventDetails,
  PublicRegistrationRequest,
  PublicRegistrationResponse,
  PublicParticipantInput,
} from '../../api/types';
import { submitPublicRegistration } from '../../api/publicRegistration';
import { ApiError } from '../../api/client';
import { generateIdempotencyKey, createPayloadFingerprint } from '../../utils/idempotency';
import { Card, CardHeader, CardBody, CardFooter } from '../common/Card';
import { TextInput } from '../common/Input';
import { Button } from '../common/Button';
import { Alert } from '../common/Alert';
import { IconCrown, IconUsers, IconX } from '../common/Icons';

interface TeamRegFormProps {
  event: PublicEventDetails;
  onSuccess: (response: PublicRegistrationResponse) => void;
}

interface MemberState {
  fullName: string;
  email: string;
  phone: string;
  college: string;
  studentId: string;
}

export const TeamRegForm: FC<TeamRegFormProps> = ({ event, onSuccess }) => {
  const minSize = Math.max(1, event.team_size_min || 2);
  const maxSize = Math.max(minSize, event.team_size_max || 4);

  const [teamName, setTeamName] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [consent, setConsent] = useState(false);

  // Initialize members with minSize slots
  const [members, setMembers] = useState<MemberState[]>(() => {
    return Array.from({ length: minSize }, () => ({
      fullName: '',
      email: '',
      phone: '',
      college: '',
      studentId: '',
    }));
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Idempotency tracking
  const idempotencyRef = useRef<{ key: string; fingerprint: string } | null>(null);

  const handleMemberChange = (index: number, field: keyof MemberState, value: string) => {
    setMembers((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
    // Clear relevant error
    if (errors[`member_${index}_${field}`]) {
      setErrors((prev) => ({ ...prev, [`member_${index}_${field}`]: '' }));
    }
  };

  const addMember = () => {
    if (members.length < maxSize) {
      setMembers((prev) => [
        ...prev,
        { fullName: '', email: '', phone: '', college: '', studentId: '' },
      ]);
    }
  };

  const removeMember = (index: number) => {
    if (members.length > minSize) {
      setMembers((prev) => prev.filter((_, idx) => idx !== index));
    }
  };

  const validate = (): boolean => {
    const errs: Record<string, string> = {};

    if (!teamName.trim()) {
      errs.teamName = 'Team name is required.';
    }

    if (members.length < minSize || members.length > maxSize) {
      errs.teamSize = `Team size must be between ${minSize} and ${maxSize} members.`;
    }

    const seenEmails = new Set<string>();
    members.forEach((m, idx) => {
      if (!m.fullName.trim()) {
        errs[`member_${idx}_fullName`] = `Member ${idx + 1} full name is required.`;
      }
      const email = m.email.trim().toLowerCase();
      if (!email) {
        errs[`member_${idx}_email`] = `Member ${idx + 1} email is required.`;
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        errs[`member_${idx}_email`] = `Member ${idx + 1} email is invalid.`;
      } else if (seenEmails.has(email)) {
        errs[`member_${idx}_email`] = `Duplicate email: Member ${idx + 1} shares email with another member.`;
      } else {
        seenEmails.add(email);
      }
    });

    if (!consent) {
      errs.consent = 'You must acknowledge event participation rules.';
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setApiError(null);

    if (!validate()) return;
    if (event.registration_status !== 'open') {
      setApiError('Registration for this event is currently not open.');
      return;
    }

    const participantsPayload: PublicParticipantInput[] = members.map((m, idx) => ({
      full_name: m.fullName.trim(),
      email: m.email.trim().toLowerCase(),
      phone_number: m.phone.trim() || null,
      college_name: m.college.trim() || null,
      student_id: m.studentId.trim() || null,
      is_primary_contact: idx === 0,
      team_role: idx === 0 ? 'leader' : 'member',
    }));

    const payload: PublicRegistrationRequest = {
      registration_type: 'team',
      team_name: teamName.trim(),
      contact_email: members[0].email.trim().toLowerCase(),
      contact_phone: contactPhone.trim() || members[0].phone.trim() || null,
      participants: participantsPayload,
    };

    const fingerprint = createPayloadFingerprint(payload);
    let idempKey: string;
    if (idempotencyRef.current && idempotencyRef.current.fingerprint === fingerprint) {
      idempKey = idempotencyRef.current.key;
    } else {
      idempKey = generateIdempotencyKey('team');
      idempotencyRef.current = { key: idempKey, fingerprint };
    }
    payload.idempotency_key = idempKey;

    setIsSubmitting(true);
    try {
      const response = await submitPublicRegistration(event.public_registration_key, payload);
      onSuccess(response);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setApiError('A conflicting team registration with this idempotency key was detected. Please check your submission.');
        } else if (err.status === 400 && err.detail.toLowerCase().includes('capacity')) {
          setApiError('Insufficient capacity for the full team. Event capacity is evaluated for all members together.');
        } else {
          setApiError(err.detail);
        }
      } else {
        setApiError('Unable to connect to registration service. Please retry.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card>
      <form onSubmit={handleSubmit} noValidate>
        <CardHeader
          title="Team Registration"
          subtitle={`Register your team of ${minSize} to ${maxSize} members. Each participant receives an individual admission pass.`}
        />
        <CardBody>
          {apiError && (
            <Alert variant="danger" title="Registration Error">
              {apiError}
            </Alert>
          )}

          {errors.teamSize && (
            <Alert variant="warning" title="Team Sizing">
              {errors.teamSize}
            </Alert>
          )}

          <TextInput
            id="team-name"
            label="Team Name"
            placeholder="e.g. CodeWarriors"
            value={teamName}
            onChange={(e) => {
              setTeamName(e.target.value);
              if (errors.teamName) setErrors((prev) => ({ ...prev, teamName: '' }));
            }}
            required
            error={errors.teamName}
            disabled={isSubmitting}
            leftAddon={<IconUsers size={16} />}
          />

          <TextInput
            id="team-contact-phone"
            type="tel"
            label="Primary Team Contact Phone"
            placeholder="e.g. +91 9876543210"
            helpText="Phone number for operational desk reach on event day."
            value={contactPhone}
            onChange={(e) => setContactPhone(e.target.value)}
            disabled={isSubmitting}
          />

          <div style={{ marginTop: 24, marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h4 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600 }}>Team Members</h4>
              <span style={{ fontSize: '0.85rem', color: 'var(--co-text-muted)' }}>
                {members.length} of max {maxSize} members
              </span>
            </div>
            <p style={{ margin: '4px 0 16px 0', fontSize: '0.85rem', color: 'var(--co-text-muted)' }}>
              Member 1 is designated as the Team Leader and primary contact. Each member will receive their own individual digital admission pass.
            </p>
          </div>

          {members.map((member, idx) => (
            <div
              key={idx}
              style={{
                padding: '16px',
                marginBottom: '16px',
                border: '1px solid var(--co-border-subtle)',
                borderRadius: 'var(--co-radius-lg)',
                backgroundColor: idx === 0 ? 'var(--co-primary-50)' : 'var(--co-bg-subtle)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {idx === 0 && <IconCrown size={16} style={{ color: 'var(--co-primary-600)' }} />}
                  <strong style={{ fontSize: '0.95rem' }}>
                    {idx === 0 ? 'Member 1 (Team Leader)' : `Member ${idx + 1}`}
                  </strong>
                </div>
                {idx >= minSize && (
                  <button
                    type="button"
                    className="co-btn co-btn-ghost co-btn-sm"
                    style={{ color: 'var(--co-danger-600)', padding: '2px 8px' }}
                    onClick={() => removeMember(idx)}
                    disabled={isSubmitting}
                    aria-label={`Remove member ${idx + 1}`}
                  >
                    <IconX size={14} />
                    <span>Remove</span>
                  </button>
                )}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
                <TextInput
                  id={`member-${idx}-name`}
                  label="Full Name"
                  placeholder="e.g. Diya Sen"
                  value={member.fullName}
                  onChange={(e) => handleMemberChange(idx, 'fullName', e.target.value)}
                  required
                  error={errors[`member_${idx}_fullName`]}
                  disabled={isSubmitting}
                />
                <TextInput
                  id={`member-${idx}-email`}
                  type="email"
                  label="Email Address"
                  placeholder="e.g. diya.sen@college.edu"
                  value={member.email}
                  onChange={(e) => handleMemberChange(idx, 'email', e.target.value)}
                  required
                  error={errors[`member_${idx}_email`]}
                  disabled={isSubmitting}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginTop: 8 }}>
                <TextInput
                  id={`member-${idx}-phone`}
                  type="tel"
                  label="Phone (Optional)"
                  placeholder="+91..."
                  value={member.phone}
                  onChange={(e) => handleMemberChange(idx, 'phone', e.target.value)}
                  disabled={isSubmitting}
                />
                <TextInput
                  id={`member-${idx}-college`}
                  label="College / Institution"
                  placeholder="Institution name"
                  value={member.college}
                  onChange={(e) => handleMemberChange(idx, 'college', e.target.value)}
                  disabled={isSubmitting}
                />
                <TextInput
                  id={`member-${idx}-student-id`}
                  label="Student ID"
                  placeholder="ID / Roll number"
                  value={member.studentId}
                  onChange={(e) => handleMemberChange(idx, 'studentId', e.target.value)}
                  disabled={isSubmitting}
                />
              </div>
            </div>
          ))}

          {members.length < maxSize && (
            <div style={{ marginBottom: 16 }}>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={addMember}
                disabled={isSubmitting || members.length >= maxSize}
              >
                + Add Another Member
              </Button>
            </div>
          )}

          <div
            style={{
              marginTop: 16,
              padding: 14,
              backgroundColor: 'var(--co-bg-subtle)',
              borderRadius: 'var(--co-radius-md)',
              border: errors.consent ? '1px solid var(--co-danger-500)' : '1px solid var(--co-border-subtle)',
            }}
          >
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer', fontSize: '0.875rem' }}>
              <input
                id="team-consent"
                type="checkbox"
                checked={consent}
                onChange={(e) => {
                  setConsent(e.target.checked);
                  if (errors.consent) setErrors((prev) => ({ ...prev, consent: '' }));
                }}
                disabled={isSubmitting}
                style={{ marginTop: 3 }}
              />
              <span style={{ color: 'var(--co-text-main)' }}>
                I confirm that all team members agreed to participate and understand that each attendee must check in individually at the desk on event day. *
              </span>
            </label>
            {errors.consent && (
              <p className="co-field-error" style={{ marginTop: 6, marginLeft: 24 }}>
                {errors.consent}
              </p>
            )}
          </div>
        </CardBody>
        <CardFooter>
          <Button
            type="submit"
            variant="primary"
            size="lg"
            isLoading={isSubmitting}
            loadingText="Securing Team Passes..."
            disabled={isSubmitting || event.registration_status !== 'open'}
            leftIcon={<IconUsers size={18} />}
          >
            Register Team ({members.length} Members)
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};
