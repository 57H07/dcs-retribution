// Pending transfers (WEB-08.2): the Qt PendingTransfersDialog. The engine lists
// the player's transfers (GET /transfers) and cancels one (DELETE
// /transfers/{id}): its units return to the origin's inventory.
import { commandErrorMessage } from "../api/commands";
import {
  TransferJs,
  useCancelTransferMutation,
  useListTransfersQuery,
} from "../api/liberationApi";
import { Button, useToast } from "../ui";
import { QueryBody, ScreenFrame } from "./ScreenFrame";
import styles from "./Secondary.module.css";

function unitsText(transfer: TransferJs): string {
  return transfer.units.map((u) => `${u.count} × ${u.name}`).join(", ");
}

function TransferCard({ transfer }: { transfer: TransferJs }) {
  const toast = useToast();
  const [cancel, { isLoading }] = useCancelTransferMutation();
  const title = `${transfer.origin} → ${transfer.destination}`;
  const onCancel = async () => {
    const result = await cancel({ transferId: transfer.id });
    if ("error" in result && result.error !== undefined) {
      toast({
        title: "Could not cancel the transfer",
        description: commandErrorMessage(result.error),
        tone: "danger",
      });
    } else {
      toast({
        title: "Transfer cancelled",
        description: `${transfer.size} units back at ${transfer.origin}.`,
        tone: "success",
      });
    }
  };
  return (
    <li className={styles.card} aria-label={title}>
      <div className={styles.cardMain}>
        <h2 className={styles.cardTitle}>
          {title} <span className={styles.count}>{transfer.size}</span>
        </h2>
        <span className={styles.cardDetail}>{unitsText(transfer)}</span>
        <span className={styles.cardDetail}>
          {transfer.position !== transfer.origin &&
            `Now at ${transfer.position}. `}
          {transfer.transport}
        </span>
      </div>
      <Button variant="danger" onClick={onCancel} disabled={isLoading}>
        Cancel transfer
      </Button>
    </li>
  );
}

export function TransfersScreen() {
  const query = useListTransfersQuery(undefined, {
    refetchOnMountOrArgChange: true,
  });
  return (
    <ScreenFrame title="Transfers">
      <QueryBody query={query} name="transfers">
        {(transfers) =>
          transfers.length === 0 ? (
            <p className={styles.state}>No pending transfer.</p>
          ) : (
            <ul className={styles.list} aria-label="Pending transfers">
              {transfers.map((transfer) => (
                <TransferCard key={transfer.id} transfer={transfer} />
              ))}
            </ul>
          )
        }
      </QueryBody>
    </ScreenFrame>
  );
}
