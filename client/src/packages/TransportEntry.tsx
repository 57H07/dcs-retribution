// The Transport mission entry of a new package on a player base (the button of the Qt
// QNewPackageDialog, WEB-04.5). A Transport mission plans its own package: once it is
// ordered, the empty one that led here goes away, as when Qt rejected its dialog.
import { PackageDetail, useDeletePackageMutation } from "../api/liberationApi";
import { TransferButton } from "../bases/TransferDialog";
import { PATHS } from "../shell/paths";
import { useNavigate } from "react-router-dom";

export function TransportEntry({ pkg }: { pkg: PackageDetail }) {
  const navigate = useNavigate();
  const [deletePackage] = useDeletePackageMutation();
  if (pkg.transport_origin_id == null) {
    return null;
  }
  return (
    <TransferButton
      cpId={pkg.transport_origin_id}
      baseName={pkg.target}
      kind="transport"
      onOrdered={async () => {
        await deletePackage({ packageId: pkg.id });
        navigate(PATHS.command);
      }}
    />
  );
}
