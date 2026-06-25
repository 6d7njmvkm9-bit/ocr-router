#!/usr/bin/env osascript -l JavaScript
// JXA entry point for legal-ocr convert

function run(argv) {
    const app = Application.currentApplication();
    app.includeStandardAdditions = true;
    const input = argv[0];
    if (!input) {
        console.log("Usage: convert.js <file>");
        return;
    }
    return input;
}
