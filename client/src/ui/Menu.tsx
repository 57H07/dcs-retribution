import { Button } from "./Button";
import styles from "./Menu.module.css";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";

export interface MenuAction {
  label: string;
  onSelect: () => void;
  /** Shortcut hint shown on the right, e.g. "Ctrl+S" (display only). */
  shortcut?: string;
  disabled?: boolean;
}

/** A menu entry, or "separator" for a divider line. */
export type MenuEntry = MenuAction | "separator";

export interface MenuProps {
  /** Text of the button that opens the menu. */
  label: string;
  items: MenuEntry[];
}

/** Drop-down menu (Radix): arrow keys move, Enter selects, Escape closes. */
export function Menu({ label, items }: MenuProps) {
  return (
    <DropdownMenu.Root modal={false}>
      <DropdownMenu.Trigger asChild>
        <Button variant="ghost">{label}</Button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className={styles.content}
          align="start"
          sideOffset={4}
          aria-label={label}
        >
          {items.map((item, index) =>
            item === "separator" ? (
              <DropdownMenu.Separator
                key={`separator-${index}`}
                className={styles.separator}
              />
            ) : (
              <DropdownMenu.Item
                key={item.label}
                className={styles.item}
                disabled={item.disabled}
                onSelect={item.onSelect}
              >
                <span>{item.label}</span>
                {item.shortcut && (
                  <kbd className={styles.shortcut}>{item.shortcut}</kbd>
                )}
              </DropdownMenu.Item>
            ),
          )}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
