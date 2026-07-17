/**
 * Screen-reader live region for co-pilot / fail-safe / intent changes.
 * Visually hidden; updates announce when message changes.
 */
type Props = {
  message: string;
  /** assertive for fail-safe / errors; polite for routine status */
  assertive?: boolean;
  id?: string;
};

export function LiveAnnouncer({ message, assertive = false, id }: Props) {
  if (!message) {
    return (
      <div
        id={id}
        className="sr-only"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      />
    );
  }
  return (
    <div
      id={id}
      className="sr-only"
      role={assertive ? "alert" : "status"}
      aria-live={assertive ? "assertive" : "polite"}
      aria-atomic="true"
    >
      {message}
    </div>
  );
}
