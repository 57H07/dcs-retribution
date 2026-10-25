// Decides when the online basemap is unusable and the map should fall back to
// the offline basemap (GFX-04.1).
//
// A single failed tile is not enough (a server hiccup, one missing tile at the
// edge of the world): the fallback triggers after a few consecutive failures
// with no successful tile in between, or as soon as the browser reports that
// it is offline.

export const TILE_ERROR_THRESHOLD = 3;

export class TileHealth {
  private consecutiveErrors = 0;

  constructor(private readonly threshold: number = TILE_ERROR_THRESHOLD) {}

  // Returns true when this error should trigger the fallback.
  recordError(): boolean {
    this.consecutiveErrors += 1;
    return this.consecutiveErrors >= this.threshold;
  }

  recordLoad() {
    this.consecutiveErrors = 0;
  }

  reset() {
    this.consecutiveErrors = 0;
  }
}

export function browserIsOffline(): boolean {
  return typeof navigator !== "undefined" && navigator.onLine === false;
}
