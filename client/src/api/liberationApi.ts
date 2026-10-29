import { _liberationApi } from "./_liberationApi";

// See https://redux-toolkit.js.org/rtk-query/usage/automated-refetching for an
// explanation of tag behavior.

export enum Tags {
  FLIGHT_PLAN = "FlightPlan",
  TOP_BAR = "TopBar",
  SETTINGS = "Settings",
  PREFERENCES = "Preferences",
}

const LIST_ID = "LIST";

function providesList<R extends { id: string | number }[], T extends string>(
  resultsWithIds: R | undefined,
  tagType: T,
) {
  return resultsWithIds
    ? [
        { type: tagType, id: LIST_ID },
        ...resultsWithIds.map(({ id }) => ({ type: tagType, id })),
      ]
    : [{ type: tagType, id: LIST_ID }];
}

export const liberationApi = _liberationApi.enhanceEndpoints({
  addTagTypes: Object.values(Tags),
  endpoints: {
    // /game/ (WEB-01.1): the top bar refreshes after each turn action.
    getTopBar: { providesTags: [Tags.TOP_BAR] },
    passTurn: { invalidatesTags: [Tags.TOP_BAR] },
    fixTots: { invalidatesTags: [Tags.TOP_BAR] },
    generateMission: { invalidatesTags: [Tags.TOP_BAR] },
    setSimSpeed: { invalidatesTags: [Tags.TOP_BAR] },
    // /debug/waypoint-geometries
    getDebugHoldZones: {
      providesTags: (result, error, arg) => [
        { type: Tags.FLIGHT_PLAN, id: arg.flightId },
      ],
    },
    getDebugJoinZones: {
      providesTags: (result, error, arg) => [
        { type: Tags.FLIGHT_PLAN, id: arg.flightId },
      ],
    },
    // /flights/
    getCommitBoundaryForFlight: {
      providesTags: (result, error, arg) => [
        { type: Tags.FLIGHT_PLAN, id: arg.flightId },
      ],
    },
    getFlightById: {
      providesTags: (result, error, arg) => [
        { type: Tags.FLIGHT_PLAN, id: arg.flightId },
      ],
    },
    listFlights: {
      providesTags: (result) => providesList(result, Tags.FLIGHT_PLAN),
    },
    // /settings/ (WEB-07.1): a change reloads the whole schema (values, markers).
    getSettings: { providesTags: [Tags.SETTINGS] },
    // A setting (cheats, fast forward...) may change what the top bar shows.
    setSetting: { invalidatesTags: [Tags.SETTINGS, Tags.TOP_BAR] },
    resetSettingsPage: { invalidatesTags: [Tags.SETTINGS, Tags.TOP_BAR] },
    // /preferences/ (WEB-07.2): saving reloads the state (problems, first start).
    getInstallPreferences: { providesTags: [Tags.PREFERENCES] },
    setInstallPreferences: { invalidatesTags: [Tags.PREFERENCES] },
    // /waypoints/
    listAllWaypointsForFlight: {
      providesTags: (result, error, arg) => [
        { type: Tags.FLIGHT_PLAN, id: arg.flightId },
      ],
    },
    setWaypointPosition: {
      invalidatesTags: (result, error, arg) => [
        { type: Tags.FLIGHT_PLAN, id: arg.flightId },
      ],
    },
  },
});

export * from "./_liberationApi";
