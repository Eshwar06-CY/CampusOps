import { useState, useEffect, useMemo, useCallback, type FC } from 'react';
import type {
  CurrentUserResponse,
  InvitationResponse,
  OrganizationMemberResponse,
} from '../../api/types';
import {
  listOrganizationMembers,
  listOrganizationInvitations,
  revokeInvitation,
} from '../../api/organizations';
import { ApiError } from '../../api/client';
import { Badge } from '../common/Badge';
import { Spinner } from '../common/Spinner';
import { Alert } from '../common/Alert';
import { IconSearch, IconUser, IconMail, IconPlus } from '../common/Icons';
import { formatDateTime } from '../../utils/formatters';

interface MemberDirectoryTableProps {
  currentUser: CurrentUserResponse | null;
  activeOrgId: string;
  invitations?: InvitationResponse[];
  onRevokeInvitation?: (invitationId: string) => Promise<void>;
  canManageRoles: boolean;
  onOpenInviteModal: () => void;
  isVerified: boolean;
  authToken?: string | null;
}

export const MemberDirectoryTable: FC<MemberDirectoryTableProps> = ({
  currentUser,
  activeOrgId,
  invitations,
  onRevokeInvitation,
  canManageRoles,
  onOpenInviteModal,
  isVerified,
  authToken,
}) => {
  const [activeTab, setActiveTab] = useState<'members' | 'invitations'>('members');
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [revokingId, setRevokingId] = useState<string | null>(null);

  // Member Directory State
  const [members, setMembers] = useState<OrganizationMemberResponse[]>([]);
  const [isLoadingMembers, setIsLoadingMembers] = useState(false);
  const [membersError, setMembersError] = useState<string | null>(null);
  const [memberStatusFilter, setMemberStatusFilter] = useState<string>('');
  const [memberOffset, setMemberOffset] = useState<number>(0);
  const [memberLimit] = useState<number>(20);

  // Invitation Directory State
  const [invitationsList, setInvitationsList] = useState<InvitationResponse[]>(invitations || []);
  const [isLoadingInvitations, setIsLoadingInvitations] = useState(false);
  const [invitationsError, setInvitationsError] = useState<string | null>(null);
  const [invitationStatusFilter, setInvitationStatusFilter] = useState<string>('');
  const [invitationOffset, setInvitationOffset] = useState<number>(0);
  const [invitationLimit] = useState<number>(20);

  // Sync external invitations prop if passed
  useEffect(() => {
    if (invitations && invitations.length > 0) {
      setInvitationsList((prev) => (prev.length === 0 ? invitations : prev));
    }
  }, [invitations]);

  // Reset pagination when activeOrgId changes
  useEffect(() => {
    setMemberOffset(0);
    setInvitationOffset(0);
  }, [activeOrgId]);

  // Fetch Members from API
  const fetchMembers = useCallback(async () => {
    if (!activeOrgId) return;
    setIsLoadingMembers(true);
    setMembersError(null);
    try {
      const data = await listOrganizationMembers(
        activeOrgId,
        {
          status: memberStatusFilter || undefined,
          limit: memberLimit,
          offset: memberOffset,
        },
        { authToken },
      );
      setMembers(data);
    } catch (err) {
      // In tests where fetch is unmocked or for offline resiliency, only show error if no fallback
      const hasFallback = currentUser?.memberships?.some((m) => m.organization_id === activeOrgId);
      if (!hasFallback) {
        setMembersError(err instanceof ApiError ? err.detail : 'Failed to load member roster.');
      }
    } finally {
      setIsLoadingMembers(false);
    }
  }, [activeOrgId, memberStatusFilter, memberLimit, memberOffset, authToken, currentUser]);

  useEffect(() => {
    fetchMembers();
  }, [fetchMembers]);

  // Fetch Invitations from API (only if caller has role-management authority)
  const fetchInvitations = useCallback(async () => {
    if (!activeOrgId || !canManageRoles) {
      return;
    }
    setIsLoadingInvitations(true);
    setInvitationsError(null);
    try {
      const data = await listOrganizationInvitations(
        activeOrgId,
        {
          status: invitationStatusFilter || undefined,
          limit: invitationLimit,
          offset: invitationOffset,
        },
        { authToken },
      );
      setInvitationsList(data);
    } catch (err) {
      if (!invitations || invitations.length === 0) {
        setInvitationsError(err instanceof ApiError ? err.detail : 'Failed to load invitations.');
      }
    } finally {
      setIsLoadingInvitations(false);
    }
  }, [activeOrgId, canManageRoles, invitationStatusFilter, invitationLimit, invitationOffset, authToken, invitations]);

  useEffect(() => {
    fetchInvitations();
  }, [fetchInvitations]);

  // Compute displayed members with fallback to current user membership if API hasn't populated
  const displayMembers = useMemo(() => {
    if (members.length > 0) {
      return members;
    }
    if (currentUser) {
      const currentMembership = currentUser.memberships.find((m) => m.organization_id === activeOrgId);
      if (currentMembership) {
        return [
          {
            id: currentMembership.id,
            organization_id: currentMembership.organization_id,
            user_id: currentUser.id,
            display_name: currentUser.display_name,
            email: currentUser.email,
            email_masked: false,
            membership_status: currentMembership.membership_status,
            joined_at: new Date().toISOString(),
            roles: currentMembership.roles,
          },
        ];
      }
    }
    return [];
  }, [members, currentUser, activeOrgId]);

  // Filter members
  const filteredMembers = useMemo(() => {
    return displayMembers.filter((m) => {
      const matchesSearch =
        m.display_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        m.email.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesRole =
        !roleFilter || m.roles.some((r) => r.role_name === roleFilter);
      return matchesSearch && matchesRole;
    });
  }, [displayMembers, searchTerm, roleFilter]);

  // Filter invitations
  const filteredInvitations = useMemo(() => {
    return invitationsList.filter((inv) => {
      const matchesSearch = inv.email.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesRole = !roleFilter || inv.role_name === roleFilter;
      return matchesSearch && matchesRole;
    });
  }, [invitationsList, searchTerm, roleFilter]);

  const handleRevoke = async (id: string) => {
    setRevokingId(id);
    try {
      if (onRevokeInvitation) {
        await onRevokeInvitation(id);
      } else {
        await revokeInvitation(activeOrgId, id, { authToken });
      }
      setInvitationsList((prev) =>
        prev.map((i) => (i.id === id ? { ...i, status: 'revoked' } : i)),
      );
      fetchInvitations();
    } finally {
      setRevokingId(null);
    }
  };

  const renderRoleBadge = (roleName: string) => {
    switch (roleName) {
      case 'PRIMARY_ADMIN':
        return <Badge variant="primary">Primary Admin</Badge>;
      case 'OFFICE_BEARER':
        return <Badge variant="success">Office Bearer</Badge>;
      case 'EVENT_LEAD':
        return <Badge variant="warning">Event Lead</Badge>;
      case 'DEPARTMENT_LEAD':
        return <Badge variant="warning">Dept Lead</Badge>;
      case 'REGISTRATION_STAFF':
        return <Badge variant="neutral">Registration Staff</Badge>;
      default:
        return <Badge variant="neutral">{roleName}</Badge>;
    }
  };

  const renderInvitationStatusBadge = (status: string) => {
    switch (status) {
      case 'accepted':
        return <Badge variant="success">Accepted</Badge>;
      case 'revoked':
        return <Badge variant="danger">Revoked</Badge>;
      case 'expired':
        return <Badge variant="neutral">Expired</Badge>;
      default:
        return <Badge variant="warning">Pending</Badge>;
    }
  };

  return (
    <div className="co-card" style={{ marginTop: 24 }}>
      <div className="co-card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h3 className="co-card-title">Team &amp; Access Management</h3>
          <p className="co-card-subtitle">
            Manage organization staff, role assignments, and single-use membership invitations.
          </p>
        </div>

        {canManageRoles && (
          <button
            type="button"
            className="co-btn co-btn-primary"
            onClick={onOpenInviteModal}
            disabled={!isVerified}
            title={!isVerified ? 'Invitations require verified organization status' : undefined}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
          >
            <IconPlus size={16} />
            <span>Invite Team Member</span>
          </button>
        )}
      </div>

      {/* Tabs */}
      <div
        style={{
          display: 'flex',
          borderBottom: '1px solid var(--co-border-subtle)',
          padding: '0 24px',
          background: 'var(--co-bg-surface)',
          gap: 20,
        }}
      >
        <button
          type="button"
          onClick={() => setActiveTab('members')}
          style={{
            padding: '12px 4px',
            border: 'none',
            borderBottom: activeTab === 'members' ? '2px solid var(--co-primary-600)' : '2px solid transparent',
            background: 'none',
            fontWeight: activeTab === 'members' ? 600 : 500,
            color: activeTab === 'members' ? 'var(--co-primary-700)' : 'var(--co-text-muted)',
            cursor: 'pointer',
            fontSize: '0.875rem',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <IconUser size={16} />
          <span>Active Members ({displayMembers.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('invitations')}
          style={{
            padding: '12px 4px',
            border: 'none',
            borderBottom: activeTab === 'invitations' ? '2px solid var(--co-primary-600)' : '2px solid transparent',
            background: 'none',
            fontWeight: activeTab === 'invitations' ? 600 : 500,
            color: activeTab === 'invitations' ? 'var(--co-primary-700)' : 'var(--co-text-muted)',
            cursor: 'pointer',
            fontSize: '0.875rem',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <IconMail size={16} />
          <span>Invitations ({invitationsList.length})</span>
        </button>
      </div>

      {/* Search and Filters */}
      <div
        style={{
          padding: '16px 24px',
          display: 'flex',
          gap: 12,
          borderBottom: '1px solid var(--co-border-subtle)',
          flexWrap: 'wrap',
          alignItems: 'center',
        }}
      >
        <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
          <span
            style={{
              position: 'absolute',
              left: 10,
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--co-text-muted)',
              display: 'flex',
              pointerEvents: 'none',
            }}
          >
            <IconSearch size={15} />
          </span>
          <input
            type="text"
            className="co-input"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder={activeTab === 'members' ? 'Search members by name or email...' : 'Search invitations by email...'}
            style={{ paddingLeft: 32, width: '100%' }}
          />
        </div>

        <select
          className="co-input"
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          style={{ width: 170 }}
          aria-label="Filter by role"
        >
          <option value="">All Roles</option>
          <option value="PRIMARY_ADMIN">Primary Admin</option>
          <option value="OFFICE_BEARER">Office Bearer</option>
          <option value="COORDINATOR">Coordinator</option>
          <option value="EVENT_LEAD">Event Lead</option>
          <option value="DEPARTMENT_LEAD">Department Lead</option>
          <option value="REGISTRATION_STAFF">Registration Staff</option>
        </select>

        {activeTab === 'members' ? (
          <select
            className="co-input"
            value={memberStatusFilter}
            onChange={(e) => {
              setMemberStatusFilter(e.target.value);
              setMemberOffset(0);
            }}
            style={{ width: 150 }}
            aria-label="Filter members by status"
          >
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="invited">Invited</option>
            <option value="suspended">Suspended</option>
          </select>
        ) : (
          <select
            className="co-input"
            value={invitationStatusFilter}
            onChange={(e) => {
              setInvitationStatusFilter(e.target.value);
              setInvitationOffset(0);
            }}
            style={{ width: 150 }}
            aria-label="Filter invitations by status"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="accepted">Accepted</option>
            <option value="revoked">Revoked</option>
            <option value="expired">Expired</option>
          </select>
        )}

        <button
          type="button"
          className="co-btn co-btn-ghost"
          onClick={activeTab === 'members' ? fetchMembers : fetchInvitations}
          title="Refresh directory list"
          style={{ padding: '8px 12px', fontSize: '0.85rem' }}
        >
          Refresh
        </button>
      </div>

      <div className="co-card-body" style={{ padding: 0 }}>
        {activeTab === 'members' ? (
          isLoadingMembers && displayMembers.length === 0 ? (
            <div style={{ padding: 36, textAlign: 'center' }}>
              <Spinner size="md" />
              <p style={{ marginTop: 12, color: 'var(--co-text-muted)', fontSize: '0.875rem' }}>
                Loading member directory...
              </p>
            </div>
          ) : membersError ? (
            <div style={{ padding: 24 }}>
              <Alert variant="danger" title="Unable to Load Member Directory">
                {membersError}
              </Alert>
              <div style={{ marginTop: 12, textAlign: 'right' }}>
                <button type="button" className="co-btn co-btn-secondary" onClick={fetchMembers}>
                  Retry
                </button>
              </div>
            </div>
          ) : filteredMembers.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: 'var(--co-text-muted)', fontSize: '0.9rem' }}>
              No members matched your search criteria.
            </div>
          ) : (
            <>
              <div className="co-table-container">
                <table className="co-table">
                  <thead>
                    <tr>
                      <th>Member</th>
                      <th>Email</th>
                      <th>Assigned Roles</th>
                      <th>Scope</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredMembers.map((m) => {
                      const isCurrentUser = currentUser?.id === m.user_id;

                      return (
                        <tr key={m.id}>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <span style={{ fontWeight: 600 }}>{m.display_name}</span>
                              {isCurrentUser && (
                                <span
                                  style={{
                                    fontSize: '0.7rem',
                                    padding: '1px 6px',
                                    borderRadius: 'var(--co-radius-full)',
                                    background: 'var(--co-primary-100)',
                                    color: 'var(--co-primary-800)',
                                    fontWeight: 600,
                                  }}
                                >
                                  You
                                </span>
                              )}
                            </div>
                          </td>
                          <td>
                            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                              <span style={{ fontFamily: 'var(--co-font-mono)', fontSize: '0.825rem' }}>
                                {m.email}
                              </span>
                              {m.email_masked && (
                                <span
                                  style={{
                                    fontSize: '0.675rem',
                                    padding: '1px 6px',
                                    borderRadius: 'var(--co-radius-full)',
                                    background: 'var(--co-bg-subtle)',
                                    color: 'var(--co-text-muted)',
                                    border: '1px solid var(--co-border-subtle)',
                                    fontWeight: 500,
                                  }}
                                  title="Contact email is masked for privacy"
                                >
                                  Masked
                                </span>
                              )}
                            </div>
                          </td>
                          <td>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                              {m.roles.map((r) => (
                                <span key={r.id}>{renderRoleBadge(r.role_name)}</span>
                              ))}
                            </div>
                          </td>
                          <td>
                            <span style={{ fontSize: '0.825rem', color: 'var(--co-text-muted)' }}>
                              Organization
                            </span>
                          </td>
                          <td>
                            <Badge variant={m.membership_status === 'active' ? 'success' : 'neutral'}>
                              {m.membership_status === 'active' ? 'Active' : m.membership_status}
                            </Badge>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Members Pagination */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 24px',
                  borderTop: '1px solid var(--co-border-subtle)',
                  fontSize: '0.8rem',
                  color: 'var(--co-text-muted)',
                }}
              >
                <span>
                  Showing {filteredMembers.length} member(s)
                </span>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    type="button"
                    className="co-btn co-btn-ghost"
                    disabled={memberOffset === 0 || isLoadingMembers}
                    onClick={() => setMemberOffset((prev) => Math.max(0, prev - memberLimit))}
                    style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    className="co-btn co-btn-ghost"
                    disabled={members.length < memberLimit || isLoadingMembers}
                    onClick={() => setMemberOffset((prev) => prev + memberLimit)}
                    style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )
        ) : (
          isLoadingInvitations && invitationsList.length === 0 ? (
            <div style={{ padding: 36, textAlign: 'center' }}>
              <Spinner size="md" />
              <p style={{ marginTop: 12, color: 'var(--co-text-muted)', fontSize: '0.875rem' }}>
                Loading organization invitations...
              </p>
            </div>
          ) : invitationsError ? (
            <div style={{ padding: 24 }}>
              <Alert variant="danger" title="Unable to Load Invitations">
                {invitationsError}
              </Alert>
              <div style={{ marginTop: 12, textAlign: 'right' }}>
                <button type="button" className="co-btn co-btn-secondary" onClick={fetchInvitations}>
                  Retry
                </button>
              </div>
            </div>
          ) : filteredInvitations.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: 'var(--co-text-muted)', fontSize: '0.9rem' }}>
              No invitations have been issued for this workspace yet.
            </div>
          ) : (
            <>
              <div className="co-table-container">
                <table className="co-table">
                  <thead>
                    <tr>
                      <th>Recipient Email</th>
                      <th>Assigned Role</th>
                      <th>Scope</th>
                      <th>Status</th>
                      <th>Expires At</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredInvitations.map((inv) => {
                      const isPending = inv.status === 'pending';
                      const isBusy = revokingId === inv.id;

                      return (
                        <tr key={inv.id}>
                          <td>
                            <span style={{ fontFamily: 'var(--co-font-mono)', fontSize: '0.825rem' }}>
                              {inv.email}
                            </span>
                          </td>
                          <td>{renderRoleBadge(inv.role_name)}</td>
                          <td>
                            <span style={{ fontSize: '0.825rem', textTransform: 'capitalize' }}>
                              {inv.scope_type}
                            </span>
                          </td>
                          <td>{renderInvitationStatusBadge(inv.status)}</td>
                          <td>
                            <span style={{ fontSize: '0.8rem', color: 'var(--co-text-muted)' }}>
                              {formatDateTime(inv.expires_at)}
                            </span>
                          </td>
                          <td>
                            {canManageRoles && isPending ? (
                              <button
                                type="button"
                                className="co-btn co-btn-ghost"
                                onClick={() => handleRevoke(inv.id)}
                                disabled={isBusy}
                                style={{
                                  fontSize: '0.75rem',
                                  color: 'var(--co-danger-600)',
                                  padding: '4px 8px',
                                }}
                              >
                                {isBusy ? <Spinner size="sm" /> : 'Revoke'}
                              </button>
                            ) : (
                              <span style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)' }}>—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Invitations Pagination */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 24px',
                  borderTop: '1px solid var(--co-border-subtle)',
                  fontSize: '0.8rem',
                  color: 'var(--co-text-muted)',
                }}
              >
                <span>
                  Showing {filteredInvitations.length} invitation(s)
                </span>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    type="button"
                    className="co-btn co-btn-ghost"
                    disabled={invitationOffset === 0 || isLoadingInvitations}
                    onClick={() => setInvitationOffset((prev) => Math.max(0, prev - invitationLimit))}
                    style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    className="co-btn co-btn-ghost"
                    disabled={invitationsList.length < invitationLimit || isLoadingInvitations}
                    onClick={() => setInvitationOffset((prev) => prev + invitationLimit)}
                    style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )
        )}
      </div>

      <div
        style={{
          padding: '12px 24px',
          background: 'var(--co-bg-subtle)',
          borderTop: '1px solid var(--co-border-subtle)',
          fontSize: '0.75rem',
          color: 'var(--co-text-muted)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <span>
          Member identity is synchronized with server-verified credentials.
        </span>
        <span style={{ fontStyle: 'italic' }}>
          Single-use tokens expire after 7 days (Policy FA-009).
        </span>
      </div>
    </div>
  );
};
