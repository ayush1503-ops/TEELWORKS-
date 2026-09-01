// Tiny event bus so any "Start Camera" button can activate the scanner
// down in the Vision Lab without prop-drilling.
export const cameraBus = new EventTarget();

export function requestCameraStart() {
  cameraBus.dispatchEvent(new Event("start"));
}
