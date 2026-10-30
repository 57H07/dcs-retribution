import { baseApi as api } from "./baseApi";
const injectedRtkApi = api.injectEndpoints({
  endpoints: (build) => ({
    listControlPoints: build.query<
      ListControlPointsApiResponse,
      ListControlPointsApiArg
    >({
      query: () => ({ url: `/control-points/` }),
    }),
    getControlPointById: build.query<
      GetControlPointByIdApiResponse,
      GetControlPointByIdApiArg
    >({
      query: (queryArg) => ({ url: `/control-points/${queryArg.cpId}` }),
    }),
    controlPointDestinationInRange: build.query<
      ControlPointDestinationInRangeApiResponse,
      ControlPointDestinationInRangeApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/destination-in-range`,
        params: { lat: queryArg.lat, lng: queryArg.lng },
      }),
    }),
    setControlPointDestination: build.mutation<
      SetControlPointDestinationApiResponse,
      SetControlPointDestinationApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/destination`,
        method: "PUT",
        body: queryArg.leafletPoint,
      }),
    }),
    clearControlPointDestination: build.mutation<
      ClearControlPointDestinationApiResponse,
      ClearControlPointDestinationApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/cancel-travel`,
        method: "PUT",
      }),
    }),
    getDebugHoldZones: build.query<
      GetDebugHoldZonesApiResponse,
      GetDebugHoldZonesApiArg
    >({
      query: (queryArg) => ({
        url: `/debug/waypoint-geometries/hold/${queryArg.flightId}`,
      }),
    }),
    getDebugJoinZones: build.query<
      GetDebugJoinZonesApiResponse,
      GetDebugJoinZonesApiArg
    >({
      query: (queryArg) => ({
        url: `/debug/waypoint-geometries/join/${queryArg.flightId}`,
      }),
    }),
    listDownedPilots: build.query<
      ListDownedPilotsApiResponse,
      ListDownedPilotsApiArg
    >({
      query: () => ({ url: `/downed-pilots/` }),
    }),
    getDownedPilotById: build.query<
      GetDownedPilotByIdApiResponse,
      GetDownedPilotByIdApiArg
    >({
      query: (queryArg) => ({ url: `/downed-pilots/${queryArg.pilotId}` }),
    }),
    listFlights: build.query<ListFlightsApiResponse, ListFlightsApiArg>({
      query: (queryArg) => ({
        url: `/flights/`,
        params: { with_waypoints: queryArg.withWaypoints },
      }),
    }),
    getFlightById: build.query<GetFlightByIdApiResponse, GetFlightByIdApiArg>({
      query: (queryArg) => ({
        url: `/flights/${queryArg.flightId}`,
        params: { with_waypoints: queryArg.withWaypoints },
      }),
    }),
    getCommitBoundaryForFlight: build.query<
      GetCommitBoundaryForFlightApiResponse,
      GetCommitBoundaryForFlightApiArg
    >({
      query: (queryArg) => ({
        url: `/flights/${queryArg.flightId}/commit-boundary`,
      }),
    }),
    listFrontLines: build.query<
      ListFrontLinesApiResponse,
      ListFrontLinesApiArg
    >({
      query: () => ({ url: `/front-lines/` }),
    }),
    getFrontLineById: build.query<
      GetFrontLineByIdApiResponse,
      GetFrontLineByIdApiArg
    >({
      query: (queryArg) => ({ url: `/front-lines/${queryArg.frontLineId}` }),
    }),
    getGameState: build.query<GetGameStateApiResponse, GetGameStateApiArg>({
      query: () => ({ url: `/game/` }),
    }),
    getTopBar: build.query<GetTopBarApiResponse, GetTopBarApiArg>({
      query: () => ({ url: `/game/top-bar` }),
    }),
    getTimeline: build.query<GetTimelineApiResponse, GetTimelineApiArg>({
      query: () => ({ url: `/game/timeline` }),
    }),
    passTurn: build.mutation<PassTurnApiResponse, PassTurnApiArg>({
      query: () => ({ url: `/game/turn/pass`, method: "POST" }),
    }),
    getMissionChecks: build.query<
      GetMissionChecksApiResponse,
      GetMissionChecksApiArg
    >({
      query: () => ({ url: `/game/mission/checks` }),
    }),
    fixTots: build.mutation<FixTotsApiResponse, FixTotsApiArg>({
      query: () => ({ url: `/game/mission/fix-tots`, method: "POST" }),
    }),
    generateMission: build.mutation<
      GenerateMissionApiResponse,
      GenerateMissionApiArg
    >({
      query: () => ({ url: `/game/mission`, method: "POST" }),
    }),
    setSimSpeed: build.mutation<SetSimSpeedApiResponse, SetSimSpeedApiArg>({
      query: (queryArg) => ({
        url: `/game/sim/speed`,
        method: "PUT",
        body: queryArg.simSpeedChangeJs,
      }),
    }),
    getSettings: build.query<GetSettingsApiResponse, GetSettingsApiArg>({
      query: () => ({ url: `/settings/` }),
    }),
    setSetting: build.mutation<SetSettingApiResponse, SetSettingApiArg>({
      query: (queryArg) => ({
        url: `/settings/values/${queryArg.key}`,
        method: "PUT",
        body: queryArg.settingValueUpdateJs,
      }),
    }),
    resetSettingsPage: build.mutation<
      ResetSettingsPageApiResponse,
      ResetSettingsPageApiArg
    >({
      query: (queryArg) => ({
        url: `/settings/pages/${queryArg.pageId}/reset`,
        method: "POST",
      }),
    }),
    getTerrainZones: build.query<
      GetTerrainZonesApiResponse,
      GetTerrainZonesApiArg
    >({
      query: () => ({ url: `/map-zones/terrain` }),
    }),
    getOfflineBasemapImage: build.query<
      GetOfflineBasemapImageApiResponse,
      GetOfflineBasemapImageApiArg
    >({
      query: (queryArg) => ({
        url: `/map-zones/offline-basemap`,
        params: {
          sea: queryArg.sea,
          land: queryArg.land,
          land_excluded: queryArg.landExcluded,
          coastline: queryArg.coastline,
        },
      }),
    }),
    listUnculledZones: build.query<
      ListUnculledZonesApiResponse,
      ListUnculledZonesApiArg
    >({
      query: () => ({ url: `/map-zones/unculled` }),
    }),
    getThreatZones: build.query<
      GetThreatZonesApiResponse,
      GetThreatZonesApiArg
    >({
      query: () => ({ url: `/map-zones/threats` }),
    }),
    getMissionResult: build.query<
      GetMissionResultApiResponse,
      GetMissionResultApiArg
    >({
      query: () => ({ url: `/game/mission/result` }),
    }),
    loadMissionResultFile: build.mutation<
      LoadMissionResultFileApiResponse,
      LoadMissionResultFileApiArg
    >({
      query: () => ({ url: `/game/mission/result/file`, method: "POST" }),
    }),
    abortMission: build.mutation<AbortMissionApiResponse, AbortMissionApiArg>({
      query: () => ({ url: `/game/mission/result/cancel`, method: "POST" }),
    }),
    acceptMissionResult: build.mutation<
      AcceptMissionResultApiResponse,
      AcceptMissionResultApiArg
    >({
      query: () => ({ url: `/game/mission/result/accept`, method: "POST" }),
    }),
    saveGame: build.mutation<SaveGameApiResponse, SaveGameApiArg>({
      query: () => ({ url: `/native/save`, method: "POST" }),
    }),
    saveGameAs: build.mutation<SaveGameAsApiResponse, SaveGameAsApiArg>({
      query: () => ({ url: `/native/save-as`, method: "POST" }),
    }),
    openGame: build.mutation<OpenGameApiResponse, OpenGameApiArg>({
      query: () => ({ url: `/native/open`, method: "POST" }),
    }),
    pickFolder: build.mutation<PickFolderApiResponse, PickFolderApiArg>({
      query: (queryArg) => ({
        url: `/native/pick-folder`,
        method: "POST",
        body: queryArg.folderPickRequestJs,
      }),
    }),
    openNewGameWizard: build.mutation<
      OpenNewGameWizardApiResponse,
      OpenNewGameWizardApiArg
    >({
      query: () => ({ url: `/native/new-game`, method: "POST" }),
    }),
    openNativeFolder: build.mutation<
      OpenNativeFolderApiResponse,
      OpenNativeFolderApiArg
    >({
      query: (queryArg) => ({
        url: `/native/open-folder/${queryArg.folder}`,
        method: "POST",
      }),
    }),
    openExternalLink: build.mutation<
      OpenExternalLinkApiResponse,
      OpenExternalLinkApiArg
    >({
      query: (queryArg) => ({
        url: `/native/open-link/${queryArg.link}`,
        method: "POST",
      }),
    }),
    quitApplication: build.mutation<
      QuitApplicationApiResponse,
      QuitApplicationApiArg
    >({
      query: () => ({ url: `/native/quit`, method: "POST" }),
    }),
    getNavmesh: build.query<GetNavmeshApiResponse, GetNavmeshApiArg>({
      query: (queryArg) => ({
        url: `/navmesh/`,
        params: { for_player: queryArg.forPlayer },
      }),
    }),
    listPackages: build.query<ListPackagesApiResponse, ListPackagesApiArg>({
      query: () => ({ url: `/packages/` }),
    }),
    createPackage: build.mutation<
      CreatePackageApiResponse,
      CreatePackageApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/`,
        method: "POST",
        body: queryArg.newPackageJs,
      }),
    }),
    deletePackage: build.mutation<
      DeletePackageApiResponse,
      DeletePackageApiArg
    >({
      query: (queryArg) => ({
        url: `/packages/${queryArg.packageId}`,
        method: "DELETE",
      }),
    }),
    getInstallPreferences: build.query<
      GetInstallPreferencesApiResponse,
      GetInstallPreferencesApiArg
    >({
      query: () => ({ url: `/preferences/` }),
    }),
    setInstallPreferences: build.mutation<
      SetInstallPreferencesApiResponse,
      SetInstallPreferencesApiArg
    >({
      query: (queryArg) => ({
        url: `/preferences/`,
        method: "PUT",
        body: queryArg.installPreferencesUpdateJs,
      }),
    }),
    openNewFrontLinePackageDialog: build.mutation<
      OpenNewFrontLinePackageDialogApiResponse,
      OpenNewFrontLinePackageDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/create-package/front-line/${queryArg.frontLineId}`,
        method: "POST",
      }),
    }),
    openNewTgoPackageDialog: build.mutation<
      OpenNewTgoPackageDialogApiResponse,
      OpenNewTgoPackageDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/create-package/tgo/${queryArg.tgoId}`,
        method: "POST",
      }),
    }),
    openTgoInfoDialog: build.mutation<
      OpenTgoInfoDialogApiResponse,
      OpenTgoInfoDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/info/tgo/${queryArg.tgoId}`,
        method: "POST",
      }),
    }),
    openNewControlPointPackageDialog: build.mutation<
      OpenNewControlPointPackageDialogApiResponse,
      OpenNewControlPointPackageDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/create-package/control-point/${queryArg.cpId}`,
        method: "POST",
      }),
    }),
    openNewDownedPilotPackageDialog: build.mutation<
      OpenNewDownedPilotPackageDialogApiResponse,
      OpenNewDownedPilotPackageDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/create-package/downed-pilot/${queryArg.pilotId}`,
        method: "POST",
      }),
    }),
    selectFlight: build.mutation<SelectFlightApiResponse, SelectFlightApiArg>({
      query: (queryArg) => ({
        url: `/qt/select-flight/${queryArg.flightId}`,
        method: "POST",
      }),
    }),
    openControlPointInfoDialog: build.mutation<
      OpenControlPointInfoDialogApiResponse,
      OpenControlPointInfoDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/info/control-point/${queryArg.cpId}`,
        method: "POST",
      }),
    }),
    openQtDialog: build.mutation<OpenQtDialogApiResponse, OpenQtDialogApiArg>({
      query: (queryArg) => ({
        url: `/qt/dialogs/${queryArg.dialog}`,
        method: "POST",
      }),
    }),
    openEditPackageDialog: build.mutation<
      OpenEditPackageDialogApiResponse,
      OpenEditPackageDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/edit-package/flight/${queryArg.flightId}`,
        method: "POST",
      }),
    }),
    listSupplyRoutes: build.query<
      ListSupplyRoutesApiResponse,
      ListSupplyRoutesApiArg
    >({
      query: () => ({ url: `/supply-routes/` }),
    }),
    listTgos: build.query<ListTgosApiResponse, ListTgosApiArg>({
      query: () => ({ url: `/tgos/` }),
    }),
    getTgoById: build.query<GetTgoByIdApiResponse, GetTgoByIdApiArg>({
      query: (queryArg) => ({ url: `/tgos/${queryArg.tgoId}` }),
    }),
    tgoDestinationInRange: build.query<
      TgoDestinationInRangeApiResponse,
      TgoDestinationInRangeApiArg
    >({
      query: (queryArg) => ({
        url: `/tgos/${queryArg.tgoId}/destination-in-range`,
        params: { lat: queryArg.lat, lng: queryArg.lng },
      }),
    }),
    setTgoDestination: build.mutation<
      SetTgoDestinationApiResponse,
      SetTgoDestinationApiArg
    >({
      query: (queryArg) => ({
        url: `/tgos/${queryArg.tgoId}/destination`,
        method: "PUT",
        body: queryArg.leafletPoint,
      }),
    }),
    clearTgoDestination: build.mutation<
      ClearTgoDestinationApiResponse,
      ClearTgoDestinationApiArg
    >({
      query: (queryArg) => ({
        url: `/tgos/${queryArg.tgoId}/cancel-travel`,
        method: "PUT",
      }),
    }),
    listAllWaypointsForFlight: build.query<
      ListAllWaypointsForFlightApiResponse,
      ListAllWaypointsForFlightApiArg
    >({
      query: (queryArg) => ({ url: `/waypoints/${queryArg.flightId}` }),
    }),
    setWaypointPosition: build.mutation<
      SetWaypointPositionApiResponse,
      SetWaypointPositionApiArg
    >({
      query: (queryArg) => ({
        url: `/waypoints/${queryArg.flightId}/${queryArg.waypointIdx}/position`,
        method: "POST",
        body: queryArg.leafletPoint,
      }),
    }),
    getIadsNetwork: build.query<
      GetIadsNetworkApiResponse,
      GetIadsNetworkApiArg
    >({
      query: () => ({ url: `/iads-network/` }),
    }),
    getIadsConnectionsForTgo: build.query<
      GetIadsConnectionsForTgoApiResponse,
      GetIadsConnectionsForTgoApiArg
    >({
      query: (queryArg) => ({ url: `/iads-network/for-tgo/${queryArg.tgoId}` }),
    }),
  }),
  overrideExisting: false,
});
export { injectedRtkApi as _liberationApi };
export type ListControlPointsApiResponse =
  /** status 200 Successful Response */ ControlPoint[];
export type ListControlPointsApiArg = void;
export type GetControlPointByIdApiResponse =
  /** status 200 Successful Response */ ControlPoint;
export type GetControlPointByIdApiArg = {
  cpId: string;
};
export type ControlPointDestinationInRangeApiResponse =
  /** status 200 Successful Response */ boolean;
export type ControlPointDestinationInRangeApiArg = {
  cpId: string;
  lat: number;
  lng: number;
};
export type SetControlPointDestinationApiResponse =
  /** status 204 Successful Response */ void;
export type SetControlPointDestinationApiArg = {
  cpId: string;
  leafletPoint: LatLng;
};
export type ClearControlPointDestinationApiResponse =
  /** status 204 Successful Response */ void;
export type ClearControlPointDestinationApiArg = {
  cpId: string;
};
export type GetDebugHoldZonesApiResponse =
  /** status 200 Successful Response */ HoldZones;
export type GetDebugHoldZonesApiArg = {
  flightId: string;
};
export type GetDebugJoinZonesApiResponse =
  /** status 200 Successful Response */ JoinZones;
export type GetDebugJoinZonesApiArg = {
  flightId: string;
};
export type ListDownedPilotsApiResponse =
  /** status 200 Successful Response */ DownedPilot[];
export type ListDownedPilotsApiArg = void;
export type GetDownedPilotByIdApiResponse =
  /** status 200 Successful Response */ DownedPilot;
export type GetDownedPilotByIdApiArg = {
  pilotId: string;
};
export type ListFlightsApiResponse =
  /** status 200 Successful Response */ Flight[];
export type ListFlightsApiArg = {
  withWaypoints?: boolean;
};
export type GetFlightByIdApiResponse =
  /** status 200 Successful Response */ Flight;
export type GetFlightByIdApiArg = {
  flightId: string;
  withWaypoints?: boolean;
};
export type GetCommitBoundaryForFlightApiResponse =
  /** status 200 Successful Response */ LatLng[][];
export type GetCommitBoundaryForFlightApiArg = {
  flightId: string;
};
export type ListFrontLinesApiResponse =
  /** status 200 Successful Response */ FrontLine[];
export type ListFrontLinesApiArg = void;
export type GetFrontLineByIdApiResponse =
  /** status 200 Successful Response */ FrontLine;
export type GetFrontLineByIdApiArg = {
  frontLineId: string;
};
export type GetGameStateApiResponse =
  /** status 200 Successful Response */ Game;
export type GetGameStateApiArg = void;
export type GetTopBarApiResponse =
  /** status 200 Successful Response */ TopBar | null;
export type GetTopBarApiArg = void;
export type GetTimelineApiResponse =
  /** status 200 Successful Response */ Timeline | null;
export type GetTimelineApiArg = void;
export type PassTurnApiResponse = /** status 200 Successful Response */ Turn;
export type PassTurnApiArg = void;
export type GetMissionChecksApiResponse =
  /** status 200 Successful Response */ MissionChecks;
export type GetMissionChecksApiArg = void;
export type FixTotsApiResponse =
  /** status 200 Successful Response */ FixedTots;
export type FixTotsApiArg = void;
export type GenerateMissionApiResponse =
  /** status 200 Successful Response */ Mission;
export type GenerateMissionApiArg = void;
export type SetSimSpeedApiResponse = /** status 200 Successful Response */ Sim;
export type SetSimSpeedApiArg = {
  simSpeedChangeJs: SimSpeedChange;
};
export type GetSettingsApiResponse =
  /** status 200 Successful Response */ Settings;
export type GetSettingsApiArg = void;
export type SetSettingApiResponse =
  /** status 200 Successful Response */ Setting;
export type SetSettingApiArg = {
  key: string;
  settingValueUpdateJs: SettingValueUpdate;
};
export type ResetSettingsPageApiResponse =
  /** status 200 Successful Response */ SettingsPage;
export type ResetSettingsPageApiArg = {
  pageId: string;
};
export type GetTerrainZonesApiResponse =
  /** status 200 Successful Response */ MapZones;
export type GetTerrainZonesApiArg = void;
export type GetOfflineBasemapImageApiResponse =
  /** status 200 Successful Response */ Blob;
export type GetOfflineBasemapImageApiArg = {
  sea?: string;
  land?: string;
  landExcluded?: string;
  coastline?: string;
};
export type ListUnculledZonesApiResponse =
  /** status 200 Successful Response */ UnculledZone[];
export type ListUnculledZonesApiArg = void;
export type GetThreatZonesApiResponse =
  /** status 200 Successful Response */ ThreatZoneContainer;
export type GetThreatZonesApiArg = void;
export type GetMissionResultApiResponse =
  /** status 200 Successful Response */ MissionResult;
export type GetMissionResultApiArg = void;
export type LoadMissionResultFileApiResponse =
  /** status 200 Successful Response */ MissionResult;
export type LoadMissionResultFileApiArg = void;
export type AbortMissionApiResponse =
  /** status 204 Successful Response */ void;
export type AbortMissionApiArg = void;
export type AcceptMissionResultApiResponse =
  /** status 200 Successful Response */ Turn;
export type AcceptMissionResultApiArg = void;
export type SaveGameApiResponse =
  /** status 200 Successful Response */ FileActionResult;
export type SaveGameApiArg = void;
export type SaveGameAsApiResponse =
  /** status 200 Successful Response */ FileActionResult;
export type SaveGameAsApiArg = void;
export type OpenGameApiResponse =
  /** status 200 Successful Response */ FileActionResult;
export type OpenGameApiArg = void;
export type PickFolderApiResponse =
  /** status 200 Successful Response */ FolderPickResult;
export type PickFolderApiArg = {
  folderPickRequestJs: FolderPickRequest;
};
export type OpenNewGameWizardApiResponse = unknown;
export type OpenNewGameWizardApiArg = void;
export type OpenNativeFolderApiResponse =
  /** status 204 Successful Response */ void;
export type OpenNativeFolderApiArg = {
  folder: NativeFolder;
};
export type OpenExternalLinkApiResponse =
  /** status 204 Successful Response */ void;
export type OpenExternalLinkApiArg = {
  link: ExternalLink;
};
export type QuitApplicationApiResponse = unknown;
export type QuitApplicationApiArg = void;
export type GetNavmeshApiResponse =
  /** status 200 Successful Response */ NavMesh;
export type GetNavmeshApiArg = {
  forPlayer: Player;
};
export type ListPackagesApiResponse =
  /** status 200 Successful Response */ Package[];
export type ListPackagesApiArg = void;
export type CreatePackageApiResponse =
  /** status 204 Successful Response */ void;
export type CreatePackageApiArg = {
  newPackageJs: NewPackage;
};
export type DeletePackageApiResponse =
  /** status 204 Successful Response */ void;
export type DeletePackageApiArg = {
  packageId: string;
};
export type GetInstallPreferencesApiResponse =
  /** status 200 Successful Response */ InstallPreferencesState;
export type GetInstallPreferencesApiArg = void;
export type SetInstallPreferencesApiResponse =
  /** status 200 Successful Response */ InstallPreferencesState;
export type SetInstallPreferencesApiArg = {
  installPreferencesUpdateJs: InstallPreferencesUpdate;
};
export type OpenNewFrontLinePackageDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenNewFrontLinePackageDialogApiArg = {
  frontLineId: string;
};
export type OpenNewTgoPackageDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenNewTgoPackageDialogApiArg = {
  tgoId: string;
};
export type OpenTgoInfoDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenTgoInfoDialogApiArg = {
  tgoId: string;
};
export type OpenNewControlPointPackageDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenNewControlPointPackageDialogApiArg = {
  cpId: string;
};
export type OpenNewDownedPilotPackageDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenNewDownedPilotPackageDialogApiArg = {
  pilotId: string;
};
export type SelectFlightApiResponse = /** status 200 Successful Response */ any;
export type SelectFlightApiArg = {
  flightId: string;
};
export type OpenControlPointInfoDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenControlPointInfoDialogApiArg = {
  cpId: string;
};
export type OpenQtDialogApiResponse =
  /** status 204 Successful Response */ void;
export type OpenQtDialogApiArg = {
  dialog: QtDialog;
};
export type OpenEditPackageDialogApiResponse =
  /** status 204 Successful Response */ void;
export type OpenEditPackageDialogApiArg = {
  flightId: string;
};
export type ListSupplyRoutesApiResponse =
  /** status 200 Successful Response */ SupplyRoute[];
export type ListSupplyRoutesApiArg = void;
export type ListTgosApiResponse = /** status 200 Successful Response */ Tgo[];
export type ListTgosApiArg = void;
export type GetTgoByIdApiResponse = /** status 200 Successful Response */ Tgo;
export type GetTgoByIdApiArg = {
  tgoId: string;
};
export type TgoDestinationInRangeApiResponse =
  /** status 200 Successful Response */ boolean;
export type TgoDestinationInRangeApiArg = {
  tgoId: string;
  lat: number;
  lng: number;
};
export type SetTgoDestinationApiResponse =
  /** status 204 Successful Response */ void;
export type SetTgoDestinationApiArg = {
  tgoId: string;
  leafletPoint: LatLng;
};
export type ClearTgoDestinationApiResponse =
  /** status 204 Successful Response */ void;
export type ClearTgoDestinationApiArg = {
  tgoId: string;
};
export type ListAllWaypointsForFlightApiResponse =
  /** status 200 Successful Response */ Waypoint[];
export type ListAllWaypointsForFlightApiArg = {
  flightId: string;
};
export type SetWaypointPositionApiResponse =
  /** status 204 Successful Response */ void;
export type SetWaypointPositionApiArg = {
  flightId: string;
  waypointIdx: number;
  leafletPoint: LatLng;
};
export type GetIadsNetworkApiResponse =
  /** status 200 Successful Response */ IadsNetwork;
export type GetIadsNetworkApiArg = void;
export type GetIadsConnectionsForTgoApiResponse =
  /** status 200 Successful Response */ IadsConnection[];
export type GetIadsConnectionsForTgoApiArg = {
  tgoId: string;
};
export type LatLng = {
  lat: number;
  lng: number;
};
export type ControlPoint = {
  id: string;
  name: string;
  blue: boolean;
  position: LatLng;
  mobile: boolean;
  destination?: LatLng;
  sidc: string;
  cut_off?: boolean;
};
export type ValidationError = {
  loc: (string | number)[];
  msg: string;
  type: string;
};
export type HttpValidationError = {
  detail?: ValidationError[];
};
export type HoldZones = {
  homeBubble: LatLng[][];
  targetBubble: LatLng[][];
  joinBubble: LatLng[][];
  excludedZones: LatLng[][][];
  permissibleZones: LatLng[][][];
  preferredLines: LatLng[][];
};
export type JoinZones = {
  homeBubble: LatLng[][];
  targetBubble: LatLng[][];
  ipBubble: LatLng[][];
  excludedZones: LatLng[][][];
  permissibleZones: LatLng[][][];
  preferredLines: LatLng[][];
};
export type DownedPilot = {
  id: string;
  name: string;
  squadron: string;
  aircraft: string;
  blue: boolean;
  position: LatLng;
  turns_remaining: number;
  sidc: string;
};
export type Waypoint = {
  name: string;
  position: LatLng;
  altitude_ft: number;
  altitude_reference: string;
  is_movable: boolean;
  should_mark: boolean;
  include_in_path: boolean;
  timing: string;
};
export type Flight = {
  id: string;
  blue: boolean;
  position?: LatLng;
  sidc: string;
  waypoints?: Waypoint[];
};
export type FrontLine = {
  id: string;
  extents: LatLng[];
};
export type Tgo = {
  id: string;
  name: string;
  control_point_name: string;
  category: string;
  blue: boolean;
  position: LatLng;
  units: string[];
  threat_ranges: number[];
  detection_ranges: number[];
  dead: boolean;
  sidc: string;
  task?: string[];
  mobile: boolean;
  destination?: LatLng;
};
export type SupplyRoute = {
  id: string;
  points: LatLng[];
  front_active: boolean;
  is_sea: boolean;
  blue: boolean;
  active_transports: string[];
};
export type IadsConnection = {
  id: string;
  points: LatLng[];
  node: string;
  connected: string;
  active: boolean;
  blue: boolean;
  is_power: boolean;
};
export type IadsNetwork = {
  advanced: boolean;
  connections: IadsConnection[];
};
export type ThreatZones = {
  full: LatLng[][][];
  aircraft: LatLng[][][];
  air_defenses: LatLng[][][];
  radar_sams: LatLng[][][];
};
export type ThreatZoneContainer = {
  blue: ThreatZones;
  red: ThreatZones;
};
export type NavMeshPoly = {
  poly: LatLng[][];
  threatened: boolean;
};
export type NavMesh = {
  polys: NavMeshPoly[];
};
export type NavMeshes = {
  blue: NavMesh;
  red: NavMesh;
};
export type UnculledZone = {
  position: LatLng;
  radius: number;
};
export type OfflineBasemapImage = {
  south_west: LatLng;
  north_east: LatLng;
};
export type MapZones = {
  inclusion: LatLng[][][];
  exclusion: LatLng[][][];
  sea: LatLng[][][];
  offline_image?: OfflineBasemapImage | null;
};
export type Game = {
  control_points: ControlPoint[];
  tgos: Tgo[];
  downed_pilots: DownedPilot[];
  supply_routes: SupplyRoute[];
  front_lines: FrontLine[];
  flights: Flight[];
  iads_network: IadsNetwork;
  threat_zones: ThreatZoneContainer;
  navmeshes: NavMeshes;
  map_center?: LatLng;
  unculled_zones: UnculledZone[];
  map_zones: MapZones;
};
export type Wind = {
  altitude: string;
  direction: number;
  speed_kt: number;
};
export type Weather = {
  clouds: string;
  precipitation: string;
  fog: string;
  cloud_base_m?: number;
  cloud_base_ft?: number;
  winds: Wind[];
};
export type ForceBalance = {
  friendly: number;
  enemy: number;
  assessment: string;
};
export type SimSpeedJs =
  | "paused"
  | "1x"
  | "2x"
  | "5x"
  | "10x"
  | "100x"
  | "1000x";
export type Sim = {
  speed: SimSpeedJs;
  time?: string;
};
export type TopBar = {
  campaign_name?: string;
  theater: string;
  player_faction: string;
  enemy_faction: string;
  turn: number;
  mission_start_date: string;
  mission_start_time: string;
  time_of_day: string;
  weather: Weather;
  budget: number;
  income: number;
  air: ForceBalance;
  ground: ForceBalance;
  economy: string;
  max_player_count: number;
  sim: Sim;
  show_sim_speed_controls: boolean;
};
export type TimelinePackage = {
  id: string;
  task: string;
  target: string;
  startup: number;
  tot: number;
  landing: number;
  flight_ids: string[];
};
export type Timeline = {
  start_time: string;
  packages: TimelinePackage[];
};
export type CampaignStateJs = "continue" | "win" | "loss";
export type Turn = {
  turn: number;
  campaign_state: CampaignStateJs;
};
export type CommandError = {
  detail: string;
};
export type MissionChecks = {
  has_player_pilots: boolean;
  flights_missing_pilots: string[];
  packages_starting_in_the_past: string[];
  max_player_count: number;
};
export type FixedTots = {
  packages: string[];
};
export type Mission = {
  path: string;
};
export type SimSpeedChange = {
  speed: SimSpeedJs;
};
export type SettingKindJs = "bool" | "choice" | "int" | "float" | "minutes";
export type Setting = {
  key: string;
  label: string;
  detail?: string;
  tooltip?: string;
  kind: SettingKindJs;
  value: boolean | number | number | string;
  default: boolean | number | number | string;
  modified: boolean;
  min?: number;
  max?: number;
  step?: number;
  choices?: string[];
};
export type SettingsSection = {
  name: string;
  description?: string;
  settings: Setting[];
};
export type SettingsPage = {
  id: string;
  name: string;
  sections: SettingsSection[];
};
export type Settings = {
  pages: SettingsPage[];
};
export type SettingValueUpdate = {
  value: boolean | number | number | string;
};
export type MissionResultStatusJs = "idle" | "waiting" | "detected" | "error";
export type LossRow = {
  label: string;
  blue: number;
  red: number;
};
export type MissionResult = {
  status: MissionResultStatusJs;
  miz_path?: string;
  state_path: string;
  mission_ended: boolean;
  error?: string;
  player_country?: string;
  enemy_country?: string;
  losses: LossRow[];
};
export type FileOutcome = "saved" | "opened" | "cancelled";
export type FileActionResult = {
  outcome: FileOutcome;
  path?: string;
};
export type FolderPickResult = {
  path?: string;
};
export type FolderPurpose = "saved-games" | "dcs-install";
export type FolderPickRequest = {
  purpose: FolderPurpose;
  start?: string;
};
export type NativeFolder = "saves" | "missions";
export type ExternalLink =
  | "discord"
  | "github"
  | "ukraine"
  | "pretense-discord"
  | "releases"
  | "manual"
  | "forum-thread"
  | "issues";
export type Player = "Neutral" | "Blue" | "Red";
export type PackageFlight = {
  id: string;
  task: string;
  aircraft: string;
  count: number;
  clients: number;
  missing_pilots: number;
  squadron: string;
  departure: string;
  custom_name?: string;
};
export type Package = {
  id: string;
  blue: boolean;
  task?: string;
  description: string;
  custom_name?: string;
  target: string;
  tot?: string;
  auto_asap: boolean;
  flights: PackageFlight[];
  missing_pilots: number;
};
export type PackageTargetKind =
  | "control-point"
  | "tgo"
  | "front-line"
  | "downed-pilot";
export type NewPackage = {
  target_kind: PackageTargetKind;
  target_id: string;
};
export type InstallPreferences = {
  saved_game_dir: string;
  dcs_install_dir: string;
  prefer_liberation_payloads: boolean;
  setup_preferences_on_every_start: boolean;
  server_port: number;
  web_ui: boolean;
};
export type InstallPreferencesState = {
  preferences: InstallPreferences;
  first_start: boolean;
  saved_game_dir_problem?: string;
  dcs_install_dir_problem?: string;
  warning?: string | null;
};
export type InstallPreferencesUpdate = {
  saved_game_dir: string;
  dcs_install_dir: string;
  prefer_liberation_payloads: boolean;
  setup_preferences_on_every_start: boolean;
  server_port: number;
  web_ui: boolean;
  allow_empty_install_dir?: boolean;
};
export type QtDialog =
  | "stats"
  | "notes"
  | "logs"
  | "about"
  | "import-layouts"
  | "pretense-campaign"
  | "air-wing"
  | "transfers"
  | "reports"
  | "finances"
  | "intel"
  | "debriefing";
export const {
  useListControlPointsQuery,
  useGetControlPointByIdQuery,
  useControlPointDestinationInRangeQuery,
  useSetControlPointDestinationMutation,
  useClearControlPointDestinationMutation,
  useGetDebugHoldZonesQuery,
  useGetDebugJoinZonesQuery,
  useListDownedPilotsQuery,
  useGetDownedPilotByIdQuery,
  useListFlightsQuery,
  useGetFlightByIdQuery,
  useGetCommitBoundaryForFlightQuery,
  useListFrontLinesQuery,
  useGetFrontLineByIdQuery,
  useGetGameStateQuery,
  useGetTopBarQuery,
  useGetTimelineQuery,
  usePassTurnMutation,
  useGetMissionChecksQuery,
  useFixTotsMutation,
  useGenerateMissionMutation,
  useSetSimSpeedMutation,
  useGetSettingsQuery,
  useSetSettingMutation,
  useResetSettingsPageMutation,
  useGetTerrainZonesQuery,
  useGetOfflineBasemapImageQuery,
  useListUnculledZonesQuery,
  useGetThreatZonesQuery,
  useGetMissionResultQuery,
  useLoadMissionResultFileMutation,
  useAbortMissionMutation,
  useAcceptMissionResultMutation,
  useSaveGameMutation,
  useSaveGameAsMutation,
  useOpenGameMutation,
  usePickFolderMutation,
  useOpenNewGameWizardMutation,
  useOpenNativeFolderMutation,
  useOpenExternalLinkMutation,
  useQuitApplicationMutation,
  useGetNavmeshQuery,
  useListPackagesQuery,
  useCreatePackageMutation,
  useDeletePackageMutation,
  useGetInstallPreferencesQuery,
  useSetInstallPreferencesMutation,
  useOpenNewFrontLinePackageDialogMutation,
  useOpenNewTgoPackageDialogMutation,
  useOpenTgoInfoDialogMutation,
  useOpenNewControlPointPackageDialogMutation,
  useOpenNewDownedPilotPackageDialogMutation,
  useSelectFlightMutation,
  useOpenControlPointInfoDialogMutation,
  useOpenQtDialogMutation,
  useOpenEditPackageDialogMutation,
  useListSupplyRoutesQuery,
  useListTgosQuery,
  useGetTgoByIdQuery,
  useTgoDestinationInRangeQuery,
  useSetTgoDestinationMutation,
  useClearTgoDestinationMutation,
  useListAllWaypointsForFlightQuery,
  useSetWaypointPositionMutation,
  useGetIadsNetworkQuery,
  useGetIadsConnectionsForTgoQuery,
} = injectedRtkApi;
