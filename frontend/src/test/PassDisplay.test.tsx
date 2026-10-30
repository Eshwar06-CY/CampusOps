import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { PublicRegistrationResponse, PublicEventDetails, IssuedPass } from '../api/types';
import { PublicPassDisplay } from '../components/public/PublicPassDisplay';
import { RegistrationConfirmation } from '../components/public/RegistrationConfirmation';

const mockEvent: PublicEventDetails = {
  public_registration_key: 'reg_test_key_123',
  event_id: 'evt-1111-2222',
  event_name: 'Hackathon 2026',
  description: 'Hackathon event.',
  event_date: '2026-11-05',
  event_end_date: null,
  venue: 'Lab 4',
  timezone: 'Asia/Kolkata',
  registration_status: 'open',
  registration_format: 'both',
  team_size_min: 2,
  team_size_max: 4,
  capacity_available: true,
};

describe('Admission Pass & Confirmation Display', () => {
  it('renders an individual pass with scannable QR code and ticket reference', () => {
    const mockPass: IssuedPass = {
      participant_id: 'p-1',
      participant_name: 'Aarav Sharma',
      ticket_reference: 'TKT-A1B2C3D4',
      pass_code: 'CO-PASS-8B1A2C3D4E5F6G7H8I9J0K1L2M3N4O5P',
      pass_url: '/passes/...',
    };

    render(<PublicPassDisplay pass={mockPass} eventName="Hackathon 2026" />);

    expect(screen.getByText('Aarav Sharma')).toBeInTheDocument();
    expect(screen.getByText('TKT-A1B2C3D4')).toBeInTheDocument();
    expect(screen.getByText(/CO-PASS-8B1A2C3D4E5F6G7H8I9J0K1L2M3N4O5P/)).toBeInTheDocument();
    expect(screen.getByTestId('qr-code-box')).toBeInTheDocument();
    expect(screen.getByText('Active Pass')).toBeInTheDocument();
  });

  it('renders a separate pass for each team member in RegistrationConfirmation', () => {
    const mockRegistration: PublicRegistrationResponse = {
      registration_id: 'reg-team-123',
      confirmation_code: 'REG-CONFIRM-99',
      registration_status: 'confirmed',
      registration_type: 'team',
      team_name: 'CyberKnights',
      is_waitlisted: false,
      passes: [
        {
          participant_id: 'p-lead',
          participant_name: 'Lead Aarav',
          ticket_reference: 'TKT-LEAD-01',
          pass_code: 'CO-PASS-LEAD-0001',
          pass_url: '/passes/...',
        },
        {
          participant_id: 'p-member',
          participant_name: 'Member Diya',
          ticket_reference: 'TKT-MEMB-02',
          pass_code: 'CO-PASS-MEMB-0002',
          pass_url: '/passes/...',
        },
      ],
    };

    render(
      <RegistrationConfirmation
        registration={mockRegistration}
        event={mockEvent}
        onReset={() => {}}
      />,
    );

    expect(screen.getByText('REG-CONFIRM-99')).toBeInTheDocument();
    expect(screen.getAllByText('CyberKnights').length).toBe(3);

    // Verify separate cards for both members
    expect(screen.getByTestId('pass-card-p-lead')).toBeInTheDocument();
    expect(screen.getByTestId('pass-card-p-member')).toBeInTheDocument();
    expect(screen.getByText('Lead Aarav')).toBeInTheDocument();
    expect(screen.getByText('Member Diya')).toBeInTheDocument();
    expect(screen.getByText('TKT-LEAD-01')).toBeInTheDocument();
    expect(screen.getByText('TKT-MEMB-02')).toBeInTheDocument();

    // Verify individual check-in notice
    expect(
      screen.getByText(/every participant must present their individual pass/i),
    ).toBeInTheDocument();
  });

  it('handles safe recovery state when one-time pass code is redacted on reloads/replays', () => {
    const redactedPass: IssuedPass = {
      participant_id: 'p-redacted',
      participant_name: 'Karan Mehra',
      ticket_reference: 'TKT-REPLAY-88',
      pass_code: '<REDACTED_AFTER_ISSUANCE>',
      pass_url: '/passes/...',
    };

    render(<PublicPassDisplay pass={redactedPass} eventName="Hackathon 2026" />);

    expect(screen.getByText('Karan Mehra')).toBeInTheDocument();
    expect(screen.getByText('TKT-REPLAY-88')).toBeInTheDocument();
    expect(screen.getByText('Pass Code Secured')).toBeInTheDocument();
    expect(
      screen.getByText(/high-entropy admission passes are generated once upon issuance/i),
    ).toBeInTheDocument();
    // QR code box should not be rendered when raw code is redacted
    expect(screen.queryByTestId('qr-code-box')).toBeNull();
  });
});
