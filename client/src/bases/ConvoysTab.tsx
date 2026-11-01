// "Departing convoys" tab (WEB-02.3): the Qt DepartingConvoysMenu. The convoys and
// cargo ships leaving this enemy base, and a package against one of them.
import { commandErrorMessage } from "../api/commands";
import {
  DepartingConvoy,
  useAttackDepartingConvoyMutation,
  useGetDepartingConvoysQuery,
} from "../api/liberationApi";
import { Button, useToast } from "../ui";
import styles from "./AirfieldTab.module.css";
import { Refusal, refusalOf } from "./orders";

export function ConvoysTab({ cpId }: { cpId: string }) {
  const { data, error, isLoading } = useGetDepartingConvoysQuery({ cpId });
  if (isLoading) {
    return <p className={styles.hint}>Loading the convoys…</p>;
  }
  if (error) {
    return (
      <p className={styles.hint} role="alert">
        {commandErrorMessage(error as Refusal)}
      </p>
    );
  }
  if (!data || data.length === 0) {
    return <p className={styles.hint}>No convoy is leaving this base.</p>;
  }
  return (
    <ul className={styles.convoys} aria-label="Departing convoys">
      {data.map((convoy) => (
        <ConvoyCard key={convoy.name} cpId={cpId} convoy={convoy} />
      ))}
    </ul>
  );
}

function ConvoyCard(props: { cpId: string; convoy: DepartingConvoy }) {
  const { cpId, convoy } = props;
  const toast = useToast();
  const [attack, { isLoading }] = useAttackDepartingConvoyMutation();
  const title = `${convoy.name} to ${convoy.destination}`;

  const onAttack = async () => {
    const refusal = refusalOf(
      await attack({
        cpId,
        destinationId: convoy.destination_id,
        kind: convoy.kind,
      }),
    );
    if (refusal !== null) {
      toast({
        title: "Could not plan the attack",
        description: commandErrorMessage(refusal),
        tone: "danger",
      });
    }
  };

  return (
    <li className={styles.incoming} aria-label={title}>
      <h3 className={styles.title}>{title}</h3>
      <ul>
        {convoy.units.map((unit) => (
          <li key={unit.name}>
            {unit.count} × {unit.name}
          </li>
        ))}
      </ul>
      <Button variant="danger" disabled={isLoading} onClick={onAttack}>
        Attack
      </Button>
    </li>
  );
}
