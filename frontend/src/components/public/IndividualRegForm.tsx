import { useState, useRef, type FC, type FormEvent } from 'react';
import type { PublicEventDetails, PublicRegistrationRequest, PublicRegistrationResponse } from '../../api/types';
import { submitPublicRegistration } from '../../api/publicRegistration';
import { ApiError } from '../../api/client';
import { generateIdempotencyKey, createPayloadFingerprint } from '../../utils/idempotency';
import { Card, CardHeader, CardBody, CardFooter } from '../common/Card';
import { TextInput } from '../common/Input';
import { Button } from '../common/Button';
import { Alert } from '../common/Alert';
import { IconUser, IconTicket } from '../common/Icons';

interface IndividualRegFormProps {
  event: PublicEventDetails;
  onSuccess: (response: PublicRegistrationResponse) => void;
}

export const IndividualRegForm: FC<IndividualRegFormProps> = ({ event, onSuccess }) => {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [collegeName, setCollegeName] = useState('');
  const [studentId, setStudentId] = useState('');
  const [consent, setConsent] = useState(false);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Idempotency tracking: reuse key if payload unchanged on retry
  const idempotencyRef = useRef<{ key: string; fingerprint: string } | null>(null);

  const validate = (): boolean => {
    const errs: Record<string, string> = {};
    if (!fullName.trim()) errs.fullName = 'Full name is required.';
    if (!email.trim()) {
      errs.email = 'Email address is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      errs.email = 'Please provide a valid email address.';
    }
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

    const payload: PublicRegistrationRequest = {
      registration_type: 'solo',
      contact_email: email.trim().toLowerCase(),
      contact_phone: phone.trim() || null,
      participants: [
        {
          full_name: fullName.trim(),
          email: email.trim().toLowerCase(),
          phone_number: phone.trim() || null,
          college_name: collegeName.trim() || null,
          student_id: studentId.trim() || null,
          is_primary_contact: true,
          team_role: null,
        },
      ],
    };

    const fingerprint = createPayloadFingerprint(payload);
    let idempKey: string;
    if (idempotencyRef.current && idempotencyRef.current.fingerprint === fingerprint) {
      idempKey = idempotencyRef.current.key;
    } else {
      idempKey = generateIdempotencyKey('solo');
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
          setApiError('An identical or conflicting submission was detected. Please check your existing registration.');
        } else if (err.status === 400 && err.detail.toLowerCase().includes('capacity')) {
          setApiError('Event capacity has been reached. Please contact event staff or check back later.');
        } else {
          setApiError(err.detail);
        }
      } else {
        setApiError('Unable to connect to the registration service. Please verify your internet connection.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card>
      <form onSubmit={handleSubmit} noValidate>
        <CardHeader
          title="Individual Attendee Registration"
          subtitle="Reserve your digital admission pass for this event."
        />
        <CardBody>
          {apiError && (
            <Alert variant="danger" title="Registration Error">
              {apiError}
            </Alert>
          )}

          {!event.capacity_available && (
            <Alert variant="warning" title="Capacity Alert">
              This event is currently at maximum capacity. Submissions may be rejected by the server.
            </Alert>
          )}

          <TextInput
            id="solo-full-name"
            label="Full Name"
            placeholder="e.g. Maya Patel"
            value={fullName}
            onChange={(e) => {
              setFullName(e.target.value);
              if (errors.fullName) setErrors((prev) => ({ ...prev, fullName: '' }));
            }}
            required
            error={errors.fullName}
            disabled={isSubmitting}
            leftAddon={<IconUser size={16} />}
          />

          <TextInput
            id="solo-email"
            type="email"
            label="Email Address"
            placeholder="e.g. maya.patel@university.edu"
            helpText="Your admission pass reference and registration notices will be associated with this email."
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (errors.email) setErrors((prev) => ({ ...prev, email: '' }));
            }}
            required
            error={errors.email}
            disabled={isSubmitting}
          />

          <TextInput
            id="solo-phone"
            type="tel"
            label="Phone Number"
            placeholder="e.g. +91 9876543210"
            helpText="Optional emergency contact number for event day."
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            disabled={isSubmitting}
          />

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
            <TextInput
              id="solo-college"
              label="College / Institution"
              placeholder="e.g. Apex Institute of Technology"
              value={collegeName}
              onChange={(e) => setCollegeName(e.target.value)}
              disabled={isSubmitting}
            />
            <TextInput
              id="solo-student-id"
              label="Student ID / Roll Number"
              placeholder="e.g. CS-2026-089"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              disabled={isSubmitting}
            />
          </div>

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
                id="solo-consent"
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
                I agree to participate in this event and understand that individual check-in at the venue is required to claim entry. *
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
            loadingText="Securing Admission Pass..."
            disabled={isSubmitting || event.registration_status !== 'open'}
            leftIcon={<IconTicket size={18} />}
          >
            Complete Registration
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};
