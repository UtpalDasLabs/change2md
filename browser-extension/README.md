# Change2MD browser extension

A Manifest V3 extension for Chrome, Edge, Brave and other Chromium browsers that support Manifest V3 extensions.

1. Open the browser's extensions page.
2. Enable developer mode.
3. Choose **Load unpacked** and select this `browser-extension` directory.
4. Open a public HTTPS page, then select Change2MD in the browser toolbar.

The popup reads the active tab's URL and sends that URL to the hosted Change2MD API. It does not read or extract page content. Conversion therefore works only for publicly accessible pages, not private intranet or login-protected pages. Markdown can be copied, downloaded and loaded in chunks.

The hosted service has no browser-specific authentication. Its existing file-size, output-size, timeout and concurrency limits apply. Production deployments should also apply edge-level rate limits.
