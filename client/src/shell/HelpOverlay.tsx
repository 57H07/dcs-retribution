import { Modal } from "../ui";
import styles from "./HelpOverlay.module.css";
import { SHORTCUT_HELP } from "./shortcuts";

export interface HelpOverlayProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** The `?` page: every keyboard shortcut of the web UI (W13). */
export function HelpOverlay({ open, onOpenChange }: HelpOverlayProps) {
  return (
    <Modal title="Keyboard shortcuts" open={open} onOpenChange={onOpenChange}>
      <dl className={styles.list}>
        {SHORTCUT_HELP.map(({ keys, description }) => (
          <div key={keys} className={styles.row}>
            <dt>
              <kbd className={styles.key}>{keys}</kbd>
            </dt>
            <dd className={styles.description}>{description}</dd>
          </div>
        ))}
      </dl>
    </Modal>
  );
}
