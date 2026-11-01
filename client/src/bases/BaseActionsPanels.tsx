// What the Qt base menu has around its tabs (WEB-02.3): the buttons of its bottom row
// (transfers, attack, cheats) and the radio settings of its header. The server says
// what this base offers (GET /control-points/{id}/actions) and enforces the limits.
import { commandErrorMessage } from "../api/commands";
import {
  BaseRadios,
  BaseRadiosUpdate,
  useCheatCaptureBaseMutation,
  useCheatRunwayStateMutation,
  useCreatePackageMutation,
  useGetBaseActionsQuery,
  useSetBaseRadiosMutation,
} from "../api/liberationApi";
import settings from "../settings/SettingsScreen.module.css";
import { Button, Modal, ModalClose, useToast } from "../ui";
import airfield from "./AirfieldTab.module.css";
import styles from "./BaseScreen.module.css";
import { Refusal, refusalOf } from "./orders";
import { TransferButton } from "./TransferDialog";
import { useState } from "react";

export function BaseActionPanels(props: { cpId: string; baseName: string }) {
  const { cpId, baseName } = props;
  const { data: actions } = useGetBaseActionsQuery({ cpId });
  const toast = useToast();
  const [createPackage, packageState] = useCreatePackageMutation();
  const [cheatRunway, runwayState] = useCheatRunwayStateMutation();
  const [cheatCapture, captureState] = useCheatCaptureBaseMutation();

  if (actions == null) {
    return null;
  }
  const cheating = runwayState.isLoading || captureState.isLoading;
  const refused = (title: string, refusal: Refusal) =>
    toast({
      title,
      description: commandErrorMessage(refusal),
      tone: "danger",
    });

  const attack = async () => {
    const refusal = refusalOf(
      await createPackage({
        newPackageJs: { target_kind: "control-point", target_id: cpId },
      }),
    );
    if (refusal !== null) {
      refused("Could not plan the attack", refusal);
    }
  };

  const cheat = async (pending: Promise<{ error?: unknown } | { data: unknown }>) => {
    const refusal = refusalOf(await pending);
    if (refusal !== null) {
      refused("Cheat refused", refusal);
    }
  };

  const hasActions =
    actions.can_transfer ||
    actions.can_plan_transport ||
    actions.can_attack_airfield ||
    actions.cheat_runway != null ||
    actions.cheat_capture != null;

  return (
    <>
      {hasActions && (
        <section className={styles.panel} aria-label="Base actions">
          <h2 className={styles.panelTitle}>Actions</h2>
          {actions.can_transfer && (
            <TransferButton cpId={cpId} baseName={baseName} kind="transfer" />
          )}
          {actions.can_plan_transport && (
            <TransferButton cpId={cpId} baseName={baseName} kind="transport" />
          )}
          {actions.can_attack_airfield && (
            <Button
              variant="danger"
              disabled={packageState.isLoading}
              onClick={attack}
            >
              Attack airfield
            </Button>
          )}
          {actions.cheat_runway != null && (
            <Button
              variant="danger"
              disabled={cheating}
              onClick={() => cheat(cheatRunway({ cpId }))}
            >
              Cheat: {actions.cheat_runway}
            </Button>
          )}
          {actions.cheat_capture != null && (
            <Button
              variant="danger"
              disabled={cheating}
              onClick={() => cheat(cheatCapture({ cpId }))}
            >
              Cheat: {actions.cheat_capture}
            </Button>
          )}
        </section>
      )}
      {actions.radios != null && <RadiosPanel cpId={cpId} radios={actions.radios} />}
    </>
  );
}

function auto(value: string | number | null | undefined): string {
  return value != null ? `${value}` : "Auto";
}

function withCallsign(channel: string, callsign?: string | null): string {
  return callsign != null ? `${channel} (${callsign})` : channel;
}

function RadiosPanel(props: { cpId: string; radios: BaseRadios }) {
  const { radios } = props;
  const [open, setOpen] = useState(false);
  const rows: [string, string][] = [];
  if (radios.has_frequency) {
    const mhz = radios.frequency_mhz;
    rows.push(["Frequency", mhz != null ? `${mhz} MHz` : "Auto"]);
  }
  if (radios.has_tacan) {
    const channel =
      radios.tacan_channel != null
        ? `${radios.tacan_channel}${radios.tacan_band ?? ""}`
        : "Auto";
    rows.push(["TACAN", withCallsign(channel, radios.tacan_callsign)]);
  }
  if (radios.has_icls) {
    rows.push([
      "ICLS",
      withCallsign(auto(radios.icls_channel), radios.icls_callsign),
    ]);
  }
  if (radios.has_link4) {
    const mhz = radios.link4_mhz;
    rows.push(["Link 4", mhz != null ? `${mhz} MHz` : "Auto"]);
  }
  return (
    <section className={styles.panel} aria-label="Radios">
      <h2 className={styles.panelTitle}>Radios</h2>
      <ul className={styles.list}>
        {rows.map(([label, value]) => (
          <li key={label} className={styles.row}>
            <span>{label}</span>
            <span className={styles.mono}>{value}</span>
          </li>
        ))}
      </ul>
      {radios.warnings.map((warning) => (
        <p key={warning} className={styles.warning}>
          {warning}
        </p>
      ))}
      <Modal
        title="Radios of the base"
        open={open}
        onOpenChange={setOpen}
        trigger={<Button>Set radios</Button>}
      >
        {open && (
          <RadiosForm
            cpId={props.cpId}
            radios={radios}
            onDone={() => setOpen(false)}
          />
        )}
      </Modal>
    </section>
  );
}

type RadiosDraft = {
  frequency: string;
  tacanChannel: string;
  tacanBand: string;
  tacanCallsign: string;
  iclsChannel: string;
  iclsCallsign: string;
  link4: string;
};

function text(value: number | string | null | undefined): string {
  return value != null ? `${value}` : "";
}

function numberOrNull(value: string): number | null {
  return value.trim() === "" ? null : Number(value);
}

function RadiosForm(props: {
  cpId: string;
  radios: BaseRadios;
  onDone: () => void;
}) {
  const { radios } = props;
  const toast = useToast();
  const [setRadios, { isLoading }] = useSetBaseRadiosMutation();
  const [draft, setDraft] = useState<RadiosDraft>({
    frequency: text(radios.frequency_mhz),
    tacanChannel: text(radios.tacan_channel),
    tacanBand: radios.tacan_band ?? "X",
    tacanCallsign: text(radios.tacan_callsign),
    iclsChannel: text(radios.icls_channel),
    iclsCallsign: text(radios.icls_callsign),
    link4: text(radios.link4_mhz),
  });
  const set = (key: keyof RadiosDraft) => (value: string) =>
    setDraft({ ...draft, [key]: value });

  const save = async () => {
    const tacan = numberOrNull(draft.tacanChannel);
    const update: BaseRadiosUpdate = {
      frequency_mhz: numberOrNull(draft.frequency),
      tacan_channel: tacan,
      tacan_band: tacan !== null ? draft.tacanBand : null,
      tacan_callsign: draft.tacanCallsign || null,
      icls_channel: numberOrNull(draft.iclsChannel),
      icls_callsign: draft.iclsCallsign || null,
      link4_mhz: numberOrNull(draft.link4),
    };
    const refusal = refusalOf(
      await setRadios({ cpId: props.cpId, baseRadiosUpdateJs: update }),
    );
    if (refusal !== null) {
      toast({
        title: "Radios refused",
        description: commandErrorMessage(refusal),
        tone: "danger",
      });
    } else {
      toast({ title: "Radios saved", tone: "success" });
      props.onDone();
    }
  };

  return (
    <div className={airfield.form}>
      <p className={airfield.hint}>Leave a field empty for automatic.</p>
      {radios.has_frequency && (
        <TextField
          label="Frequency (MHz)"
          value={draft.frequency}
          onChange={set("frequency")}
        />
      )}
      {radios.has_tacan && (
        <>
          <TextField
            label="TACAN channel"
            value={draft.tacanChannel}
            onChange={set("tacanChannel")}
          />
          <label className={airfield.field}>
            TACAN band
            <select
              className={settings.select}
              value={draft.tacanBand}
              onChange={(event) => set("tacanBand")(event.target.value)}
            >
              <option value="X">X</option>
              <option value="Y">Y</option>
            </select>
          </label>
          <TextField
            label="TACAN callsign"
            value={draft.tacanCallsign}
            onChange={set("tacanCallsign")}
          />
        </>
      )}
      {radios.has_icls && (
        <>
          <TextField
            label="ICLS channel"
            value={draft.iclsChannel}
            onChange={set("iclsChannel")}
          />
          <TextField
            label="ICLS callsign"
            value={draft.iclsCallsign}
            onChange={set("iclsCallsign")}
          />
        </>
      )}
      {radios.has_link4 && (
        <TextField
          label="Link 4 (MHz)"
          value={draft.link4}
          onChange={set("link4")}
        />
      )}
      <div className={airfield.actions}>
        <ModalClose asChild>
          <Button>Cancel</Button>
        </ModalClose>
        <Button variant="primary" disabled={isLoading} onClick={save}>
          Save
        </Button>
      </div>
    </div>
  );
}

function TextField(props: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className={airfield.field}>
      {props.label}
      <input
        className={settings.select}
        value={props.value}
        onChange={(event) => props.onChange(event.target.value)}
      />
    </label>
  );
}
