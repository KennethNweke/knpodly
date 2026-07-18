/**
 * @novnc/novnc has no official TypeScript definitions. This is a minimal
 * ambient declaration covering only the RFB API surface NoVNCViewer.tsx
 * actually uses — extend it if you use more of the client (e.g.
 * clipboard sync, quality/compression settings).
 */
declare module "@novnc/novnc" {
  export interface RFBOptions {
    shared?: boolean;
    credentials?: { username?: string; password?: string; target?: string };
    wsProtocols?: string[];
  }

  export default class RFB extends EventTarget {
    constructor(target: HTMLElement, url: string, options?: RFBOptions);

    scaleViewport: boolean;
    resizeSession: boolean;
    showDotCursor: boolean;
    viewOnly: boolean;
    clipViewport: boolean;

    disconnect(): void;
    sendCredentials(credentials: { username?: string; password?: string }): void;
    sendKey(keysym: number, code: string, down?: boolean): void;
    sendCtrlAltDel(): void;
    focus(): void;
    blur(): void;
  }
}
