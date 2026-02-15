/**
 * Zenith — Background service worker.
 *
 * Toggles the sidebar when the toolbar button or keybind (Ctrl+Space) fires.
 * In MV3, "browserAction" is replaced by "action".
 */
declare const browser: {
  action: { onClicked: { addListener(cb: () => void): void } };
  sidebarAction: { toggle(): void };
};

browser.action.onClicked.addListener(() => {
  browser.sidebarAction.toggle();
});
