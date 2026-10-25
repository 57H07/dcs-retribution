// jsdom lacks SVGSVGElement.createSVGRect, so Leaflet decides SVG is not
// supported and cannot draw vector layers. Import this module before leaflet
// in tests that add paths (polygons, polylines) to a real map.
const proto = window.SVGSVGElement?.prototype as any;
if (proto && !proto.createSVGRect) {
  proto.createSVGRect = () => ({ x: 0, y: 0, width: 0, height: 0 });
}

export {};
