import styles from "./Tabs.module.css";
import { cx } from "./cx";
import * as RadixTabs from "@radix-ui/react-tabs";
import { ComponentPropsWithoutRef, forwardRef } from "react";

export const Tabs = RadixTabs.Root;

export interface TabsListProps extends ComponentPropsWithoutRef<
  typeof RadixTabs.List
> {
  /** Triggers share the width equally (side panel tabs). */
  stretch?: boolean;
}

export const TabsList = forwardRef<HTMLDivElement, TabsListProps>(
  function TabsList({ stretch, className, ...props }, ref) {
    return (
      <RadixTabs.List
        ref={ref}
        className={cx(styles.list, stretch && styles.stretch, className)}
        {...props}
      />
    );
  },
);

export const TabsTrigger = forwardRef<
  HTMLButtonElement,
  ComponentPropsWithoutRef<typeof RadixTabs.Trigger>
>(function TabsTrigger({ className, ...props }, ref) {
  return (
    <RadixTabs.Trigger
      ref={ref}
      className={cx(styles.trigger, className)}
      {...props}
    />
  );
});

export const TabsContent = forwardRef<
  HTMLDivElement,
  ComponentPropsWithoutRef<typeof RadixTabs.Content>
>(function TabsContent({ className, ...props }, ref) {
  return (
    <RadixTabs.Content
      ref={ref}
      className={cx(styles.content, className)}
      {...props}
    />
  );
});
