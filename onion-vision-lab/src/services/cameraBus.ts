/** Tiny event bus: any "Launch Camera" button can activate the live scanner
 *  inside the Vision Lab section without prop-drilling (same pattern as the
 *  previous ONION LAB project). */
export const cameraBus = new EventTarget();

export function requestCameraStart(): void {
  cameraBus.dispatchEvent(new Event('start'));
}
