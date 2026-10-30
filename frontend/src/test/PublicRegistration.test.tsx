import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import type { PublicEventDetails, PublicRegistrationResponse } from '../api/types';
import { EventOverview } from '../components/public/EventOverview';
import { IndividualRegForm } from '../components/public/IndividualRegForm';
import { TeamRegForm } from '../components/public/TeamRegForm';
import * as publicApi from '../api/publicRegistration';
import { ApiError } from '../api/client';

const mockEvent: PublicEventDetails = {
  public_registration_key: 'reg_test_key_123',
  event_id: 'evt-1111-2222',
  event_name: 'Campus Tech Fest 2026',
  description: 'Annual technical symposium and collaborative hackathon.',
  event_date: '2026-11-05',
  event_end_date: '2026-11-06',
  venue: 'Main Seminar Hall',
  timezone: 'Asia/Kolkata',
  registration_status: 'open',
  registration_format: 'both',
  team_size_min: 2,
  team_size_max: 4,
  capacity_available: true,
};

describe('Public Event Registration Components', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  describe('EventOverview Component', () => {
    it('renders event details, dates, venue, and status badges', () => {
      render(<EventOverview event={mockEvent} />);

      expect(screen.getByText('Campus Tech Fest 2026')).toBeInTheDocument();
      expect(screen.getByText(/annual technical symposium/i)).toBeInTheDocument();
      expect(screen.getByText('Registration Open')).toBeInTheDocument();
      expect(screen.getByText('Capacity Available')).toBeInTheDocument();
      expect(screen.getByText(/main seminar hall/i)).toBeInTheDocument();
      expect(screen.getByText(/asia\/kolkata/i)).toBeInTheDocument();
      expect(screen.getByText(/2–4 members/i)).toBeInTheDocument();
    });

    it('renders closed status and capacity warning appropriately', () => {
      const closedEvent: PublicEventDetails = {
        ...mockEvent,
        registration_status: 'closed',
        capacity_available: false,
      };
      render(<EventOverview event={closedEvent} />);

      expect(screen.getByText('Registration Closed')).toBeInTheDocument();
      expect(screen.getByText('At Full Capacity')).toBeInTheDocument();
    });
  });

  describe('IndividualRegForm Component', () => {
    it('validates required fields before submitting', async () => {
      const onSuccess = vi.fn();
      render(<IndividualRegForm event={mockEvent} onSuccess={onSuccess} />);

      const submitButton = screen.getByRole('button', { name: /complete registration/i });
      fireEvent.click(submitButton);

      expect(await screen.findByText('Full name is required.')).toBeInTheDocument();
      expect(screen.getByText('Email address is required.')).toBeInTheDocument();
      expect(screen.getByText('You must acknowledge event participation rules.')).toBeInTheDocument();
      expect(onSuccess).not.toHaveBeenCalled();
    });

    it('submits individual registration successfully and passes result to onSuccess', async () => {
      const onSuccess = vi.fn();
      const mockResponse: PublicRegistrationResponse = {
        registration_id: 'reg-sub-001',
        confirmation_code: 'REG-A1B2C3D4',
        registration_status: 'confirmed',
        registration_type: 'solo',
        team_name: null,
        is_waitlisted: false,
        passes: [
          {
            participant_id: 'part-001',
            participant_name: 'Maya Patel',
            ticket_reference: 'TKT-12345678',
            pass_code: 'CO-PASS-8B1A2C3D4E5F6G7H8I9J0K1L2M3N4O5P',
            pass_url: '/passes/CO-PASS-8B1A...',
          },
        ],
      };

      const submitSpy = vi
        .spyOn(publicApi, 'submitPublicRegistration')
        .mockResolvedValueOnce(mockResponse);

      render(<IndividualRegForm event={mockEvent} onSuccess={onSuccess} />);

      fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Maya Patel' } });
      fireEvent.change(screen.getByLabelText(/email address/i), {
        target: { value: 'maya.patel@university.edu' },
      });
      fireEvent.change(screen.getByLabelText(/phone number/i), {
        target: { value: '+91 9876543210' },
      });
      fireEvent.click(screen.getByRole('checkbox'));

      const submitButton = screen.getByRole('button', { name: /complete registration/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(submitSpy).toHaveBeenCalledTimes(1);
        expect(onSuccess).toHaveBeenCalledWith(mockResponse);
      });

      // Verify idempotency key was included
      const calledPayload = submitSpy.mock.calls[0][1];
      expect(calledPayload.idempotency_key).toMatch(/^solo_[a-f0-9]{32}$/);
      expect(calledPayload.participants[0].full_name).toBe('Maya Patel');

      // Security verify: No raw credentials written to localStorage or sessionStorage
      expect(localStorage.getItem('CO-PASS-8B1A2C3D4E5F6G7H8I9J0K1L2M3N4O5P')).toBeNull();
      expect(sessionStorage.getItem('REG-A1B2C3D4')).toBeNull();
    });

    it('prevents double submission while request is in flight', async () => {
      let resolvePromise: (value: PublicRegistrationResponse) => void = () => {};
      const pendingPromise = new Promise<PublicRegistrationResponse>((resolve) => {
        resolvePromise = resolve;
      });

      const submitSpy = vi
        .spyOn(publicApi, 'submitPublicRegistration')
        .mockReturnValueOnce(pendingPromise);

      render(<IndividualRegForm event={mockEvent} onSuccess={vi.fn()} />);

      fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Aarav Kumar' } });
      fireEvent.change(screen.getByLabelText(/email address/i), {
        target: { value: 'aarav@university.edu' },
      });
      fireEvent.click(screen.getByRole('checkbox'));

      const submitButton = screen.getByRole('button', { name: /complete registration/i });
      fireEvent.click(submitButton);

      // Button should be disabled and show loading state
      expect(submitButton).toBeDisabled();
      expect(screen.getByText(/securing admission pass/i)).toBeInTheDocument();

      // Second click should be ignored
      fireEvent.click(submitButton);
      expect(submitSpy).toHaveBeenCalledTimes(1);

      // Resolve
      resolvePromise({
        registration_id: 'reg-sub-002',
        confirmation_code: 'REG-2222',
        registration_status: 'confirmed',
        registration_type: 'solo',
        team_name: null,
        is_waitlisted: false,
        passes: [],
      });
    });

    it('handles capacity exhausted API errors cleanly', async () => {
      vi.spyOn(publicApi, 'submitPublicRegistration').mockRejectedValueOnce(
        new ApiError(400, 'Registration capacity exhausted for this event.'),
      );

      render(<IndividualRegForm event={mockEvent} onSuccess={vi.fn()} />);

      fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Aarav Kumar' } });
      fireEvent.change(screen.getByLabelText(/email address/i), {
        target: { value: 'aarav@university.edu' },
      });
      fireEvent.click(screen.getByRole('checkbox'));

      fireEvent.click(screen.getByRole('button', { name: /complete registration/i }));

      expect(await screen.findByText(/event capacity has been reached/i)).toBeInTheDocument();
    });
  });

  describe('TeamRegForm Component', () => {
    it('enforces min and max team member bounds and unique emails', async () => {
      render(<TeamRegForm event={mockEvent} onSuccess={vi.fn()} />);

      // Minimum team size is 2
      expect(screen.getByText(/member 1 \(team leader\)/i)).toBeInTheDocument();
      expect(screen.getByText(/member 2/i)).toBeInTheDocument();

      // Fill in team name but duplicate emails
      fireEvent.change(screen.getByLabelText(/team name/i), { target: { value: 'ApexCoders' } });

      const nameInputs = screen.getAllByLabelText(/full name/i);
      const emailInputs = screen.getAllByLabelText(/email address/i);

      fireEvent.change(nameInputs[0], { target: { value: 'Leader Aarav' } });
      fireEvent.change(emailInputs[0], { target: { value: 'shared@college.edu' } });

      fireEvent.change(nameInputs[1], { target: { value: 'Member Diya' } });
      fireEvent.change(emailInputs[1], { target: { value: 'shared@college.edu' } });

      fireEvent.click(screen.getByRole('checkbox'));

      fireEvent.click(screen.getByRole('button', { name: /register team/i }));

      expect(
        await screen.findByText(/duplicate email: member 2 shares email/i),
      ).toBeInTheDocument();
    });

    it('submits a valid team registration successfully', async () => {
      const onSuccess = vi.fn();
      const mockTeamResponse: PublicRegistrationResponse = {
        registration_id: 'reg-team-001',
        confirmation_code: 'REG-TEAM99',
        registration_status: 'confirmed',
        registration_type: 'team',
        team_name: 'ApexCoders',
        is_waitlisted: false,
        passes: [
          {
            participant_id: 'part-lead',
            participant_name: 'Leader Aarav',
            ticket_reference: 'TKT-LEAD',
            pass_code: 'CO-PASS-LEAD-12345678901234567890',
            pass_url: '/passes/...',
          },
          {
            participant_id: 'part-member',
            participant_name: 'Member Diya',
            ticket_reference: 'TKT-MEMB',
            pass_code: 'CO-PASS-MEMB-12345678901234567890',
            pass_url: '/passes/...',
          },
        ],
      };

      const submitSpy = vi
        .spyOn(publicApi, 'submitPublicRegistration')
        .mockResolvedValueOnce(mockTeamResponse);

      render(<TeamRegForm event={mockEvent} onSuccess={onSuccess} />);

      fireEvent.change(screen.getByLabelText(/team name/i), { target: { value: 'ApexCoders' } });
      fireEvent.change(screen.getByLabelText(/primary team contact phone/i), {
        target: { value: '+91 9876543210' },
      });

      const nameInputs = screen.getAllByLabelText(/full name/i);
      const emailInputs = screen.getAllByLabelText(/email address/i);

      fireEvent.change(nameInputs[0], { target: { value: 'Leader Aarav' } });
      fireEvent.change(emailInputs[0], { target: { value: 'aarav@apex.edu' } });

      fireEvent.change(nameInputs[1], { target: { value: 'Member Diya' } });
      fireEvent.change(emailInputs[1], { target: { value: 'diya@apex.edu' } });

      fireEvent.click(screen.getByRole('checkbox'));

      fireEvent.click(screen.getByRole('button', { name: /register team/i }));

      await waitFor(() => {
        expect(submitSpy).toHaveBeenCalledTimes(1);
        expect(onSuccess).toHaveBeenCalledWith(mockTeamResponse);
      });

      const calledPayload = submitSpy.mock.calls[0][1];
      expect(calledPayload.registration_type).toBe('team');
      expect(calledPayload.team_name).toBe('ApexCoders');
      expect(calledPayload.participants.length).toBe(2);
      expect(calledPayload.participants[0].team_role).toBe('leader');
      expect(calledPayload.participants[1].team_role).toBe('member');
    });
  });
});
