import { IconButton } from "./Button";
import styles from "./Modal.module.css";
import { cx } from "./cx";
import * as Dialog from "@radix-ui/react-dialog";
import { ReactNode } from "react";

export interface ModalProps {
  title: string;
  description?: string;
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  /** Element that opens the modal (rendered as is, e.g. a Button). */
  trigger?: ReactNode;
  children?: ReactNode;
  /** Actions, right-aligned; wrap the cancel action in ModalClose. */
  footer?: ReactNode;
  size?: "md" | "lg";
}

/** Closes the enclosing modal when its child is activated. */
export const ModalClose = Dialog.Close;

/** Modal dialog: focus trapped, Escape and the ✕ button close it. */
export function Modal({
  title,
  description,
  open,
  defaultOpen,
  onOpenChange,
  trigger,
  children,
  footer,
  size = "md",
}: ModalProps) {
  return (
    <Dialog.Root
      open={open}
      defaultOpen={defaultOpen}
      onOpenChange={onOpenChange}
    >
      {trigger && <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>}
      <Dialog.Portal>
        <Dialog.Overlay className={styles.overlay} />
        <Dialog.Content
          className={cx(styles.content, size === "lg" && styles.lg)}
          // Without a description, tell Radix there is none on purpose.
          {...(description ? {} : { "aria-describedby": undefined })}
        >
          <div className={styles.header}>
            <div className={styles.headings}>
              <Dialog.Title className={styles.title}>{title}</Dialog.Title>
              {description && (
                <Dialog.Description className={styles.description}>
                  {description}
                </Dialog.Description>
              )}
            </div>
            <Dialog.Close asChild>
              <IconButton aria-label="Close">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <path d="M6 6l12 12M18 6L6 18" />
                </svg>
              </IconButton>
            </Dialog.Close>
          </div>
          {children && <div className={styles.body}>{children}</div>}
          {footer && <div className={styles.footer}>{footer}</div>}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
