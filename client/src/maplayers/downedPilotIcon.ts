// A parachute-and-survivor glyph drawn inline rather than via milsymbol: the
// APP-6 dismounted-individual symbol set isn't rendered distinctly by milsymbol,
// and a downed pilot needs to be obvious at a glance on a busy map. Shared by the
// downed pilots layer and the legend.
export function downedPilotIconSvg(blue: boolean): string {
  const fill = blue ? "#4a90d9" : "#d94a4a";
  return `
<svg xmlns="http://www.w3.org/2000/svg" width="30" height="34" viewBox="0 0 30 34">
  <g fill="none" stroke="#000" stroke-width="3" stroke-linejoin="round">
    <path d="M3 12a12 12 0 0 1 24 0z" fill="${fill}"/>
    <path d="M3 12l12 9M27 12l-12 9M11 12l4 9M19 12l-4 9"/>
    <circle cx="15" cy="26" r="4" fill="${fill}"/>
  </g>
  <g fill="none" stroke="${fill}" stroke-width="1.5" stroke-linejoin="round">
    <path d="M3 12a12 12 0 0 1 24 0z" fill="${fill}"/>
    <path d="M3 12l12 9M27 12l-12 9M11 12l4 9M19 12l-4 9"/>
  </g>
  <circle cx="15" cy="26" r="4" fill="${fill}" stroke="#fff" stroke-width="1.5"/>
</svg>`.trim();
}

export function downedPilotIconDataUrl(blue: boolean): string {
  return `data:image/svg+xml;base64,${window.btoa(downedPilotIconSvg(blue))}`;
}
