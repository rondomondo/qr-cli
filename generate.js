#!/usr/bin/env node

'use strict';

// NOte that qr-code-styling references browser globals at require-time on some code paths
const { JSDOM } = require('jsdom');
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
global.window = dom.window;
global.document = dom.window.document;
global.navigator = dom.window.navigator;

const { QRCodeStyling } = require('qr-code-styling/lib/qr-code-styling.common.js');
const nodeCanvas = require('canvas');
const sharp = require('sharp');

// Parse CLI args
// Accepts a single JSON argument OR individual --key=value flags.
// Priority: --json='{}' > individual flags
// TODO: Do I want to support `--key "walue"` as well as with equals
function parseArgs(argv) {
    const args = argv.slice(2);

    // Bail out early with usage info if the caller just wants to know what this thing takes
    if (args.includes('--help') || args.includes('-h')) {
        printHelp();
        process.exit(0);
    }

    // Try --json='{...}' first
    const jsonFlag = args.find((a) => a.startsWith('--json='));
    if (jsonFlag) {
        try {
            return JSON.parse(jsonFlag.slice(7));
        } catch (e) {
            fatal(`Invalid JSON passed to --json: ${e.message}`);
        }
    }

    // Also accept piped JSON via stdin (non-tty)
    // (handled separately below)

    // Fall back to --key=value pairs with dot-path support
    const opts = {};
    for (const arg of args) {
        if (!arg.startsWith('--')) continue;
        const eq = arg.indexOf('=');
        if (eq === -1) continue;
        const key = arg.slice(2, eq);
        const raw = arg.slice(eq + 1);

        // Parse value: try number/bool/null, fall back to string
        let value;
        if (raw === 'true') value = true;
        else if (raw === 'false') value = false;
        else if (raw === 'null') value = null;
        else if (!isNaN(raw) && raw !== '') value = Number(raw);
        else {
            // Strip surrounding quotes if present
            value = raw.replace(/^['"]|['"]$/g, '');
        }

        setDeep(opts, key, value);
    }

    return opts;
}

// Print a structured JSON usage block to stdout so callers (scripts, CI) can
// parse it the same way they parse a real QR result - no separate text parsing needed
function printHelp() {
    const usage = {
        usage: 'docker run --rm qr-cli [OPTIONS]',
        description: 'Generate a styled QR code and return the result as JSON.',
        options: {
            '--data=<string>': '(required) The URL or string to encode',
            '--format=<png|jpeg|webp|svg>': 'Output format (default: png)',
            '--width=<px>': 'Image width in pixels (default: 300)',
            '--height=<px>': 'Image height in pixels (default: 300)',
            '--border=<px>': 'Pixel border around the QR code (default: 10)',
            '--margin=<px>': 'Quiet zone around the QR code (default: 0)',
            '--project=<name>':
                'Used to namespace the output filename (e.g. "filename": "output/images/daveco/300x300_0255C7_FDFBD4_daveco.png",    // output/images/{project}/{width}x{height}_{dots}_{bg}_{project}.{format}))',
            '--dotsOptions.type=<square|rounded|...>': 'Dot shape style',
            '--dotsOptions.color=<hex>': 'Dot colour (default: #000000)',
            '--backgroundOptions.color=<hex>': 'Background colour (default: #ffffff)',
            '--image=<url>': 'Centre logo image URL',
            '--json=<json>': 'Pass all options as a single JSON string (takes priority over flags)',
            '--help, -h': 'Show this message',
        },
        examples: [
            'docker run --rm qr-cli --data="https://example.com"',
            'docker run --rm qr-cli --data="https://example.com" --format=svg --width=512 --height=512',
        ],
        output: {
            success: 'boolean',
            meta: 'object - format, dimensions, colours, timing, etc.',
            image: 'object - filename, base64, dataUri',
        },
    };
    process.stdout.write(JSON.stringify(usage, null, 2) + '\n');
}

function setDeep(obj, path, value) {
    const parts = path.split('.');
    let cur = obj;
    for (let i = 0; i < parts.length - 1; i++) {
        if (cur[parts[i]] == null || typeof cur[parts[i]] !== 'object') {
            cur[parts[i]] = {};
        }
        cur = cur[parts[i]];
    }
    cur[parts[parts.length - 1]] = value;
}

function fatal(msg, code = 1) {
    const out = JSON.stringify({ success: false, error: msg }) + '\n';
    process.stdout.write(out);
    process.stderr.write(out);
    process.exit(code);
}

// Main
async function main() {
    let options = {};

    // Support piped JSON (e.g. echo '{}' | docker run ...)
    if (!process.stdin.isTTY) {
        let stdinData = '';
        process.stdin.setEncoding('utf8');
        for await (const chunk of process.stdin) stdinData += chunk;
        stdinData = stdinData.trim();
        if (stdinData) {
            try {
                options = JSON.parse(stdinData);
            } catch (e) {
                fatal(`Invalid JSON from stdin: ${e.message}`);
            }
        }
    }

    // CLI args override / merge with stdin
    const cliOptions = parseArgs(process.argv);
    options = deepMerge(options, cliOptions);

    if (!options.data) {
        fatal(
            'Missing required option: "data" - the string/URL to encode. ' +
                'Pass --data="https://example.com" or supply JSON.',
        );
    }

    // Resolve output format
    const outputFormat = (options._format || options.format || 'png').toLowerCase().replace(/^\./, '');
    delete options._format;
    delete options.format;

    const isSvg = outputFormat === 'svg';
    const isWebp = outputFormat === 'webp';
    // qr-code-styling needs type:'svg' to use its SVG renderer; everything else uses canvas
    const type = options.type || (isSvg ? 'svg' : 'canvas');

    // Build QRCodeStyling options
    const qrOptions = {
        width: 300,
        height: 300,
        margin: 0,
        ...options,
        type,
        // Inject node dependencies
        ...(isSvg ? { jsdom: JSDOM } : { nodeCanvas }),
        // SVG + embedded image needs canvas too for the logo rasterisation step
        ...(isSvg && options.image ? { nodeCanvas } : {}),
    };

    // Strip non-QRCodeStyling keys before handing off to the library
    const cleanOptions = { ...qrOptions };

    const project = options.project || null;
    const border = cleanOptions.border ?? 0;
    delete cleanOptions.project;
    delete cleanOptions.border;

    const generatedAt = new Date().toISOString();
    const started = Date.now();
    const qrCode = new QRCodeStyling(cleanOptions);

    let buffer;
    try {
        // webp is not a native qr-code-styling format - generate png then re-encode
        const rawFormat = isWebp ? 'png' : outputFormat;
        buffer = await qrCode.getRawData(rawFormat);
        if (isWebp) {
            buffer = await sharp(buffer).webp().toBuffer();
        }
    } catch (err) {
        fatal(`QR generation failed: ${err.message}`);
    }

    const base64 = buffer.toString('base64');
    const mimeMap = {
        png: 'image/png',
        jpeg: 'image/jpeg',
        jpg: 'image/jpeg',
        webp: 'image/webp',
        svg: 'image/svg+xml',
    };
    const mimeType = mimeMap[outputFormat] || 'application/octet-stream';
    const dataUri = `data:${mimeType};base64,${base64}`;

    const durationMs = Date.now() - started;
    const ext = outputFormat === 'jpeg' ? 'jpg' : outputFormat;
    const dotsHex = (cleanOptions.dotsOptions?.color || '#000000').replace('#', '').toUpperCase();
    const bgHex = (cleanOptions.backgroundOptions?.color || '#ffffff').replace('#', '').toUpperCase();
    const filename = project
        ? `output/images/${project}/${cleanOptions.width}x${cleanOptions.height}_${dotsHex}_${bgHex}_${project}.${ext}`
        : `qr.${ext}`;

    const result = {
        success: true,
        meta: {
            format: outputFormat,
            mimeType,
            width: cleanOptions.width,
            height: cleanOptions.height,
            type: cleanOptions.type,
            data: options.data,
            project: project || undefined,
            sizeBytes: buffer.length,
            durationMs,
            generatedAt,
            errorCorrectionLevel: cleanOptions.qrOptions?.errorCorrectionLevel || 'Q',
            dotsType: cleanOptions.dotsOptions?.type || 'square',
            dotsColor: cleanOptions.dotsOptions?.color || '#000000',
            backgroundColor: cleanOptions.backgroundOptions?.color || '#ffffff',
            hasImage: Boolean(cleanOptions.image),
            margin: cleanOptions.margin,
            border,
        },
        image: {
            filename,
            generated: generatedAt,
            base64,
            dataUri,
        },
    };

    process.stdout.write(JSON.stringify(result) + '\n');
}

function deepMerge(target, source) {
    const out = { ...target };
    for (const [k, v] of Object.entries(source)) {
        if (v !== null && typeof v === 'object' && !Array.isArray(v) && typeof out[k] === 'object' && out[k] !== null) {
            out[k] = deepMerge(out[k], v);
        } else {
            out[k] = v;
        }
    }
    return out;
}

main().catch((err) => fatal(err.message));
