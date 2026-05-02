(() => {
  // 1. Remove webdriver flag
  Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true,
  });

  // 2. Languages
  Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
    configurable: true,
  });

  // 3. Vendor
  Object.defineProperty(navigator, 'vendor', {
    get: () => 'Google Inc.',
    configurable: true,
  });

  // 4. Platform
  Object.defineProperty(navigator, 'platform', {
    get: () => 'Win32',
    configurable: true,
  });

  // 5. Hardware concurrency
  Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => 8,
    configurable: true,
  });

  // 6. Device memory
  Object.defineProperty(navigator, 'deviceMemory', {
    get: () => 8,
    configurable: true,
  });

  // 7. Max touch points (desktop = 0)
  Object.defineProperty(navigator, 'maxTouchPoints', {
    get: () => 0,
    configurable: true,
  });

  // 8. Realistic Chrome object
  window.chrome = {
    app: {
      isInstalled: false,
      InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
      RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' },
    },
    runtime: {
      OnInstalledReason: { CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update' },
      OnRestartRequiredReason: { APP_UPDATE: 'app_update', GC: 'gc', OS_UPDATE: 'os_update' },
      PlatformArch: { ARM: 'arm', ARM64: 'arm64', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
      PlatformNaclArch: { ARM: 'arm', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
      PlatformOs: { ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', OPENBSD: 'openbsd', WIN: 'win' },
      RequestUpdateCheckStatus: { NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available' },
    },
  };

  // 9. Permissions — handle notifications correctly, pass others through
  const _origPermQuery = window.navigator.permissions.query;
  window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications'
      ? Promise.resolve({ state: Notification.permission })
      : _origPermQuery(parameters)
  );

  // 10. Canvas fingerprint noise — add imperceptible jitter to text rendering
  const _origGetContext = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (type, ...args) {
    const ctx = _origGetContext.call(this, type, ...args);
    if (type === '2d' && ctx) {
      const _origFillText = ctx.fillText.bind(ctx);
      ctx.fillText = function (text, x, y, ...rest) {
        ctx.shadowBlur = Math.random() * 0.02;
        return _origFillText(text, x, y, ...rest);
      };
      const _origStrokeText = ctx.strokeText.bind(ctx);
      ctx.strokeText = function (text, x, y, ...rest) {
        ctx.shadowBlur = Math.random() * 0.02;
        return _origStrokeText(text, x, y, ...rest);
      };
    }
    return ctx;
  };

  // 11. WebGL — spoof UNMASKED_VENDOR and UNMASKED_RENDERER
  const _webglParamHandler = {
    apply(target, ctx, args) {
      const param = args[0];
      if (param === 37445) return 'Intel Inc.';              // UNMASKED_VENDOR_WEBGL
      if (param === 37446) return 'Intel Iris OpenGL Engine'; // UNMASKED_RENDERER_WEBGL
      return Reflect.apply(target, ctx, args);
    },
  };
  try {
    WebGLRenderingContext.prototype.getParameter = new Proxy(
      WebGLRenderingContext.prototype.getParameter, _webglParamHandler
    );
  } catch (_) {}
  try {
    WebGL2RenderingContext.prototype.getParameter = new Proxy(
      WebGL2RenderingContext.prototype.getParameter, _webglParamHandler
    );
  } catch (_) {}

  // 12. Battery API — report always charging and full
  if (navigator.getBattery) {
    navigator.getBattery = () => Promise.resolve({
      charging: true,
      chargingTime: 0,
      dischargingTime: Infinity,
      level: 1.0,
      addEventListener() {},
      removeEventListener() {},
      dispatchEvent() { return true; },
    });
  }

  // 13. Network connection — report stable 4G
  try {
    Object.defineProperty(navigator, 'connection', {
      get: () => ({
        rtt: 100,
        downlink: 10,
        effectiveType: '4g',
        saveData: false,
        addEventListener() {},
        removeEventListener() {},
      }),
      configurable: true,
    });
  } catch (_) {}

  // 14. Clean up CDP / ChromeDriver artifacts leaked onto window
  try {
    Object.keys(window).forEach(key => {
      if (key.startsWith('cdc_') || key.startsWith('__cdc_')) {
        try { delete window[key]; } catch (_) {}
      }
    });
  } catch (_) {}

  // 16. Cursor indicator — dot driven by the agent, not the physical mouse
  (function () {
    function injectCursor() {
      if (document.getElementById('__wu_cursor__')) return;
      var cur = document.createElement('div');
      cur.id = '__wu_cursor__';
      cur.style.cssText =
        'position:fixed;top:-20px;left:-20px;width:14px;height:14px;' +
        'border-radius:50%;' +
        'background:rgba(30,110,255,0.9);' +
        'border:2px solid rgba(255,255,255,0.95);' +
        'box-shadow:0 0 8px 3px rgba(30,110,255,0.55);' +
        'pointer-events:none;z-index:2147483646;' +
        'transform:translate(-50%,-50%);';
      (document.body || document.documentElement).appendChild(cur);
    }

    window.__wu_set_cursor__ = function (x, y) {
      var cur = document.getElementById('__wu_cursor__');
      if (!cur) { injectCursor(); cur = document.getElementById('__wu_cursor__'); }
      if (cur) { cur.style.left = x + 'px'; cur.style.top = y + 'px'; }
    };

    window.__wu_click_cursor__ = function () {
      var cur = document.getElementById('__wu_cursor__');
      if (!cur) return;
      cur.style.transform = 'translate(-50%,-50%) scale(1.8)';
      cur.style.transition = 'transform 0.12s ease,opacity 0.12s ease';
      setTimeout(function () {
        cur.style.transform = 'translate(-50%,-50%) scale(1)';
      }, 120);
    };

    if (document.body) {
      injectCursor();
    } else {
      document.addEventListener('DOMContentLoaded', injectCursor);
    }
  })();

  // 17. Welcome screen on about:blank
  if (location.href === 'about:blank') {
    (function () {
      function renderWelcome() {
        var style = document.createElement('style');
        style.textContent = [
          '@keyframes wu-pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.6;transform:scale(0.96)}}',
          '@keyframes wu-fadein{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}',
          '@keyframes wu-spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}',
          '.wu-wrap{animation:wu-fadein 0.7s cubic-bezier(.22,.68,0,1.2) both}',
          '.wu-badge{animation:wu-fadein 0.7s 0.35s cubic-bezier(.22,.68,0,1.2) both;opacity:0}',
          '.wu-sub{animation:wu-fadein 0.7s 0.5s ease both;opacity:0}',
          '.wu-ring{animation:wu-spin 8s linear infinite}',
          '.wu-dot{animation:wu-pulse 2.4s ease-in-out infinite}',
        ].join('');
        document.head.appendChild(style);

        document.documentElement.style.cssText = 'margin:0;padding:0;height:100%;';
        document.body.style.cssText =
          'margin:0;height:100vh;display:flex;align-items:center;justify-content:center;' +
          'background:#080a0f;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,sans-serif;' +
          'overflow:hidden;user-select:none;';

        document.body.innerHTML =
          // dot-grid background
          '<svg style="position:fixed;inset:0;width:100%;height:100%;opacity:0.18;pointer-events:none;" xmlns="http://www.w3.org/2000/svg">' +
            '<defs><pattern id="g" x="0" y="0" width="28" height="28" patternUnits="userSpaceOnUse">' +
              '<circle cx="1" cy="1" r="1" fill="#3b6fff"/>' +
            '</pattern></defs>' +
            '<rect width="100%" height="100%" fill="url(#g)"/>' +
          '</svg>' +

          // ambient glow blobs
          '<div style="position:fixed;top:-180px;left:50%;transform:translateX(-50%);width:600px;height:400px;' +
            'background:radial-gradient(ellipse,rgba(30,100,255,0.12) 0%,transparent 70%);pointer-events:none;"></div>' +
          '<div style="position:fixed;bottom:-200px;left:50%;transform:translateX(-50%);width:700px;height:400px;' +
            'background:radial-gradient(ellipse,rgba(10,60,200,0.1) 0%,transparent 70%);pointer-events:none;"></div>' +

          // card
          '<div class="wu-wrap" style="position:relative;text-align:center;padding:56px 72px 48px;' +
            'background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);' +
            'border-radius:20px;backdrop-filter:blur(12px);' +
            'box-shadow:0 0 0 1px rgba(30,110,255,0.08),0 32px 80px rgba(0,0,0,0.5);' +
            'max-width:420px;">' +

            // icon
            '<div style="position:relative;width:72px;height:72px;margin:0 auto 32px;">' +
              '<svg class="wu-ring" style="position:absolute;inset:0;width:72px;height:72px;" viewBox="0 0 72 72" fill="none" xmlns="http://www.w3.org/2000/svg">' +
                '<circle cx="36" cy="36" r="34" stroke="url(#rg)" stroke-width="1.5" stroke-dasharray="6 6"/>' +
                '<defs><linearGradient id="rg" x1="0" y1="0" x2="72" y2="72" gradientUnits="userSpaceOnUse">' +
                  '<stop offset="0%" stop-color="#1a6fff" stop-opacity="0.8"/>' +
                  '<stop offset="100%" stop-color="#1a6fff" stop-opacity="0"/>' +
                '</linearGradient></defs>' +
              '</svg>' +
              '<div style="position:absolute;inset:10px;border-radius:50%;' +
                'background:linear-gradient(145deg,#1a5fff,#0a2fa8);' +
                'box-shadow:0 0 32px 8px rgba(30,100,255,0.4);' +
                'display:flex;align-items:center;justify-content:center;">' +
                '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.95)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' +
                  '<circle cx="12" cy="12" r="10"/>' +
                  '<line x1="2" y1="12" x2="22" y2="12"/>' +
                  '<path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>' +
                '</svg>' +
              '</div>' +
            '</div>' +

            // wordmark
            '<div style="font-size:32px;font-weight:700;letter-spacing:-1px;color:#eef0f8;margin-bottom:8px;">' +
              'Web<span style="color:#3b7fff;">Use</span>' +
            '</div>' +
            '<div style="font-size:13px;color:#3b4562;letter-spacing:0.6px;text-transform:uppercase;font-weight:500;margin-bottom:32px;">AI Browser Agent</div>' +

            // divider
            '<div style="height:1px;background:linear-gradient(90deg,transparent,rgba(59,111,255,0.25),transparent);margin-bottom:28px;"></div>' +

            // status row
            '<div class="wu-badge" style="display:inline-flex;align-items:center;gap:8px;' +
              'background:rgba(30,100,255,0.08);border:1px solid rgba(30,100,255,0.18);' +
              'border-radius:100px;padding:6px 16px;">' +
              '<span class="wu-dot" style="width:7px;height:7px;border-radius:50%;background:#3b7fff;display:block;flex-shrink:0;"></span>' +
              '<span style="font-size:12px;font-weight:500;color:#6b8fff;letter-spacing:0.3px;">Ready · Awaiting instruction</span>' +
            '</div>' +

            // sub-hint
            '<p class="wu-sub" style="margin:20px 0 0;font-size:12px;color:#2a3050;letter-spacing:0.2px;">' +
              'Type a task to get started' +
            '</p>' +
          '</div>';
      }

      if (document.body) {
        renderWelcome();
      } else {
        document.addEventListener('DOMContentLoaded', renderWelcome);
      }
    })();
  }
})();
