import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { ToastProvider, useToast } from '../components/common/Toast';
import { Skeleton, CardSkeleton, TableSkeleton } from '../components/common/Skeleton';
import { CheckInDesk } from '../components/staff/CheckInDesk';
import * as staffApi from '../api/staffOperations';

const ToastTestConsumer = () => {
  const { showToast } = useToast();
  return (
    <div>
      <button
        type="button"
        onClick={() => showToast('success', 'Test Success', 'Operation completed.')}
      >
        Trigger Toast
      </button>
      <button
        type="button"
        onClick={() => showToast('error', 'Critical Error', 'Something broke.')}
      >
        Trigger Error Toast
      </button>
    </div>
  );
};

describe('Premium Design System & Interaction Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('Toast Notification System', () => {
    it('renders toast with correct message and auto-dismisses', () => {
      vi.useFakeTimers();

      render(
        <ToastProvider>
          <ToastTestConsumer />
        </ToastProvider>,
      );

      const triggerBtn = screen.getByRole('button', { name: /trigger toast/i });
      fireEvent.click(triggerBtn);

      expect(screen.getByText('Test Success')).toBeInTheDocument();
      expect(screen.getByText('Operation completed.')).toBeInTheDocument();

      // Fast-forward 4500ms
      act(() => {
        vi.advanceTimersByTime(4500);
      });

      expect(screen.queryByText('Test Success')).toBeNull();

      vi.useRealTimers();
    });

    it('allows manual dismissal of toast notifications', () => {
      render(
        <ToastProvider>
          <ToastTestConsumer />
        </ToastProvider>,
      );

      fireEvent.click(screen.getByRole('button', { name: /trigger error toast/i }));
      expect(screen.getByText('Critical Error')).toBeInTheDocument();

      const dismissBtn = screen.getByRole('button', { name: /dismiss notification/i });
      fireEvent.click(dismissBtn);

      expect(screen.queryByText('Critical Error')).toBeNull();
    });
  });

  describe('Skeleton Loaders', () => {
    it('renders basic Skeleton with aria-hidden="true"', () => {
      const { container } = render(<Skeleton width="100px" height="20px" />);
      const skeletonEl = container.querySelector('.co-skeleton');
      expect(skeletonEl).toBeInTheDocument();
      expect(skeletonEl).toHaveAttribute('aria-hidden', 'true');
    });

    it('renders CardSkeleton with aria-busy="true"', () => {
      render(<CardSkeleton lines={3} />);
      const busyCard = screen.getByLabelText(/loading content/i);
      expect(busyCard).toHaveAttribute('aria-busy', 'true');
    });

    it('renders TableSkeleton with rows and columns', () => {
      render(<TableSkeleton rows={4} columns={5} />);
      const tableWrapper = screen.getByLabelText(/loading table records/i);
      expect(tableWrapper).toHaveAttribute('aria-busy', 'true');
      expect(tableWrapper.querySelectorAll('tbody tr').length).toBe(4);
    });
  });

  describe('Check-In Desk Keyboard Ergonomics', () => {
    it('focuses pass code input when pressing "/" key outside of an input', () => {
      render(
        <ToastProvider>
          <CheckInDesk orgId="org-1" eventId="evt-1" onCheckInSuccess={vi.fn()} />
        </ToastProvider>,
      );

      const passInput = screen.getByLabelText(/scan or enter admission pass code/i);

      // Blur input
      passInput.blur();
      expect(document.activeElement).not.toBe(passInput);

      // Press '/'
      fireEvent.keyDown(window, { key: '/' });
      expect(document.activeElement).toBe(passInput);
    });

    it('supports arrow key navigation and Enter check-in for search candidate results', async () => {
      const mockCandidates = [
        {
          participant_id: 'p-cand-1',
          full_name: 'Aarav Sharma',
          email_masked: 'a***a@apex.edu',
          team_name: 'ByteCrafters',
          student_id: 'CS-001',
          ticket_reference: 'TKT-001',
          can_check_in: true,
          attendance_status: 'registered',
        },
        {
          participant_id: 'p-cand-2',
          full_name: 'Diya Sen',
          email_masked: 'd***n@apex.edu',
          team_name: 'ByteCrafters',
          student_id: 'CS-002',
          ticket_reference: 'TKT-002',
          can_check_in: true,
          attendance_status: 'registered',
        },
      ];

      vi.spyOn(staffApi, 'lookupCheckInCandidates').mockResolvedValue(mockCandidates);
      const checkInSpy = vi.spyOn(staffApi, 'performCheckIn').mockResolvedValue({
        check_in_id: 'chk-cand-1',
        status: 'verified',
        participant_id: 'p-cand-1',
        participant_name: 'Aarav Sharma',
        team_name: 'ByteCrafters',
        checked_in_at: '2026-10-30T10:00:00Z',
        station_id: 'DESK-LOOKUP',
        message: 'Verified.',
      });

      render(
        <ToastProvider>
          <CheckInDesk orgId="org-1" eventId="evt-1" onCheckInSuccess={vi.fn()} />
        </ToastProvider>,
      );

      const searchInput = screen.getByLabelText(/search by name, student id/i);
      fireEvent.change(searchInput, { target: { value: 'Aarav' } });

      expect(await screen.findByText('Aarav Sharma')).toBeInTheDocument();
      expect(screen.getByText('Diya Sen')).toBeInTheDocument();

      // Press ArrowDown to highlight first candidate
      fireEvent.keyDown(searchInput, { key: 'ArrowDown' });

      // Press Enter to check in highlighted candidate
      fireEvent.keyDown(searchInput, { key: 'Enter' });

      expect(checkInSpy).toHaveBeenCalledWith(
        'org-1',
        'evt-1',
        expect.objectContaining({ participant_id: 'p-cand-1', method: 'manual_search' }),
        expect.anything(),
      );
    });
  });
});

