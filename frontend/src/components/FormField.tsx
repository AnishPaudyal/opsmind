import type { InputHTMLAttributes } from "react";
import type { UseFormRegisterReturn } from "react-hook-form";

export function FormField({
  error,
  help,
  id,
  label,
  registration,
  ...inputProps
}: InputHTMLAttributes<HTMLInputElement> & {
  readonly error?: string;
  readonly help?: string;
  readonly id: string;
  readonly label: string;
  readonly registration?: UseFormRegisterReturn;
}) {
  const descriptionId = `${id}-description`;
  return (
    <div className="form-field">
      <label htmlFor={id}>{label}</label>
      <input
        aria-describedby={help || error ? descriptionId : undefined}
        aria-invalid={error ? true : undefined}
        id={id}
        {...registration}
        {...inputProps}
      />
      {help || error ? (
        <p
          className={error ? "form-field__error" : "form-field__help"}
          id={descriptionId}
        >
          {error ?? help}
        </p>
      ) : null}
    </div>
  );
}
