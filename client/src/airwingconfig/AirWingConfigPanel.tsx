// Air wing configuration (WEB-06), the Qt AirWingConfigurationDialog: squadrons of
// each coalition and their factions, on the campaign the wizard just generated or on
// the campaign in play. Each change is a command applied at once; the engine lists
// the choices and refuses what is not allowed.
import { commandErrorMessage } from "../api/commands";
import {
  AirWingConfigSide,
  AirWingConfigSquadron,
  ConfigSide,
  ConfigTarget,
  useAddConfigFactionUnitMutation,
  useAddConfigSquadronMutation,
  useGetAirWingConfigQuery,
  useGetConfigFactionQuery,
  useGetConfigSquadronLiveriesQuery,
  useLoadAirWingFileMutation,
  useRemoveConfigSquadronMutation,
  useReplaceConfigSquadronMutation,
  useRerollConfigSquadronNicknameMutation,
  useSaveAirWingFileMutation,
  useSetConfigFactionDoctrineMutation,
  useSetConfigFactionJtacMutation,
  useSetConfigSquadronAutoAssignMutation,
  useSetConfigSquadronLiveryMutation,
  useUpdateConfigSquadronMutation,
} from "../api/liberationApi";
import { useCommand } from "../airwing/useCommand";
import {
  Button,
  ListCard,
  Modal,
  ModalClose,
  NumberField,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  useToast,
} from "../ui";
import styles from "./AirWingConfig.module.css";
import { FactionUnits } from "./FactionUnits";
import { useEffect, useState } from "react";

const SIDE_NAMES: Record<ConfigSide, string> = { blue: "Blue", red: "Red" };
const FACTION_NAMES: Record<ConfigSide, string> = {
  blue: "Faction OWNFOR",
  red: "Faction OPFOR",
};

interface TargetProps {
  target: ConfigTarget;
}

/** A text field that sends its value when it loses the focus. */
function CommitField({
  label,
  value,
  onCommit,
  multiline = false,
  disabled = false,
}: {
  label: string;
  value: string;
  onCommit: (value: string) => void;
  multiline?: boolean;
  disabled?: boolean;
}) {
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [value]);
  const commit = () => {
    if (draft !== value) {
      onCommit(draft);
    }
  };
  return (
    <label className={styles.field}>
      <span className={styles.label}>{label}</span>
      {multiline ? (
        <textarea
          className={styles.input}
          rows={3}
          value={draft}
          disabled={disabled}
          onChange={(event) => setDraft(event.target.value)}
          onBlur={commit}
        />
      ) : (
        <input
          className={styles.input}
          value={draft}
          disabled={disabled}
          onChange={(event) => setDraft(event.target.value)}
          onBlur={commit}
        />
      )}
    </label>
  );
}

function Liveries({
  target,
  squadronId,
}: TargetProps & { squadronId: string }) {
  const { data } = useGetConfigSquadronLiveriesQuery({ target, squadronId });
  const [setLivery] = useSetConfigSquadronLiveryMutation();
  const run = useCommand();
  if (!data || data.length === 0) {
    return null;
  }
  const selected = data.findIndex((choice) => choice.selected);
  return (
    <label className={styles.field}>
      <span className={styles.label}>Livery</span>
      <select
        className={styles.select}
        value={selected}
        onChange={(event) => {
          const choice = data[Number(event.target.value)];
          run(
            setLivery({
              target,
              squadronId,
              setLiveryJs: {
                livery_id: choice.livery_id,
                use_livery_set: choice.use_livery_set,
              },
            }),
            "Livery not changed",
          );
        }}
      >
        {data.map((choice, index) => (
          <option key={`${choice.label}-${index}`} value={index}>
            {choice.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function ReplaceWithPreset({
  target,
  squadron,
}: TargetProps & { squadron: AirWingConfigSquadron }) {
  const [open, setOpen] = useState(false);
  const [preset, setPreset] = useState<string>();
  const [replace] = useReplaceConfigSquadronMutation();
  const run = useCommand();
  const chosen = preset ?? squadron.presets[0];
  return (
    <Modal
      open={open}
      onOpenChange={setOpen}
      title="Replace with preset"
      description={`Same task, size and base; the player pilots stay. ${squadron.name} leaves.`}
      trigger={
        <Button disabled={squadron.presets.length === 0}>
          Replace with preset
        </Button>
      }
      footer={
        <>
          <ModalClose asChild>
            <Button>Cancel</Button>
          </ModalClose>
          <Button
            variant="primary"
            onClick={async () => {
              await run(
                replace({
                  target,
                  squadronId: squadron.id,
                  replacePresetJs: { preset: chosen },
                }),
                "Squadron not replaced",
              );
              setOpen(false);
            }}
          >
            Replace
          </Button>
        </>
      }
    >
      <label className={styles.field}>
        <span className={styles.label}>Preset</span>
        <select
          className={styles.select}
          value={chosen}
          onChange={(event) => setPreset(event.target.value)}
        >
          {squadron.presets.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>
    </Modal>
  );
}

function SquadronEditor({
  target,
  squadron,
}: TargetProps & { squadron: AirWingConfigSquadron }) {
  const [update] = useUpdateConfigSquadronMutation();
  const [remove] = useRemoveConfigSquadronMutation();
  const [reroll] = useRerollConfigSquadronNicknameMutation();
  const [autoAssign] = useSetConfigSquadronAutoAssignMutation();
  const run = useCommand();
  const change = (squadronConfigUpdateJs: Record<string, unknown>) =>
    run(
      update({ target, squadronId: squadron.id, squadronConfigUpdateJs }),
      "Squadron not changed",
    );
  const { required, total, fitting } = squadron.parking;
  return (
    <article className={styles.editor} aria-label={squadron.name}>
      <h3 className={styles.editorTitle}>
        {squadron.name} · {squadron.aircraft}
      </h3>
      <div className={styles.fields}>
        <CommitField
          label="Name"
          value={squadron.name}
          onCommit={(name) => change({ name })}
        />
        <CommitField
          label="Nickname"
          value={squadron.nickname ?? ""}
          onCommit={(nickname) => change({ nickname })}
        />
        <div className={styles.field}>
          <span className={styles.label}>&nbsp;</span>
          <Button
           
            onClick={() =>
              run(
                reroll({ target, squadronId: squadron.id }),
                "Nickname not changed",
              )
            }
          >
            Re-roll nickname
          </Button>
        </div>
        <Liveries target={target} squadronId={squadron.id} />
        <NumberField
          label="Max size"
          value={squadron.max_size}
          min={1}
          step={1}
          onValueChange={(max_size) => change({ max_size })}
        />
        <label className={styles.field}>
          <span className={styles.label}>Primary task</span>
          <select
            className={styles.select}
            value={squadron.primary_task}
            onChange={(event) => change({ primary_task: event.target.value })}
          >
            {squadron.primary_tasks.map((task) => (
              <option key={task} value={task}>
                {task}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          <span className={styles.label}>Base</span>
          <select
            className={styles.select}
            value={squadron.base_id}
            onChange={(event) => change({ base_id: event.target.value })}
          >
            {squadron.bases.map((base) => (
              <option key={base.id} value={base.id}>
                {base.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className={styles.hint}>
        Parking slots required: {required} · available: {total}
        {fitting != null && ` · that fit this aircraft: ${fitting}`}
      </p>
      <CommitField
        label={
          squadron.player_names_refusal ?? "Player pilots, one name per line"
        }
        multiline
        disabled={squadron.player_names_refusal != null}
        value={squadron.player_names.join("\n")}
        onCommit={(text) => change({ player_names: text.split("\n") })}
      />
      <fieldset className={styles.tasks}>
        <legend className={styles.label}>Auto-assign</legend>
        {squadron.tasks.map((task) => (
          <label key={task.task} className={styles.check}>
            <input
              type="checkbox"
              checked={task.auto_assign}
              onChange={(event) =>
                run(
                  autoAssign({
                    target,
                    squadronId: squadron.id,
                    autoAssignJs: {
                      task: task.task,
                      enabled: event.target.checked,
                    },
                  }),
                  "Task not changed",
                )
              }
            />
            {task.task}
          </label>
        ))}
      </fieldset>
      <div className={styles.buttons}>
        <ReplaceWithPreset target={target} squadron={squadron} />
        <Button
         
          variant="danger"
          onClick={() =>
            run(
              remove({ target, squadronId: squadron.id }),
              "Squadron not removed",
            )
          }
        >
          Remove squadron
        </Button>
      </div>
    </article>
  );
}

function AddSquadron({
  target,
  side,
}: TargetProps & { side: AirWingConfigSide }) {
  const [open, setOpen] = useState(false);
  const [aircraftId, setAircraftId] = useState<string>();
  const [task, setTask] = useState<string>();
  const [baseId, setBaseId] = useState<string>();
  const [preset, setPreset] = useState("");
  const [add] = useAddConfigSquadronMutation();
  const run = useCommand();
  const options = side.aircraft_options;
  const option = options.find((o) => o.aircraft_id === aircraftId) ?? options[0];
  const chosenTask =
    task !== undefined && option?.primary_tasks.includes(task)
      ? task
      : option?.primary_tasks[0];
  const chosenBase =
    option?.bases.find((base) => base.id === baseId) ?? option?.bases[0];
  return (
    <Modal
      open={open}
      onOpenChange={setOpen}
      title="Add new squadron"
      trigger={
        <Button disabled={options.length === 0}>
          Add squadron
        </Button>
      }
      footer={
        <>
          <ModalClose asChild>
            <Button>Cancel</Button>
          </ModalClose>
          <Button
            variant="primary"
            disabled={!option || !chosenTask || !chosenBase}
            onClick={async () => {
              await run(
                add({
                  target,
                  side: side.side as ConfigSide,
                  configNewSquadronJs: {
                    aircraft_id: option.aircraft_id,
                    base_id: chosenBase!.id,
                    primary_task: chosenTask!,
                    preset: preset === "" ? undefined : preset,
                  },
                }),
                "Squadron not added",
              );
              setOpen(false);
            }}
          >
            Add
          </Button>
        </>
      }
    >
      <div className={styles.fields}>
        <label className={styles.field}>
          <span className={styles.label}>Aircraft</span>
          <select
            className={styles.select}
            value={option?.aircraft_id}
            onChange={(event) => {
              setAircraftId(event.target.value);
              setPreset("");
            }}
          >
            {options.map((o) => (
              <option key={o.aircraft_id} value={o.aircraft_id}>
                {o.aircraft}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          <span className={styles.label}>Primary task</span>
          <select
            className={styles.select}
            value={chosenTask}
            onChange={(event) => setTask(event.target.value)}
          >
            {option?.primary_tasks.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          <span className={styles.label}>Base</span>
          <select
            className={styles.select}
            value={chosenBase?.id}
            onChange={(event) => setBaseId(event.target.value)}
          >
            {option?.bases.map((base) => (
              <option key={base.id} value={base.id}>
                {base.name}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          <span className={styles.label}>Preset</span>
          <select
            className={styles.select}
            value={preset}
            onChange={(event) => setPreset(event.target.value)}
          >
            <option value="">Random</option>
            {option?.presets.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
      </div>
    </Modal>
  );
}

function SideSquadrons({
  target,
  side,
}: TargetProps & { side: AirWingConfigSide }) {
  const [selectedId, setSelectedId] = useState<string>();
  const [save] = useSaveAirWingFileMutation();
  const [load] = useLoadAirWingFileMutation();
  const toast = useToast();
  const sideId = side.side as ConfigSide;
  const selected =
    side.squadrons.find((s) => s.id === selectedId) ?? side.squadrons[0];

  const file = async (
    pending: Promise<{ data: { path?: string | null } } | { error: unknown }>,
    done: string,
  ) => {
    const result = await pending;
    if ("error" in result) {
      toast({
        title: "Air wing file not used",
        description: commandErrorMessage(
          result.error as Parameters<typeof commandErrorMessage>[0],
        ),
        tone: "danger",
      });
    } else if (result.data.path != null) {
      toast({ title: done, description: result.data.path });
    }
  };

  return (
    <div className={styles.side}>
      <div className={styles.buttons}>
        <AddSquadron target={target} side={side} />
        <Button
         
          onClick={() =>
            file(
              load({ target, side: sideId }) as never,
              "Air wing loaded",
            )
          }
        >
          Load config
        </Button>
        <Button
         
          onClick={() =>
            file(save({ target, side: sideId }) as never, "Air wing saved")
          }
        >
          Save config
        </Button>
      </div>
      {side.squadrons.length === 0 ? (
        <p className={styles.hint}>This air wing has no squadron.</p>
      ) : (
        <div className={styles.columns}>
          <aside className={styles.list} aria-label="Squadrons">
            {side.squadrons.map((squadron) => (
              <ListCard
                key={squadron.id}
                title={squadron.name}
                meta={squadron.max_size}
                subtitle={`${squadron.aircraft} · ${squadron.primary_task}`}
                selected={squadron.id === selected?.id}
                onSelect={() => setSelectedId(squadron.id)}
              />
            ))}
          </aside>
          {selected && (
            <SquadronEditor
              key={selected.id}
              target={target}
              squadron={selected}
            />
          )}
        </div>
      )}
    </div>
  );
}

function FactionTab({ target, side }: TargetProps & { side: ConfigSide }) {
  const { data, error } = useGetConfigFactionQuery({ target, side });
  const [addUnit] = useAddConfigFactionUnitMutation();
  const [setJtac] = useSetConfigFactionJtacMutation();
  const [setDoctrine] = useSetConfigFactionDoctrineMutation();
  const run = useCommand();
  if (error) {
    return <p role="alert">{commandErrorMessage(error)}</p>;
  }
  if (!data) {
    return <p className={styles.hint}>Loading the faction…</p>;
  }
  return (
    <FactionUnits
      sheet={data}
      hasJtac={data.has_jtac}
      doctrine={data.doctrine}
      onAddUnit={(group, unit) =>
        run(
          addUnit({ target, side, factionUnitJs: { group, unit } }),
          "Unit not added",
        )
      }
      onJtacChange={(has_jtac) =>
        run(
          setJtac({ target, side, factionJtacJs: { has_jtac } }),
          "JTAC not changed",
        )
      }
      onDoctrineChange={(doctrine) =>
        run(
          setDoctrine({ target, side, factionDoctrineJs: { doctrine } }),
          "Doctrine not changed",
        )
      }
    />
  );
}

export function AirWingConfigPanel({ target }: TargetProps) {
  const { data, error } = useGetAirWingConfigQuery(
    { target },
    { refetchOnMountOrArgChange: true },
  );
  if (error) {
    return <p role="alert">{commandErrorMessage(error)}</p>;
  }
  if (!data) {
    return <p className={styles.hint}>Loading the air wing…</p>;
  }
  return (
    <div className={styles.panel}>
      {data.replans && (
        <p className={styles.hint}>
          Moving, adding or removing a squadron replans this turn for its
          coalition: the packages of that coalition are planned again.
        </p>
      )}
      <Tabs defaultValue="blue">
        <TabsList aria-label="Air wing configuration">
          {data.sides.map((side) => (
            <TabsTrigger key={side.side} value={side.side}>
              {SIDE_NAMES[side.side as ConfigSide]}
            </TabsTrigger>
          ))}
          {data.sides.map((side) => (
            <TabsTrigger key={`f-${side.side}`} value={`faction-${side.side}`}>
              {FACTION_NAMES[side.side as ConfigSide]}
            </TabsTrigger>
          ))}
        </TabsList>
        {data.sides.map((side) => (
          <TabsContent key={side.side} value={side.side}>
            <SideSquadrons target={target} side={side} />
          </TabsContent>
        ))}
        {data.sides.map((side) => (
          <TabsContent key={`f-${side.side}`} value={`faction-${side.side}`}>
            <FactionTab target={target} side={side.side as ConfigSide} />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
