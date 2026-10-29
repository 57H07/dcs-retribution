// Keyboard shortcuts of the web shell (W13). Deliberately none for passing the
// turn or taking off: those stay explicit clicks.
import { LAYER_SHORTCUTS } from "../maplayers/layerToggle";
import { OVERLAYS, OverlayId } from "../maplayers/overlays";
import { useEffect, useRef } from "react";

export type ShortcutAction =
  | { kind: "close" }
  | { kind: "layer"; overlay: OverlayId }
  | { kind: "newPackage" }
  | { kind: "save" }
  | { kind: "help" };

/** Rows of the help overlay, in display order. */
export const SHORTCUT_HELP: { keys: string; description: string }[] = [
  { keys: "Esc", description: "Close the open dialog or panel" },
  ...LAYER_SHORTCUTS.map(({ key, overlay }) => ({
    keys: key,
    description: `Toggle map layer: ${OVERLAYS[overlay].name}`,
  })),
  { keys: "N", description: "New package" },
  { keys: "Ctrl+S", description: "Save the campaign" },
  { keys: "?", description: "Show this help" },
];

/** True when the key goes to a text field, which keeps it (no shortcut). */
export function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  if (target.isContentEditable) {
    return true;
  }
  if (target instanceof HTMLInputElement) {
    // Buttons, checkboxes... do not take text: shortcuts still apply.
    return !["button", "checkbox", "radio", "range", "reset", "submit"].includes(
      target.type,
    );
  }
  return (
    target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement
  );
}

type KeyInfo = Pick<
  KeyboardEvent,
  "key" | "ctrlKey" | "metaKey" | "altKey" | "target"
>;

/** The shortcut a key press triggers, or null. */
export function shortcutFor(event: KeyInfo): ShortcutAction | null {
  if (isTypingTarget(event.target)) {
    return null;
  }
  const command = event.ctrlKey || event.metaKey;
  if (command && !event.altKey && event.key.toLowerCase() === "s") {
    return { kind: "save" };
  }
  if (command || event.altKey) {
    return null;
  }
  if (event.key === "Escape") {
    return { kind: "close" };
  }
  if (event.key === "?") {
    return { kind: "help" };
  }
  if (event.key === "n" || event.key === "N") {
    return { kind: "newPackage" };
  }
  const layer = LAYER_SHORTCUTS.find(({ key }) => key === event.key);
  if (layer) {
    return { kind: "layer", overlay: layer.overlay };
  }
  return null;
}

/** Listens to the window keyboard and runs `onShortcut` for each shortcut. */
export function useShortcuts(onShortcut: (action: ShortcutAction) => void) {
  const handler = useRef(onShortcut);
  useEffect(() => {
    handler.current = onShortcut;
  });
  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      if (event.defaultPrevented) {
        return;
      }
      const action = shortcutFor(event);
      if (action === null) {
        return;
      }
      // Escape is left to whoever else handles it (Radix dialogs, menus).
      if (action.kind !== "close") {
        event.preventDefault();
      }
      handler.current(action);
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, []);
}
