// Layer toolbar of the command view (WEB-01.3): the five main overlays as
// toggle buttons over the top-left of the map (shortcuts 1-5, W13), and a
// "More layers" menu with the basemaps and every other overlay. It replaces
// the expanded Leaflet layer controls in the web shell: those stay mounted but
// hidden, and remain the source of truth (the legend and the shortcuts read
// and drive them). It sits beside the map container, not inside it, so its
// clicks never reach Leaflet.
import {
  ControlLayerState,
  LAYER_SHORTCUTS,
  listLayersInControls,
  selectBaseLayerInControls,
  toggleOverlayInControls,
} from "../../maplayers/layerToggle";
import { OVERLAYS, OverlayId } from "../../maplayers/overlays";
import styles from "./LayerToolbar.module.css";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Control, Map } from "leaflet";
import { useCallback, useEffect, useState } from "react";

/** Titles of the menu groups, by index of the layer control. */
const CONTROL_GROUPS = ["Map layers", "Debug layers"];

export interface LayerToolbarProps {
  map: Map;
  /** The layer controls of the map: map layers first, then debug layers. */
  controls: () => (Control.Layers | null)[];
}

export function LayerToolbar({ map, controls }: LayerToolbarProps) {
  const [layers, setLayers] = useState<ControlLayerState[]>([]);

  const refresh = useCallback(
    () => setLayers(listLayersInControls(map, controls())),
    [map, controls],
  );

  useEffect(() => {
    refresh();
    // react-leaflet registers the overlays in their control one render after
    // adding them to the map, without any event: read them again then.
    const registered = window.setTimeout(refresh, 0);
    map.on("overlayadd overlayremove baselayerchange", refresh);
    return () => {
      window.clearTimeout(registered);
      map.off("overlayadd overlayremove baselayerchange", refresh);
    };
  }, [map, refresh]);

  const toggle = (name: string) => {
    toggleOverlayInControls(map, controls(), name);
    refresh();
  };
  const selectBase = (name: string) => {
    selectBaseLayerInControls(map, controls(), name);
    refresh();
  };
  // Until the controls are read, an overlay is in its default state.
  const isActive = (id: OverlayId) => {
    const name = OVERLAYS[id].name;
    const layer = layers.find((l) => l.overlay && l.name === name);
    return layer ? layer.active : OVERLAYS[id].checked;
  };

  const bases = layers.filter((layer) => !layer.overlay);
  const activeBase = bases.find((layer) => layer.active)?.name ?? "";

  return (
    <div className={styles.toolbar} role="toolbar" aria-label="Map layers">
      {LAYER_SHORTCUTS.map(({ key, overlay, label }) => {
        const name = OVERLAYS[overlay].name;
        return (
          <button
            key={overlay}
            type="button"
            className={styles.toggle}
            data-overlay={overlay}
            aria-pressed={isActive(overlay)}
            aria-keyshortcuts={key}
            title={`${name} (${key})`}
            onClick={() => toggle(name)}
          >
            {label}
          </button>
        );
      })}
      <DropdownMenu.Root
        modal={false}
        onOpenChange={(open) => open && refresh()}
      >
        <DropdownMenu.Trigger asChild>
          <button type="button" className={styles.toggle}>
            More layers
          </button>
        </DropdownMenu.Trigger>
        <DropdownMenu.Portal>
          <DropdownMenu.Content
            className={styles.menu}
            align="start"
            sideOffset={4}
            aria-label="More layers"
          >
            <DropdownMenu.Label className={styles.group}>
              Basemap
            </DropdownMenu.Label>
            <DropdownMenu.RadioGroup
              value={activeBase}
              onValueChange={selectBase}
            >
              {bases.map((layer) => (
                <DropdownMenu.RadioItem
                  key={layer.name}
                  value={layer.name}
                  className={styles.item}
                  // Keep the menu open to compare basemaps.
                  onSelect={(event) => event.preventDefault()}
                >
                  <span className={styles.mark} aria-hidden="true">
                    <DropdownMenu.ItemIndicator>●</DropdownMenu.ItemIndicator>
                  </span>
                  {layer.name}
                </DropdownMenu.RadioItem>
              ))}
            </DropdownMenu.RadioGroup>
            {CONTROL_GROUPS.map((title, control) => {
              const overlays = layers.filter(
                (layer) => layer.overlay && layer.control === control,
              );
              if (overlays.length === 0) {
                return null;
              }
              return (
                <DropdownMenu.Group key={title}>
                  <DropdownMenu.Separator className={styles.separator} />
                  <DropdownMenu.Label className={styles.group}>
                    {title}
                  </DropdownMenu.Label>
                  {overlays.map((layer) => (
                    <DropdownMenu.CheckboxItem
                      key={layer.name}
                      className={styles.item}
                      checked={layer.active}
                      onCheckedChange={() => toggle(layer.name)}
                      // Several layers are often toggled in a row.
                      onSelect={(event) => event.preventDefault()}
                    >
                      <span className={styles.mark} aria-hidden="true">
                        <DropdownMenu.ItemIndicator>
                          ✓
                        </DropdownMenu.ItemIndicator>
                      </span>
                      {layer.name}
                    </DropdownMenu.CheckboxItem>
                  ))}
                </DropdownMenu.Group>
              );
            })}
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
    </div>
  );
}
