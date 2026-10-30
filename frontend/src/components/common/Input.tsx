import type { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes, FC, ReactNode, Ref } from 'react';
import { IconAlertCircle } from './Icons';

interface BaseFieldProps {
  id: string;
  label: string;
  required?: boolean;
  error?: string;
  helpText?: string;
  className?: string;
}

export interface TextInputProps extends BaseFieldProps, Omit<InputHTMLAttributes<HTMLInputElement>, 'id'> {
  leftAddon?: ReactNode;
  rightAddon?: ReactNode;
  ref?: Ref<HTMLInputElement>;
}

export const TextInput: FC<TextInputProps> = ({
  id,
  label,
  required,
  error,
  helpText,
  leftAddon,
  rightAddon,
  className = '',
  ref,
  ...rest
}) => {
  return (
    <div className={`co-form-group ${className}`}>
      <div className="co-label-row">
        <label htmlFor={id} className={`co-label ${required ? 'co-label-required' : ''}`}>
          {label}
        </label>
      </div>
      <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
        {leftAddon && (
          <div style={{ position: 'absolute', left: 12, display: 'flex', alignItems: 'center', color: 'var(--co-text-muted)', pointerEvents: 'none' }}>
            {leftAddon}
          </div>
        )}
        <input
          id={id}
          ref={ref}
          className={`co-input ${error ? 'co-input-error' : ''}`}
          style={{
            paddingLeft: leftAddon ? '2.5rem' : undefined,
            paddingRight: rightAddon ? '2.5rem' : undefined,
          }}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : helpText ? `${id}-help` : undefined}
          required={required}
          {...rest}
        />
        {rightAddon && (
          <div style={{ position: 'absolute', right: 12, display: 'flex', alignItems: 'center', color: 'var(--co-text-muted)' }}>
            {rightAddon}
          </div>
        )}
      </div>
      {error && (
        <div id={`${id}-error`} className="co-field-error" role="alert">
          <IconAlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}
      {!error && helpText && (
        <p id={`${id}-help`} className="co-field-help">
          {helpText}
        </p>
      )}
    </div>
  );
};

export interface TextareaProps extends BaseFieldProps, Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'id'> {
  showCount?: boolean;
  minCount?: number;
  ref?: Ref<HTMLTextAreaElement>;
}

export const Textarea: FC<TextareaProps> = ({
  id,
  label,
  required,
  error,
  helpText,
  showCount = false,
  minCount,
  className = '',
  rows = 3,
  value,
  ref,
  ...rest
}) => {
  const currentLen = typeof value === 'string' ? value.trim().length : 0;
  const isMinSatisfied = minCount !== undefined ? currentLen >= minCount : true;

  return (
    <div className={`co-form-group ${className}`}>
      <div className="co-label-row">
        <label htmlFor={id} className={`co-label ${required ? 'co-label-required' : ''}`}>
          {label}
        </label>
        {showCount && minCount !== undefined && (
          <span className={`co-char-count ${isMinSatisfied ? 'valid' : ''}`}>
            {currentLen}/{minCount} min chars
          </span>
        )}
      </div>
      <textarea
        id={id}
        ref={ref}
        rows={rows}
        className={`co-textarea ${error ? 'co-input-error' : ''}`}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : helpText ? `${id}-help` : undefined}
        required={required}
        value={value}
        {...rest}
      />
      {error && (
        <div id={`${id}-error`} className="co-field-error" role="alert">
          <IconAlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}
      {!error && helpText && (
        <p id={`${id}-help`} className="co-field-help">
          {helpText}
        </p>
      )}
    </div>
  );
};

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectInputProps extends BaseFieldProps, Omit<SelectHTMLAttributes<HTMLSelectElement>, 'id'> {
  options: SelectOption[];
  children?: ReactNode;
  ref?: Ref<HTMLSelectElement>;
}

export const SelectInput: FC<SelectInputProps> = ({
  id,
  label,
  required,
  error,
  helpText,
  options,
  className = '',
  ref,
  ...rest
}) => {
  return (
    <div className={`co-form-group ${className}`}>
      <div className="co-label-row">
        <label htmlFor={id} className={`co-label ${required ? 'co-label-required' : ''}`}>
          {label}
        </label>
      </div>
      <select
        id={id}
        ref={ref}
        className={`co-select ${error ? 'co-input-error' : ''}`}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : helpText ? `${id}-help` : undefined}
        required={required}
        {...rest}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && (
        <div id={`${id}-error`} className="co-field-error" role="alert">
          <IconAlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}
      {!error && helpText && (
        <p id={`${id}-help`} className="co-field-help">
          {helpText}
        </p>
      )}
    </div>
  );
};
