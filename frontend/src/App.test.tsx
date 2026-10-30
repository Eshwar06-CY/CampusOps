import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import App from './App';
import * as publicApi from './api/publicRegistration';
import * as staffApi from './api/staffOperations';
import * as orgApi from './api/organizations';
import { ApiError } from './api/client';
import type { PublicEventDetails } from './api/types';

const mockEvent: PublicEventDetails = {
  public_registration_key: 'reg_demo_key',
  event_id: 'evt-1111',
  event_name: 'CampusOps Hackathon 2026',
  description: 'Hackathon description.',
  event_date: '2026-11-10',
  event_end_date: null,
  venue: 'Main Hall',
  timezone: 'Asia/Kolkata',
  registration_status: 'open',
  registration_format: 'both',
  team_size_min: 2,
  team_size_max: 4,
  capacity_available: true,
};

describe('CampusOps Application Shell', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(publicApi, 'getPublicEventDetails').mockResolvedValue(mockEvent);
    // Staff APIs reject with 401 when unauthenticated
    vi.spyOn(staffApi, 'getRegistrationSettings').mockRejectedValue(
      new ApiError(401, 'Authentication token required.'),
    );
    vi.spyOn(staffApi, 'getAttendanceSummary').mockRejectedValue(
      new ApiError(401, 'Authentication token required.'),
    );
    vi.spyOn(staffApi, 'listParticipants').mockRejectedValue(
      new ApiError(401, 'Authentication token required.'),
    );
    // Workspace APIs reject with 401 when unauthenticated
    vi.spyOn(orgApi, 'getCurrentUser').mockRejectedValue(
      new ApiError(401, 'Authentication token required.'),
    );
    vi.spyOn(orgApi, 'listOrganizations').mockRejectedValue(
      new ApiError(401, 'Authentication token required.'),
    );
  });

  it('renders the CampusOps brand and Slice 5D badge', async () => {
    render(<App />);
    expect(screen.getAllByText('CampusOps').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Slice 5D')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('CampusOps Hackathon 2026')).toBeInTheDocument();
    });
  });

  it('provides navigation between Public Registration and Staff Event Desk', async () => {
    render(<App />);

    const publicBtn = screen.getByRole('button', { name: /public registration/i });
    const staffBtn = screen.getByRole('button', { name: /staff event desk/i });

    expect(publicBtn).toBeInTheDocument();
    expect(staffBtn).toBeInTheDocument();

    // Default mode is public
    expect(publicBtn).toHaveAttribute('aria-pressed', 'true');
    expect(staffBtn).toHaveAttribute('aria-pressed', 'false');

    // Switch to Staff mode
    fireEvent.click(staffBtn);
    expect(staffBtn).toHaveAttribute('aria-pressed', 'true');
    expect(publicBtn).toHaveAttribute('aria-pressed', 'false');

    // Staff mode shows workspace context and authentication boundary notice
    await waitFor(() => {
      expect(screen.getByText(/staff authentication required/i)).toBeInTheDocument();
      expect(screen.getByText(/identity provider not configured/i)).toBeInTheDocument();
    });
  });

  it('provides navigation to Workspace & Team mode and fails closed with Auth notice', async () => {
    render(<App />);

    const workspaceBtn = screen.getByRole('button', { name: /workspace & team/i });
    expect(workspaceBtn).toBeInTheDocument();

    fireEvent.click(workspaceBtn);
    expect(workspaceBtn).toHaveAttribute('aria-pressed', 'true');

    // Fails closed (401) without authentication token
    await waitFor(() => {
      expect(screen.getByText(/staff authentication required/i)).toBeInTheDocument();
    });
  });
});
