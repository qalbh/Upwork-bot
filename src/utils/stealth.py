STEALTH_SCRIPT = """
(() => {
    // ── 1. Remove webdriver flag ──────────────────────────────────────────
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

    // ── 2. Navigator properties ───────────────────────────────────────────
    Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });
    Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' });
    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
    Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
    Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    Object.defineProperty(navigator, 'language', { get: () => 'en-US' });
    Object.defineProperty(navigator, 'doNotTrack', { get: () => null });
    Object.defineProperty(navigator, 'cookieEnabled', { get: () => true });
    Object.defineProperty(navigator, 'onLine', { get: () => true });

    // ── 3. Plugins (empty in bots, real browsers have some) ───────────────
    const pluginData = [
        { name: 'Chrome PDF Plugin',  filename: 'internal-pdf-viewer',          description: 'Portable Document Format', suffixes: 'pdf' },
        { name: 'Chrome PDF Viewer',  filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '',                     suffixes: 'pdf' },
        { name: 'Native Client',      filename: 'internal-nacl-plugin',          description: '',                       suffixes: '' },
    ];
    const plugins = pluginData.map(d => {
        const p = Object.create(Plugin.prototype);
        Object.defineProperties(p, {
            name:        { value: d.name },
            filename:    { value: d.filename },
            description: { value: d.description },
            length:      { value: 1 },
        });
        return p;
    });
    Object.defineProperty(navigator, 'plugins', {
        get: () => Object.assign(plugins, {
            item:      (i) => plugins[i] || null,
            namedItem: (n) => plugins.find(p => p.name === n) || null,
            refresh:   () => {},
            length:    plugins.length,
        }),
    });

    // ── 4. MimeTypes ──────────────────────────────────────────────────────
    const mimeData = [
        { type: 'application/pdf',         suffixes: 'pdf',  description: '' },
        { type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format' },
        { type: 'application/x-nacl',      suffixes: '',     description: 'Native Client Executable' },
        { type: 'application/x-pnacl',     suffixes: '',     description: 'Portable Native Client Executable' },
    ];
    const mimes = mimeData.map(d => {
        const m = Object.create(MimeType.prototype);
        Object.defineProperties(m, {
            type:        { value: d.type },
            suffixes:    { value: d.suffixes },
            description: { value: d.description },
        });
        return m;
    });
    Object.defineProperty(navigator, 'mimeTypes', {
        get: () => Object.assign(mimes, {
            item:      (i) => mimes[i] || null,
            namedItem: (n) => mimes.find(m => m.type === n) || null,
            length:    mimes.length,
        }),
    });

    // ── 5. Screen properties ──────────────────────────────────────────────
    Object.defineProperty(screen, 'colorDepth',  { get: () => 24 });
    Object.defineProperty(screen, 'pixelDepth',  { get: () => 24 });
    Object.defineProperty(screen, 'availWidth',  { get: () => window.screen.width });
    Object.defineProperty(screen, 'availHeight', { get: () => window.screen.height - 40 });

    // ── 6. Window sizing (outer should be >= inner in real browsers) ───────
    if (window.outerWidth === 0) {
        Object.defineProperty(window, 'outerWidth',  { get: () => window.innerWidth });
        Object.defineProperty(window, 'outerHeight', { get: () => window.innerHeight + 85 });
    }

    // ── 7. Full chrome object ─────────────────────────────────────────────
    window.chrome = {
        app: {
            isInstalled: false,
            InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
            RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' },
        },
        runtime: {
            OnInstalledReason: { CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update' },
            OnRestartRequiredReason: { APP_UPDATE: 'app_update', GC_REQUIRED: 'gc_required', PERIODIC: 'periodic' },
            PlatformArch: { ARM: 'arm', ARM64: 'arm64', X86_32: 'x86-32', X86_64: 'x86-64' },
            PlatformOs: { ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', WIN: 'win' },
            RequestUpdateCheckStatus: { NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available' },
        },
        csi: () => ({ startE: Date.now(), onloadT: Date.now(), pageT: Math.random() * 3000 + 1000, tran: 15 }),
        loadTimes: () => ({
            commitLoadTime:           Date.now() / 1000 - 0.8,
            connectionInfo:           'http/2',
            finishDocumentLoadTime:   Date.now() / 1000 - 0.2,
            finishLoadTime:           Date.now() / 1000 - 0.1,
            firstPaintAfterLoadTime:  0,
            firstPaintTime:           Date.now() / 1000 - 0.5,
            navigationType:           'Other',
            npnNegotiatedProtocol:    'h2',
            requestTime:              Date.now() / 1000 - 1.2,
            startLoadTime:            Date.now() / 1000 - 1.0,
            wasAlternateProtocolAvailable: false,
            wasFetchedViaSpdy:        true,
            wasNpnNegotiated:         true,
        }),
    };

    // ── 8. WebGL — mask vendor/renderer to look like real Mac GPU ─────────
    const getParam = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {
        if (param === 37445) return 'Intel Inc.';
        if (param === 37446) return 'Intel Iris Pro OpenGL Engine';
        return getParam.call(this, param);
    };
    if (typeof WebGL2RenderingContext !== 'undefined') {
        const getParam2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(param) {
            if (param === 37445) return 'Intel Inc.';
            if (param === 37446) return 'Intel Iris Pro OpenGL Engine';
            return getParam2.call(this, param);
        };
    }

    // ── 9. Permissions — realistic responses ─────────────────────────────
    const _origQuery = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = (params) => {
        const map = {
            'notifications':   Notification.permission,
            'clipboard-read':  'prompt',
            'clipboard-write': 'granted',
            'camera':          'prompt',
            'microphone':      'prompt',
            'geolocation':     'prompt',
        };
        if (params.name in map) {
            return Promise.resolve({ state: map[params.name], onchange: null });
        }
        return _origQuery(params);
    };

    // ── 10. Network connection info ───────────────────────────────────────
    if (!navigator.connection) {
        Object.defineProperty(navigator, 'connection', {
            get: () => ({ effectiveType: '4g', rtt: 50, downlink: 20, saveData: false }),
        });
    }

    // ── 11. Remove CDP / automation artifacts ─────────────────────────────
    const artifacts = [
        '$cdc_asdjflasutopfhvcZLmcfl_',
        '__playwright', '__pw_manual', '__PW_inspect_',
        '__selenium_unwrapped', '__webdriver_evaluate', '__driver_evaluate',
        '_phantom', '__nightmare', 'callPhantom',
        '_selenium', 'calledSelenium', '_Selenium_IDE_Recorder',
        '__webdriverFunc', '__fxdriver_unwrapped', '__driver_unwrapped',
    ];
    artifacts.forEach(k => { try { delete window[k]; } catch (_) {} });

    // ── 12. Canvas — add imperceptible noise to fingerprint ───────────────
    const _toDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        const ctx = this.getContext('2d');
        if (ctx) {
            const imgData = ctx.getImageData(0, 0, this.width, this.height);
            for (let i = 0; i < imgData.data.length; i += 512) {
                imgData.data[i] ^= 1;
            }
            ctx.putImageData(imgData, 0, 0);
        }
        return _toDataURL.apply(this, arguments);
    };

    // ── 13. Page visibility — always visible ──────────────────────────────
    Object.defineProperty(document, 'hidden',           { get: () => false });
    Object.defineProperty(document, 'visibilityState',  { get: () => 'visible' });
    document.addEventListener('visibilitychange', e => e.stopImmediatePropagation(), true);

    // ── 14. Media devices — return realistic device list ─────────────────
    if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        navigator.mediaDevices.enumerateDevices = () => Promise.resolve([
            { deviceId: 'default', kind: 'audioinput',  label: '',  groupId: 'default' },
            { deviceId: 'default', kind: 'audiooutput', label: '',  groupId: 'default' },
        ]);
    }
})();
"""
