// Package selection shared by the command view (WEB-01.4, WEB-01.2): the
// timeline, the packages panel and the map select the same package.
//
// A package is keyed by the id of its first flight (the `id` of
// `TimelinePackage`), as the routes acting on a package through one of its
// flights. Selecting a package also selects that flight in `flightsSlice`, so
// the map highlights its flight plan. A flight selected elsewhere (map click,
// Qt) clears the explicit package key: its package is then found from the
// selected flight (`selectedPackageId`).
import { AppDispatch, RootState } from "../app/store";
import { gameLoaded, gameUnloaded } from "./actions";
import { deselectFlight, selectFlight } from "./flightsSlice";
import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface SelectionState {
  packageId: string | null;
}

const initialState: SelectionState = { packageId: null };

export const selectionSlice = createSlice({
  name: "selection",
  initialState,
  reducers: {
    packageSelected: (state, action: PayloadAction<string>) => {
      state.packageId = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(selectFlight, (state) => {
      state.packageId = null;
    });
    builder.addCase(deselectFlight, (state) => {
      state.packageId = null;
    });
    builder.addCase(gameLoaded, (state) => {
      state.packageId = null;
    });
    builder.addCase(gameUnloaded, (state) => {
      state.packageId = null;
    });
  },
});

export const { packageSelected } = selectionSlice.actions;

/** Selects a package and its lead flight (`leadFlightId`) for the map. */
export function selectPackage(
  dispatch: AppDispatch,
  packageId: string,
  leadFlightId: string = packageId,
) {
  dispatch(selectFlight(leadFlightId));
  dispatch(packageSelected(packageId));
}

export const selectSelectedPackageKey = (state: RootState) =>
  state.selection.packageId;

/**
 * The selected package among `packages`: the explicit package key, or the
 * package holding the selected flight; null when none is.
 */
export function selectedPackageId(
  packageKey: string | null,
  selectedFlightId: string | null,
  packages: { id: string; flight_ids: string[] }[],
): string | null {
  if (packageKey != null && packages.some((p) => p.id === packageKey)) {
    return packageKey;
  }
  if (selectedFlightId == null) {
    return null;
  }
  return (
    packages.find((p) => p.flight_ids.includes(selectedFlightId))?.id ?? null
  );
}

export default selectionSlice.reducer;
