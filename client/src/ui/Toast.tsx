import { IconButton } from "./Button";
import styles from "./Toast.module.css";
import * as RadixToast from "@radix-ui/react-toast";
import {
  ReactNode,
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
} from "react";

export type ToastTone = "info" | "success" | "danger" | "accent";

export interface ToastOptions {
  title: string;
  description?: string;
  tone?: ToastTone;
  /** Milliseconds before it hides; defaults to the provider's duration. */
  duration?: number;
}

interface ToastItem extends ToastOptions {
  id: number;
}

type ShowToast = (options: ToastOptions) => void;

const ToastContext = createContext<ShowToast | null>(null);

/** Returns toast(options). Needs a ToastProvider above. */
export function useToast(): ShowToast {
  const show = useContext(ToastContext);
  if (!show) {
    throw new Error("useToast must be used inside a ToastProvider");
  }
  return show;
}

export interface ToastProviderProps {
  children: ReactNode;
  duration?: number;
}

/** Hosts the notifications (bottom right, F8 focuses them). */
export function ToastProvider({
  children,
  duration = 5000,
}: ToastProviderProps) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(0);

  const show = useCallback<ShowToast>((options) => {
    const id = nextId.current++;
    setItems((current) => [...current, { ...options, id }]);
  }, []);

  // A closed toast (timeout, swipe, ✕) leaves the list.
  const remove = (id: number) =>
    setItems((current) => current.filter((item) => item.id !== id));

  return (
    <ToastContext.Provider value={show}>
      <RadixToast.Provider duration={duration} swipeDirection="right">
        {children}
        {items.map((item) => (
          <RadixToast.Root
            key={item.id}
            className={styles.toast}
            data-tone={item.tone ?? "info"}
            duration={item.duration}
            type={item.tone === "danger" ? "foreground" : "background"}
            onOpenChange={(open) => !open && remove(item.id)}
          >
            <div className={styles.text}>
              <RadixToast.Title className={styles.title}>
                {item.title}
              </RadixToast.Title>
              {item.description && (
                <RadixToast.Description className={styles.description}>
                  {item.description}
                </RadixToast.Description>
              )}
            </div>
            <RadixToast.Close asChild>
              <IconButton aria-label="Dismiss" className={styles.close}>
                ✕
              </IconButton>
            </RadixToast.Close>
          </RadixToast.Root>
        ))}
        <RadixToast.Viewport className={styles.viewport} />
      </RadixToast.Provider>
    </ToastContext.Provider>
  );
}
