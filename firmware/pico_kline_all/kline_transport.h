// Transport selector for pico_kline_all.
//
// This enum lives in a header (not the .ino) on purpose: Arduino auto-generates
// function prototypes and prepends them ABOVE the sketch body, so a type defined
// in the .ino isn't visible to a prototype like `hostAvailable(ActiveT)`. Types
// pulled in via #include are processed first, so this is always in scope.
#pragma once

enum ActiveT { T_USB, T_BLE, T_WIFI };
