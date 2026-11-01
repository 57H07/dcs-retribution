// Replacing the group of a ground object (WEB-08.3), the web version of the Qt
// QGroundObjectBuyMenu. The -/+ and selects only prepare the purchase: the server
// quotes every change and has the last word when buying.
import { commandErrorMessage } from "../api/commands";
import {
  LayoutSlot,
  PurchaseLayout,
  TgoPurchase,
  useBuyTgoGroupMutation,
  useGetTgoPurchaseOptionsQuery,
  useQuoteTgoPurchaseMutation,
} from "../api/liberationApi";
import { money } from "../bases/money";
import secondary from "../secondary/Secondary.module.css";
import settings from "../settings/SettingsScreen.module.css";
import {
  Button,
  Modal,
  ModalClose,
  NumberField,
  Switch,
  useToast,
} from "../ui";
import styles from "./TgoScreen.module.css";
import { useEffect, useMemo, useState } from "react";

export interface BuyDialogProps {
  tgoId: string;
  siteName: string;
  onClose: () => void;
}

export function BuyDialog({ tgoId, siteName, onClose }: BuyDialogProps) {
  const { data, error, isLoading } = useGetTgoPurchaseOptionsQuery({ tgoId });
  const [forceGroupName, setForceGroupName] = useState<string | null>(null);
  const [layoutName, setLayoutName] = useState<string | null>(null);
  const groups = data?.force_groups ?? [];
  const forceGroup =
    groups.find((group) => group.name === forceGroupName) ?? groups[0];
  const layout =
    forceGroup?.layouts.find((l) => l.name === layoutName) ??
    forceGroup?.layouts[0];

  return (
    <Modal
      title={`Buy units at ${siteName}`}
      size="lg"
      open
      onOpenChange={(open) => !open && onClose()}
    >
      {isLoading ? (
        <p className={secondary.state}>Loading what you can buy…</p>
      ) : error ? (
        <p className={secondary.state} role="alert">
          {commandErrorMessage(error) ?? "The purchases are not available."}
        </p>
      ) : !forceGroup || !layout ? (
        <p className={secondary.state}>
          Your faction has nothing for this site.
        </p>
      ) : (
        <div className={styles.buy}>
          <label className={styles.field}>
            Armed forces group
            <select
              className={settings.select}
              value={forceGroup.name}
              disabled={groups.length < 2}
              onChange={(event) => {
                setForceGroupName(event.target.value);
                setLayoutName(null);
              }}
            >
              {groups.map((group) => (
                <option key={group.name} value={group.name}>
                  {group.name}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.field}>
            Layout
            <select
              className={settings.select}
              value={layout.name}
              disabled={forceGroup.layouts.length < 2}
              onChange={(event) => setLayoutName(event.target.value)}
            >
              {forceGroup.layouts.map((l) => (
                <option key={l.name} value={l.name}>
                  {l.name}
                </option>
              ))}
            </select>
          </label>
          <LayoutForm
            key={`${forceGroup.name}/${layout.name}`}
            tgoId={tgoId}
            forceGroup={forceGroup.name}
            layout={layout}
            onBought={onClose}
          />
        </div>
      )}
    </Modal>
  );
}

interface SlotState {
  enabled: boolean;
  unitType: string;
  amount: number;
}

function initialSlots(layout: PurchaseLayout): Record<number, SlotState> {
  return Object.fromEntries(
    layout.slots.map((slot) => [
      slot.id,
      { enabled: true, unitType: slot.options[0].id, amount: slot.amount },
    ]),
  );
}

function LayoutForm(props: {
  tgoId: string;
  forceGroup: string;
  layout: PurchaseLayout;
  onBought: () => void;
}) {
  const { tgoId, forceGroup, layout, onBought } = props;
  const toast = useToast();
  const [slots, setSlots] = useState(() => initialSlots(layout));
  const [buy, buyState] = useBuyTgoGroupMutation();
  const [quote, quoteState] = useQuoteTgoPurchaseMutation();

  const purchase: TgoPurchase = useMemo(
    () => ({
      force_group: forceGroup,
      layout: layout.name,
      choices: layout.slots
        .filter((slot) => slots[slot.id].enabled)
        .map((slot) => ({
          slot: slot.id,
          unit_type: slots[slot.id].unitType,
          amount: slots[slot.id].amount,
        })),
    }),
    [forceGroup, layout, slots],
  );

  useEffect(() => {
    quote({ tgoId, tgoPurchaseJs: purchase });
  }, [quote, tgoId, purchase]);

  const change = (id: number, changes: Partial<SlotState>) =>
    setSlots((current) => ({
      ...current,
      [id]: { ...current[id], ...changes },
    }));

  const onBuy = async () => {
    const result = await buy({ tgoId, tgoPurchaseJs: purchase });
    if ("error" in result) {
      toast({
        title: "Purchase refused",
        description: commandErrorMessage(result.error),
        tone: "danger",
      });
    } else {
      toast({ title: "Units bought", tone: "success" });
      onBought();
    }
  };

  const offer = quoteState.isLoading ? undefined : quoteState.data;
  const groupNames = [...new Set(layout.slots.map((s) => s.group_name))];

  return (
    <>
      {groupNames.map((groupName) => (
        <fieldset key={groupName} className={styles.group}>
          <legend className={styles.groupName}>{groupName}</legend>
          {layout.slots
            .filter((slot) => slot.group_name === groupName)
            .map((slot) => (
              <SlotRow
                key={slot.id}
                slot={slot}
                state={slots[slot.id]}
                onChange={(changes) => change(slot.id, changes)}
              />
            ))}
        </fieldset>
      ))}
      {quoteState.isError && (
        <p className={styles.damaged} role="alert">
          {commandErrorMessage(quoteState.error)}
        </p>
      )}
      {offer && (
        <p className={secondary.prose} aria-label="Quote">
          New group {money(offer.price)}, current group worth{" "}
          {money(offer.credit)}: you pay{" "}
          <strong className={secondary.mono}>{money(offer.cost)}</strong>
        </p>
      )}
      <div className={styles.buyActions}>
        <ModalClose asChild>
          <Button>Cancel</Button>
        </ModalClose>
        <Button
          variant="primary"
          disabled={!offer?.affordable || buyState.isLoading}
          title={
            offer && !offer.affordable
              ? "Not enough money to buy this group"
              : undefined
          }
          onClick={onBuy}
        >
          Buy
        </Button>
      </div>
    </>
  );
}

function SlotRow(props: {
  slot: LayoutSlot;
  state: SlotState;
  onChange: (changes: Partial<SlotState>) => void;
}) {
  const { slot, state, onChange } = props;
  return (
    <div className={styles.slot}>
      <select
        className={settings.select}
        aria-label={`Unit type ${slot.id + 1}`}
        value={state.unitType}
        disabled={slot.options.length < 2 || !state.enabled}
        onChange={(event) => onChange({ unitType: event.target.value })}
      >
        {slot.options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.name} [{money(option.price)}]
          </option>
        ))}
      </select>
      <NumberField
        label={`Amount ${slot.id + 1}`}
        hideLabel
        min={1}
        max={slot.max_amount}
        value={state.amount}
        disabled={slot.max_amount < 2 || !state.enabled}
        onValueChange={(amount) => onChange({ amount })}
      />
      {slot.optional && (
        <Switch
          aria-label={`Include ${slot.id + 1}`}
          checked={state.enabled}
          onCheckedChange={(enabled) => onChange({ enabled })}
        />
      )}
    </div>
  );
}
