import type { ButtonHTMLAttributes, ReactNode } from "react";

export function Button({
  children,
  className = "",
  type = "button",
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  readonly children: ReactNode;
  readonly variant?: "primary" | "secondary" | "quiet";
}) {
  return (
    <button
      className={`button button--${variant} ${className}`.trim()}
      type={type}
      {...props}
    >
      {children}
    </button>
  );
}
