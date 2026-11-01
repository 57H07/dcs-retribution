// Payload tab of a flight (WEB-04.3), after QFlightPayloadTab. Each change is a command
// that applies at once; the server lists what is possible and has the last word, so a
// pylon only ever offers what the engine says it accepts.
import { commandErrorMessage } from "../api/commands";
import {
  FlightPayload,
  MemberPayload,
  MemberPylon,
  PayloadPylonOptions,
  PayloadProperty,
  WeaponSetting,
  useBackupFlightPayloadsMutation,
  useGetFlightPayloadQuery,
  useResetMemberWeaponSettingsMutation,
  useSaveMemberPayloadMutation,
  useSetFlightFuelMutation,
  useSetMemberCustomLoadoutMutation,
  useSetMemberLiveryMutation,
  useSetMemberLoadoutMutation,
  useSetMemberPropertyMutation,
  useSetMemberPylonMutation,
  useSetMemberTgpLaserCodeMutation,
  useSetMemberWeaponLaserCodeMutation,
  useSetMemberWeaponSettingMutation,
  useSetSameLiveryMutation,
  useSetSameLoadoutMutation,
} from "../api/liberationApi";
import settings from "../settings/SettingsScreen.module.css";
import {
  Button,
  Modal,
  ModalClose,
  NumberField,
  Switch,
  useToast,
} from "../ui";
import styles from "./PayloadTab.module.css";
import { useEffect, useState } from "react";

const KG_TO_LBS = 1 / 0.45359237;

type Result = { error?: unknown } | { data: unknown };
type Report = (title: string, result: Result) => void;
type OptionValue = boolean | number | string | null | undefined;

function useReport(): Report {
  const toast = useToast();
  return (title, result) => {
    if ("error" in result && result.error !== undefined) {
      toast({
        title,
        description: commandErrorMessage(
          result.error as Parameters<typeof commandErrorMessage>[0],
        ),
        tone: "danger",
      });
    }
  };
}

export interface PayloadTabProps {
  packageId: string;
  flightId: string;
}

export function PayloadTab({ packageId, flightId }: PayloadTabProps) {
  const { data, error, isLoading } = useGetFlightPayloadQuery({
    packageId,
    flightId,
  });
  if (isLoading) {
    return <p className={styles.hint}>Loading the payload…</p>;
  }
  if (error || data == null) {
    return (
      <p className={styles.hint} role="alert">
        {(error && commandErrorMessage(error)) ??
          "This payload is not available."}
      </p>
    );
  }
  return <PayloadBody ids={{ packageId, flightId }} payload={data} />;
}

interface FlightIds {
  packageId: string;
  flightId: string;
}

function PayloadBody({
  ids,
  payload,
}: {
  ids: FlightIds;
  payload: FlightPayload;
}) {
  const report = useReport();
  const [setSameLoadout] = useSetSameLoadoutMutation();
  const [setSameLivery] = useSetSameLiveryMutation();
  const [selected, setSelected] = useState(0);
  // A flight can shrink under the tab.
  const index = Math.min(selected, payload.members.length - 1);
  const member = payload.members[index];
  if (member === undefined) {
    return <p className={styles.hint}>This flight has no member.</p>;
  }
  const loadoutLocked = payload.same_loadout && index !== 0;
  const liveryLocked = payload.same_livery && index !== 0;

  return (
    <div className={styles.tab}>
      <div className={styles.row}>
        <div
          role="tablist"
          aria-label="Flight member"
          className={styles.members}
        >
          {payload.members.map((m) => (
            <button
              key={m.index}
              type="button"
              role="tab"
              aria-selected={m.index === index}
              className={styles.member}
              onClick={() => setSelected(m.index)}
            >
              {m.index + 1} · {m.pilot ?? "No pilot"}
              {m.is_player ? " (player)" : ""}
            </button>
          ))}
        </div>
      </div>
      <div className={styles.row}>
        <Switch
          label="Same loadout for all members"
          checked={payload.same_loadout}
          onCheckedChange={async (same) =>
            report(
              "Could not change the shared loadout",
              await setSameLoadout({ ...ids, sameForAllJs: { same } }),
            )
          }
        />
        <Switch
          label="Same livery for all members"
          checked={payload.same_livery}
          onCheckedChange={async (same) =>
            report(
              "Could not change the shared livery",
              await setSameLivery({ ...ids, sameForAllJs: { same } }),
            )
          }
        />
      </div>
      {!payload.same_loadout && (
        <p className={styles.warning}>
          AI flights should use the same loadout for all members.
        </p>
      )}
      <FuelField ids={ids} payload={payload} />
      <LoadoutSection
        ids={ids}
        payload={payload}
        member={member}
        locked={loadoutLocked}
      />
      <LaserSection ids={ids} member={member} />
      <LiverySection ids={ids} member={member} locked={liveryLocked} />
      <PropertiesSection ids={ids} payload={payload} member={member} />
    </div>
  );
}

function FuelField({
  ids,
  payload,
}: {
  ids: FlightIds;
  payload: FlightPayload;
}) {
  const report = useReport();
  const [setFuel] = useSetFlightFuelMutation();
  return (
    <div className={styles.row}>
      <NumberField
        label="Internal fuel"
        unit="kg"
        value={payload.fuel}
        min={0}
        max={payload.fuel_max}
        onValueChange={async (fuel) =>
          report(
            "Could not set the fuel",
            await setFuel({ ...ids, flightFuelJs: { fuel } }),
          )
        }
      />
      <span className={styles.hint}>
        {Math.round(payload.fuel * KG_TO_LBS)} lbs, of{" "}
        {Math.round(payload.fuel_max * KG_TO_LBS)} lbs
      </span>
    </div>
  );
}

function LoadoutSection({
  ids,
  payload,
  member,
  locked,
}: {
  ids: FlightIds;
  payload: FlightPayload;
  member: MemberPayload;
  locked: boolean;
}) {
  const report = useReport();
  const toast = useToast();
  const [setLoadout] = useSetMemberLoadoutMutation();
  const [setCustom] = useSetMemberCustomLoadoutMutation();
  const [backup] = useBackupFlightPayloadsMutation();
  const memberIds = { ...ids, memberIndex: member.index };
  const names = payload.loadouts.includes(member.loadout)
    ? payload.loadouts
    : [member.loadout, ...payload.loadouts];

  const runBackup = async () => {
    const result = await backup(ids);
    report("Could not back up the payloads", result);
    if ("data" in result) {
      toast({
        title:
          result.data.path != null
            ? "Payloads backed up"
            : "No payload file to back up yet",
        description: result.data.path ?? undefined,
      });
    }
  };

  return (
    <section className={styles.section} aria-label="Loadout">
      <h3 className={styles.title}>Loadout</h3>
      <div className={styles.row}>
        <label className={styles.field}>
          Named loadout
          <select
            className={settings.select}
            value={member.loadout}
            disabled={locked || member.custom}
            onChange={async (event) =>
              report(
                "Could not change the loadout",
                await setLoadout({
                  ...memberIds,
                  memberLoadoutNameJs: { name: event.target.value },
                }),
              )
            }
          >
            {names.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <Switch
          label="Custom loadout"
          checked={member.custom}
          disabled={locked}
          onCheckedChange={async (custom) =>
            report(
              "Could not change the loadout",
              await setCustom({
                ...memberIds,
                memberCustomLoadoutJs: { custom },
              }),
            )
          }
        />
        {member.custom && !locked && (
          <SavePayloadButton ids={ids} member={member} />
        )}
        <Button onClick={runBackup}>Create backup</Button>
      </div>
      {locked && (
        <p className={styles.hint}>
          All members share the loadout of member 1.
        </p>
      )}
      {payload.restrict_weapons_by_date && (
        <p className={styles.hint}>
          Weapons are restricted to those available on {payload.date}.
        </p>
      )}
      <ul className={styles.pylons} aria-label="Pylons">
        {payload.pylons.map((options) => {
          const pylon = member.pylons.find((p) => p.number === options.number);
          return pylon === undefined ? null : (
            <PylonRow
              key={options.number}
              ids={ids}
              member={member}
              options={options}
              pylon={pylon}
              editable={member.custom && !locked}
            />
          );
        })}
      </ul>
    </section>
  );
}

function PylonRow({
  ids,
  member,
  options,
  pylon,
  editable,
}: {
  ids: FlightIds;
  member: MemberPayload;
  options: PayloadPylonOptions;
  pylon: MemberPylon;
  editable: boolean;
}) {
  const report = useReport();
  const [setPylon] = useSetMemberPylonMutation();
  const current = pylon.weapon;
  const offered = options.weapons.some((w) => w.clsid === current?.clsid);

  return (
    <li className={styles.pylon}>
      <span className={styles.pylonNumber}>{options.number}</span>
      <select
        className={settings.select}
        aria-label={`Pylon ${options.number}`}
        value={current?.clsid ?? ""}
        disabled={!editable}
        onChange={async (event) =>
          report(
            `Could not change pylon ${options.number}`,
            await setPylon({
              ...ids,
              memberIndex: member.index,
              number: options.number,
              memberPylonWeaponJs: {
                clsid:
                  event.target.value === "" ? undefined : event.target.value,
              },
            }),
          )
        }
      >
        <option value="">None</option>
        {current != null && !offered && (
          // Carried by the loadout, but not something the engine offers here.
          <option value={current.clsid} disabled>
            {current.name}
          </option>
        )}
        {options.weapons.map((weapon) => (
          <option key={weapon.clsid} value={weapon.clsid}>
            {weapon.name}
          </option>
        ))}
      </select>
      {pylon.settings.length > 0 && editable && (
        <WeaponSettingsButton ids={ids} member={member} pylon={pylon} />
      )}
      {pylon.replaced_weapon != null && (
        <span className={styles.hint}>
          Replaces {pylon.replaced_weapon} (not available yet)
        </span>
      )}
    </li>
  );
}

function SavePayloadButton({
  ids,
  member,
}: {
  ids: FlightIds;
  member: MemberPayload;
}) {
  const toast = useToast();
  const report = useReport();
  const [save, saveState] = useSaveMemberPayloadMutation();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("Custom");

  const submit = async () => {
    const result = await save({
      ...ids,
      memberIndex: member.index,
      savePayloadJs: { name },
    });
    report("Could not save the payload", result);
    if ("data" in result) {
      setOpen(false);
      toast({
        title: "Payload saved",
        description: result.data.path ?? undefined,
      });
    }
  };

  return (
    <Modal
      title="Save payload"
      open={open}
      onOpenChange={setOpen}
      trigger={<Button>Save payload</Button>}
    >
      <div className={styles.form}>
        <label className={styles.field}>
          Name of the payload
          <input
            className={styles.input}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <div className={styles.formActions}>
          <ModalClose asChild>
            <Button>Cancel</Button>
          </ModalClose>
          <Button
            variant="primary"
            disabled={saveState.isLoading}
            onClick={submit}
          >
            Save
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function WeaponSettingsButton({
  ids,
  member,
  pylon,
}: {
  ids: FlightIds;
  member: MemberPayload;
  pylon: MemberPylon;
}) {
  const report = useReport();
  const [setSetting] = useSetMemberWeaponSettingMutation();
  const [reset] = useResetMemberWeaponSettingsMutation();
  const pylonIds = {
    ...ids,
    memberIndex: member.index,
    number: pylon.number,
  };
  const change = async (id: string, value: OptionValue) =>
    report(
      "Could not change the setting",
      await setSetting({ ...pylonIds, payloadValueJs: { id, value } }),
    );

  return (
    <Modal
      title={`${pylon.weapon?.name ?? "Weapon"} settings`}
      trigger={<Button>Settings</Button>}
    >
      <div className={styles.form}>
        {pylon.settings.map((setting) => (
          <WeaponSettingField
            key={setting.id}
            setting={setting}
            onChange={(value) => change(setting.id, value)}
          />
        ))}
        <div className={styles.formActions}>
          <Button
            onClick={async () =>
              report("Could not reset the settings", await reset(pylonIds))
            }
          >
            Reset to defaults
          </Button>
          <ModalClose asChild>
            <Button variant="primary">Close</Button>
          </ModalClose>
        </div>
      </div>
    </Modal>
  );
}

function WeaponSettingField({
  setting,
  onChange,
}: {
  setting: WeaponSetting;
  onChange: (value: OptionValue) => void;
}) {
  if (setting.control === "comboList") {
    return (
      <OptionSelect
        label={setting.label}
        options={setting.options}
        value={setting.value}
        disabled={setting.read_only}
        onChange={onChange}
      />
    );
  }
  return (
    <NumberField
      label={setting.label}
      unit={setting.unit ?? undefined}
      value={Number(setting.value ?? 0)}
      min={setting.minimum ?? undefined}
      max={setting.maximum ?? undefined}
      step={setting.control === "doubleSpinbox" ? 0.001 : 1}
      disabled={setting.read_only}
      onValueChange={onChange}
    />
  );
}

/** A list of engine values: they may be numbers or null, so options go by position. */
function OptionSelect({
  label,
  options,
  value,
  disabled,
  onChange,
}: {
  label: string;
  options: { id?: OptionValue; label: string }[];
  value: OptionValue;
  disabled?: boolean;
  onChange: (value: OptionValue) => void;
}) {
  const index = options.findIndex((o) => (o.id ?? null) === (value ?? null));
  return (
    <label className={styles.field}>
      {label}
      <select
        className={settings.select}
        value={index}
        disabled={disabled}
        onChange={(event) =>
          onChange(options[Number(event.target.value)]?.id ?? null)
        }
      >
        {index < 0 && <option value={-1}>{String(value ?? "")}</option>}
        {options.map((option, position) => (
          <option key={position} value={position}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function LaserSection({
  ids,
  member,
}: {
  ids: FlightIds;
  member: MemberPayload;
}) {
  const report = useReport();
  const [setTgp] = useSetMemberTgpLaserCodeMutation();
  const [setWeapon] = useSetMemberWeaponLaserCodeMutation();
  const memberIds = { ...ids, memberIndex: member.index };
  const assigned = member.tgp_laser_code != null;

  return (
    <section className={styles.section} aria-label="Laser codes">
      <h3 className={styles.title}>Laser codes</h3>
      <div className={styles.row}>
        <span>
          Assigned TGP laser code:{" "}
          {member.tgp_laser_code ??
            (member.is_player ? "Not assigned" : "AI does not use laser codes")}
        </span>
        <Button
          disabled={!assigned && !member.is_player}
          onClick={async () =>
            report(
              "Could not change the laser code",
              await setTgp({
                ...memberIds,
                tgpLaserCodeJs: { assigned: !assigned },
              }),
            )
          }
        >
          {assigned ? "Release" : "Assign"}
        </Button>
      </div>
      {member.weapon_laser_codes.length > 0 && (
        <>
          <OptionSelect
            label="Preset laser code for weapons"
            options={member.weapon_laser_codes.map((choice) => ({
              id: choice.code,
              label: choice.label,
            }))}
            value={member.weapon_laser_code}
            onChange={async (code) =>
              report(
                "Could not change the laser code",
                await setWeapon({
                  ...memberIds,
                  weaponLaserCodeChoiceJs: {
                    code: typeof code === "number" ? code : undefined,
                  },
                }),
              )
            }
          />
          <p className={styles.hint}>
            Equipped weapons will be pre-configured to the selected laser code
            at mission start.
          </p>
        </>
      )}
    </section>
  );
}

function LiverySection({
  ids,
  member,
  locked,
}: {
  ids: FlightIds;
  member: MemberPayload;
  locked: boolean;
}) {
  const report = useReport();
  const [setLivery] = useSetMemberLiveryMutation();
  const index = member.liveries.findIndex((choice) => choice.selected);
  if (member.liveries.length === 0) {
    return null;
  }
  return (
    <section className={styles.section} aria-label="Livery">
      <h3 className={styles.title}>Livery</h3>
      <label className={styles.field}>
        Livery
        <select
          className={settings.select}
          value={index}
          disabled={locked}
          onChange={async (event) => {
            const choice = member.liveries[Number(event.target.value)];
            report(
              "Could not change the livery",
              await setLivery({
                ...ids,
                memberIndex: member.index,
                memberLiveryJs: {
                  livery_id: choice.livery_id,
                  use_livery_set: choice.use_livery_set,
                },
              }),
            );
          }}
        >
          {member.liveries.map((choice, position) => (
            <option key={position} value={position}>
              {choice.label}
            </option>
          ))}
        </select>
      </label>
    </section>
  );
}

function PropertiesSection({
  ids,
  payload,
  member,
}: {
  ids: FlightIds;
  payload: FlightPayload;
  member: MemberPayload;
}) {
  const report = useReport();
  const [setProperty] = useSetMemberPropertyMutation();
  if (payload.properties.length === 0) {
    return null;
  }
  const change = async (id: string, value: OptionValue) =>
    report(
      "Could not change the option",
      await setProperty({
        ...ids,
        memberIndex: member.index,
        payloadValueJs: { id, value },
      }),
    );

  return (
    <section className={styles.section} aria-label="Aircraft options">
      <h3 className={styles.title}>Aircraft options</h3>
      <div className={styles.properties}>
        {payload.properties.map((property, position) => {
          const previous = payload.properties[position - 1];
          const heading =
            property.section != null && property.section !== previous?.section;
          return (
            <div key={property.id} className={styles.property}>
              {heading && (
                <h4 className={styles.subtitle}>{property.section}</h4>
              )}
              <PropertyField
                property={property}
                value={member.properties[property.id]}
                onChange={(value) => change(property.id, value)}
              />
            </div>
          );
        })}
      </div>
    </section>
  );
}

function PropertyField({
  property,
  value,
  onChange,
}: {
  property: PayloadProperty;
  value: OptionValue;
  onChange: (value: OptionValue) => void;
}) {
  switch (property.control) {
    case "checkbox":
      return (
        <Switch
          label={property.label}
          checked={value === true}
          onCheckedChange={onChange}
        />
      );
    case "comboList":
      return (
        <OptionSelect
          label={property.label}
          options={property.options}
          value={value}
          onChange={onChange}
        />
      );
    case "editbox":
      return (
        <PropertyText
          label={property.label}
          value={value == null ? "" : String(value)}
          onChange={onChange}
        />
      );
    default:
      return (
        <NumberField
          label={property.label}
          value={Number(value ?? 0)}
          min={property.minimum ?? undefined}
          max={property.maximum ?? undefined}
          onValueChange={onChange}
        />
      );
  }
}

/** Sent when left: the engine checks and completes the text, then it comes back. */
function PropertyText({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [value]);
  const commit = () => {
    if (draft !== value) {
      onChange(draft);
    }
  };
  return (
    <label className={styles.field}>
      {label}
      <input
        className={styles.input}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            commit();
          }
        }}
      />
    </label>
  );
}
