import { useState, useMemo, type FC } from 'react';
import type { IssuedPass } from '../../api/types';
import { generateQrSvg } from '../../utils/qr';
import { Badge } from '../common/Badge';
import { IconCheckCircle, IconCopy, IconCheck, IconPrinter } from '../common/Icons';
import { useToast } from '../common/Toast';

interface PublicPassDisplayProps {
  pass: IssuedPass;
  eventName: string;
  isTeam?: boolean;
  teamName?: string | null;
}

export const PublicPassDisplay: FC<PublicPassDisplayProps> = ({
  pass,
  eventName,
  isTeam = false,
  teamName,
}) => {
  const [copied, setCopied] = useState(false);
  const { showToast } = useToast();

  const isRedacted = pass.pass_code === '<REDACTED_AFTER_ISSUANCE>';

  // Generate SVG QR code from opaque pass_code (strictly NO PII in QR payload)
  const qrSvg = useMemo(() => {
    if (isRedacted || !pass.pass_code) return null;
    return generateQrSvg(pass.pass_code, {
      title: `Admission Pass QR for ${pass.participant_name}`,
      ecc: 'M',
      margin: 2,
    });
  }, [pass.pass_code, pass.participant_name, isRedacted]);

  const handleCopyCode = async () => {
    if (isRedacted || !pass.pass_code) return;
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(pass.pass_code);
        setCopied(true);
        showToast('success', 'Pass Code Copied', `${pass.participant_name}'s code is on your clipboard.`);
        setTimeout(() => setCopied(false), 2000);
      }
    } catch {
      // Ignore clipboard write rejection
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="co-pass-card" data-testid={`pass-card-${pass.participant_id}`}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#94a3b8', fontWeight: 600 }}>
          CampusOps Admission Pass
        </span>
        <Badge variant="success" icon={<IconCheckCircle size={12} />}>
          Active Pass
        </Badge>
      </div>

      <h3 style={{ margin: '0 0 4px 0', fontSize: '1.3rem', color: '#ffffff', letterSpacing: '-0.01em' }}>
        {pass.participant_name}
      </h3>
      {isTeam && teamName && (
        <p style={{ margin: '0 0 8px 0', fontSize: '0.85rem', color: '#cbd5e1' }}>
          Team: <strong>{teamName}</strong>
        </p>
      )}
      <p style={{ margin: '0 0 12px 0', fontSize: '0.9rem', color: '#94a3b8' }}>
        {eventName}
      </p>

      {/* QR Code Presentation */}
      {qrSvg ? (
        <div className="co-pass-qr-box" data-testid="qr-code-box">
          <div dangerouslySetInnerHTML={{ __html: qrSvg }} />
        </div>
      ) : (
        <div
          style={{
            background: 'rgba(255, 255, 255, 0.08)',
            padding: '24px 16px',
            borderRadius: '12px',
            margin: '16px 0',
            fontSize: '0.85rem',
            color: '#e2e8f0',
          }}
        >
          <p style={{ margin: '0 0 8px 0', fontWeight: 600 }}>Pass Code Secured</p>
          <p style={{ margin: 0, fontSize: '0.8rem', color: '#94a3b8' }}>
            High-entropy admission passes are generated once upon issuance. Your ticket reference below is on record with the event desk.
          </p>
        </div>
      )}

      {/* Ticket Reference & Pass Code */}
      <div style={{ marginTop: 8 }}>
        <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Ticket Reference
        </div>
        <div style={{ fontFamily: 'var(--co-font-mono)', fontSize: '1.2rem', fontWeight: 700, color: '#38bdf8', letterSpacing: '0.04em' }}>
          {pass.ticket_reference}
        </div>
      </div>

      {!isRedacted && (
        <div className="co-pass-code-display">
          <span>Pass Code: {pass.pass_code}</span>
          <div style={{ marginTop: 8, display: 'flex', justifyContent: 'center', gap: 8 }} className="no-print">
            <button
              type="button"
              className="co-btn co-btn-ghost co-btn-sm"
              onClick={handleCopyCode}
              style={{ color: '#cbd5e1', fontSize: '0.75rem', padding: '3px 10px', background: 'rgba(255,255,255,0.06)' }}
            >
              {copied ? (
                <>
                  <IconCheck size={12} style={{ color: 'var(--co-success-500)' }} />
                  <span>✓ Copied Pass Code</span>
                </>
              ) : (
                <>
                  <IconCopy size={12} />
                  <span>Copy Code</span>
                </>
              )}
            </button>
            <button
              type="button"
              className="co-btn co-btn-ghost co-btn-sm"
              onClick={handlePrint}
              style={{ color: '#cbd5e1', fontSize: '0.75rem', padding: '3px 10px', background: 'rgba(255,255,255,0.06)' }}
              title="Print Pass / Save as PDF"
            >
              <IconPrinter size={12} />
              <span>Print Pass</span>
            </button>
          </div>
        </div>
      )}

      <p style={{ margin: '16px 0 0 0', fontSize: '0.75rem', color: '#94a3b8', lineHeight: 1.4 }}>
        Present this pass at the desk on event day. Individual check-in is verified per attendee.
      </p>
    </div>
  );
};
