import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import type {
  StaffParticipantRosterItemResponse,
  CheckInResponse,
  CheckInLookupItemResponse,
  AttendanceSummaryResponse,
} from '../api/types';
import { AuthUnavailableNotice } from '../components/staff/AuthUnavailableNotice';
import { CheckInDesk } from '../components/staff/CheckInDesk';
import { ParticipantRoster } from '../components/staff/ParticipantRoster';
import { CheckInCorrectionModal } from '../components/staff/CheckInCorrectionModal';
import { AttendanceSummaryCard } from '../components/staff/AttendanceSummaryCard';
import * as staffApi from '../api/staffOperations';

describe('Staff Event Operations Components', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('AuthUnavailableNotice Component', () => {
    it('renders fail-closed authentication notice without mock login or hardcoded credentials', () => {
      render(<AuthUnavailableNotice />);

      expect(screen.getByText('Staff Authentication Required')).toBeInTheDocument();
      expect(
        screen.getByText(/identity provider not configured \(http 401\)/i),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/deny-by-default role-based access control/i),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/prospective attendees do not require a staff account/i),
      ).toBeInTheDocument();
    });
  });

  describe('CheckInDesk Component', () => {
    it('handles successful individual check-in via pass code', async () => {
      const onCheckInSuccess = vi.fn();
      const mockSuccess: CheckInResponse = {
        check_in_id: 'chk-111',
        status: 'verified',
        participant_id: 'part-1',
        participant_name: 'Aarav Sharma',
        team_name: 'ByteCrafters',
        checked_in_at: '2026-10-29T10:15:00Z',
        station_id: 'DESK-FRONT',
        message: 'Check-in verified successfully.',
      };

      const checkInSpy = vi
        .spyOn(staffApi, 'performCheckIn')
        .mockResolvedValueOnce(mockSuccess);

      render(
        <CheckInDesk
          orgId="org-1"
          eventId="evt-1"
          onCheckInSuccess={onCheckInSuccess}
        />,
      );

      const passInput = screen.getByLabelText(/scan or enter admission pass code/i);
      fireEvent.change(passInput, {
        target: { value: 'CO-PASS-8B1A2C3D4E5F6G7H8I9J0K1L2M3N4O5P' },
      });

      const submitBtn = screen.getByRole('button', { name: /verify & check in/i });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(checkInSpy).toHaveBeenCalledTimes(1);
        expect(onCheckInSuccess).toHaveBeenCalled();
      });

      expect(
        screen.getByText(/aarav sharma \(bytecrafters\) checked in successfully/i),
      ).toBeInTheDocument();
    });

    it('handles duplicate scan idempotency correctly without inflating counts', async () => {
      const mockDuplicate: CheckInResponse = {
        check_in_id: 'chk-111',
        status: 'already_checked_in',
        participant_id: 'part-1',
        participant_name: 'Aarav Sharma',
        team_name: 'ByteCrafters',
        checked_in_at: '2026-10-29T10:15:00Z',
        station_id: 'DESK-FRONT',
        message: 'Attendee was already checked in at 10:15:00.',
      };

      vi.spyOn(staffApi, 'performCheckIn').mockResolvedValueOnce(mockDuplicate);

      render(
        <CheckInDesk
          orgId="org-1"
          eventId="evt-1"
          onCheckInSuccess={vi.fn()}
        />,
      );

      fireEvent.change(screen.getByLabelText(/scan or enter admission pass code/i), {
        target: { value: 'CO-PASS-8B1A2C3D4E5F6G7H8I9J0K1L2M3N4O5P' },
      });
      fireEvent.click(screen.getByRole('button', { name: /verify & check in/i }));

      expect(await screen.findByText('Attendee Already Present')).toBeInTheDocument();
      expect(
        screen.getByText(/no duplicate attendance recorded/i),
      ).toBeInTheDocument();
    });

    it('searches candidates and allows direct check-in from search results', async () => {
      const mockCandidates: CheckInLookupItemResponse[] = [
        {
          participant_id: 'cand-1',
          full_name: 'Diya Sen',
          email_masked: 'd***n@apex.edu',
          team_name: 'CodeWarriors',
          student_id: 'APEX-092',
          ticket_reference: 'TKT-DIYA-01',
          can_check_in: true,
          attendance_status: 'registered',
        },
      ];

      vi.spyOn(staffApi, 'lookupCheckInCandidates').mockResolvedValueOnce(mockCandidates);
      const checkInSpy = vi.spyOn(staffApi, 'performCheckIn').mockResolvedValueOnce({
        check_in_id: 'chk-222',
        status: 'verified',
        participant_id: 'cand-1',
        participant_name: 'Diya Sen',
        team_name: 'CodeWarriors',
        checked_in_at: '2026-10-29T10:20:00Z',
        station_id: 'DESK-LOOKUP',
        message: 'Verified.',
      });

      render(
        <CheckInDesk
          orgId="org-1"
          eventId="evt-1"
          onCheckInSuccess={vi.fn()}
        />,
      );

      const searchInput = screen.getByLabelText(/search by name, student id/i);
      fireEvent.change(searchInput, { target: { value: 'Diya' } });

      // Fast-forward debounce
      await waitFor(() => {
        expect(screen.getByText('Diya Sen')).toBeInTheDocument();
        expect(screen.getByText(/team: codewarriors/i)).toBeInTheDocument();
        expect(screen.getByText(/d\*\*\*n@apex.edu/i)).toBeInTheDocument();
      });

      // Click Check In on candidate row
      const checkInRowBtn = screen.getByRole('button', { name: /^check in$/i });
      fireEvent.click(checkInRowBtn);

      await waitFor(() => {
        expect(checkInSpy).toHaveBeenCalledWith(
          'org-1',
          'evt-1',
          expect.objectContaining({ participant_id: 'cand-1', method: 'manual_search' }),
          expect.anything(),
        );
      });
    });
  });

  describe('ParticipantRoster Component', () => {
    it('displays masked contact information and proper action buttons', () => {
      const mockRoster: StaffParticipantRosterItemResponse[] = [
        {
          participant_id: 'p-1',
          full_name: 'Aarav Sharma',
          email: 'a***a@domain.edu',
          phone_number: '******3210',
          college_name: 'Apex Institute',
          student_id: 'CS-001',
          team_name: 'ByteCrafters',
          role_in_team: 'leader',
          attendance_status: 'registered',
          ticket_status: 'active',
          ticket_reference: 'TKT-1111',
          check_in_id: null,
          checked_in_at: null,
        },
        {
          participant_id: 'p-2',
          full_name: 'Diya Sen',
          email: 'd***n@domain.edu',
          phone_number: '******9999',
          college_name: 'Apex Institute',
          student_id: 'CS-002',
          team_name: 'ByteCrafters',
          role_in_team: 'member',
          attendance_status: 'checked_in',
          ticket_status: 'used',
          ticket_reference: 'TKT-2222',
          check_in_id: 'chk-diya-1',
          checked_in_at: '2026-10-29T10:05:00Z',
        },
      ];

      render(
        <ParticipantRoster
          orgId="org-1"
          eventId="evt-1"
          roster={mockRoster}
          isLoading={false}
          error={null}
          searchTerm=""
          onSearchChange={vi.fn()}
          statusFilter=""
          onStatusFilterChange={vi.fn()}
          onRefresh={vi.fn()}
          onOpenVoidModal={vi.fn()}
          onOpenReissueModal={vi.fn()}
        />,
      );

      // Verify contact fields are masked
      expect(screen.getByText('a***a@domain.edu')).toBeInTheDocument();
      expect(screen.getByText('******3210')).toBeInTheDocument();
      expect(screen.getByText('d***n@domain.edu')).toBeInTheDocument();
      expect(screen.getByText('******9999')).toBeInTheDocument();

      // Registered row should have Check In button
      expect(screen.getByRole('button', { name: /^check in$/i })).toBeInTheDocument();

      // Checked-in row should have Void Check-In button
      expect(screen.getByRole('button', { name: /void check-in/i })).toBeInTheDocument();
    });
  });

  describe('CheckInCorrectionModal Component', () => {
    it('requires a mandatory audit reason of at least 10 characters', async () => {
      const onSuccess = vi.fn();
      const mockParticipant: StaffParticipantRosterItemResponse = {
        participant_id: 'p-2',
        full_name: 'Diya Sen',
        email: 'd***n@domain.edu',
        phone_number: null,
        college_name: null,
        student_id: null,
        team_name: null,
        role_in_team: null,
        attendance_status: 'checked_in',
        ticket_status: 'used',
        ticket_reference: 'TKT-2222',
        check_in_id: 'chk-diya-1',
        checked_in_at: '2026-10-29T10:05:00Z',
      };

      const voidSpy = vi.spyOn(staffApi, 'voidCheckIn').mockResolvedValueOnce({
        check_in_id: 'chk-diya-1',
        participant_id: 'p-2',
        status: 'voided',
        voided_at: '2026-10-29T10:30:00Z',
        reason: 'Accidental desk check-in of wrong attendee',
        message: 'Voided successfully.',
      });

      render(
        <CheckInCorrectionModal
          isOpen={true}
          onClose={vi.fn()}
          orgId="org-1"
          eventId="evt-1"
          participant={mockParticipant}
          onSuccess={onSuccess}
        />,
      );

      const confirmBtn = screen.getByRole('button', { name: /confirm & void attendance/i });
      expect(confirmBtn).toBeDisabled();

      const reasonInput = screen.getByLabelText(/mandatory audit reason/i);
      // Short reason (< 10 chars)
      fireEvent.change(reasonInput, { target: { value: 'mistake' } });
      expect(confirmBtn).toBeDisabled();

      // Valid reason (>= 10 chars)
      fireEvent.change(reasonInput, {
        target: { value: 'Accidental desk check-in of wrong attendee' },
      });
      expect(confirmBtn).toBeEnabled();

      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(voidSpy).toHaveBeenCalledWith(
          'org-1',
          'evt-1',
          'chk-diya-1',
          'Accidental desk check-in of wrong attendee',
          expect.anything(),
        );
        expect(onSuccess).toHaveBeenCalled();
      });
    });
  });

  describe('AttendanceSummaryCard Component', () => {
    it('displays operational metrics, capacity ratio, and team breakdown', () => {
      const mockSummary: AttendanceSummaryResponse = {
        event_id: 'evt-1',
        capacity_limit: 100,
        current_confirmed_count: 50,
        current_attended_count: 35,
        attendance_percentage: 70.0,
        total_individual_registrations: 10,
        total_team_registrations: 10,
        total_participants_registered: 50,
        teams_fully_attended: 6,
        teams_partially_attended: 3,
        teams_absent: 1,
      };

      render(
        <AttendanceSummaryCard
          summary={mockSummary}
          isLoading={false}
          onRefresh={vi.fn()}
        />,
      );

      expect(screen.getByText('35')).toBeInTheDocument();
      expect(screen.getByText('/ 50 Confirmed')).toBeInTheDocument();
      expect(screen.getByText('70.0% Present')).toBeInTheDocument();
      expect(screen.getByText('50 Slots Remaining')).toBeInTheDocument();
      expect(screen.getByText('10 Solo · 10 Teams')).toBeInTheDocument();
      expect(screen.getByText('Fully Present:')).toBeInTheDocument();
      expect(screen.getByText('6')).toBeInTheDocument();
      expect(screen.getByText('Partially Present:')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
    });
  });
});

