/*
 * Pure decision logic of the status LEDs (no Zephyr/ZMK dependencies), so it can
 * be unit-tested on the host: tests/host/test_status_logic.c.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#define SL_NUM_LEDS 4
#define SL_ALL 0x0F

/* One step of an animation: `mask` on for on_ms, then all off for off_ms,
 * `count` times. With `chase`, the LEDs of `mask` light one after another
 * (LED1 -> LED4), each for on_ms. count == 0: no animation (just re-apply the
 * steady-state / layer LEDs). */
struct sl_pattern {
    uint8_t mask;
    uint8_t count;
    bool chase;
    uint16_t on_ms;
    uint16_t off_ms;
};

/* Battery: 1-4 LEDs solid (<=25 % -> 1, <=50 -> 2, <=75 -> 3, else 4);
 * at/below `low_pct` LED1 blinks fast instead. soc 0 = unknown -> LED1 blinks. */
static inline struct sl_pattern sl_battery_pattern(uint8_t soc, uint8_t low_pct,
                                                   uint16_t show_ms) {
    if (soc <= low_pct) {
        return (struct sl_pattern){.mask = 0x01, .count = 5, .on_ms = 100, .off_ms = 100};
    }
    uint8_t n = soc > 75 ? 4 : soc > 50 ? 3 : soc > 25 ? 2 : 1;
    return (struct sl_pattern){.mask = (uint8_t)((1u << n) - 1), .count = 1, .on_ms = show_ms};
}

/* BLE profile 0-3 -> LED1-LED4; higher profiles (ZMK has 5 by default) -> all four. */
static inline uint8_t sl_profile_mask(int profile) {
    return (profile >= 0 && profile < SL_NUM_LEDS) ? (uint8_t)(1u << profile) : SL_ALL;
}

/* Steady-state LEDs for the highest active layer: layer 1-4 -> LED1-LED4, base -> off. */
static inline uint8_t sl_layer_mask(int layer) {
    return (layer >= 1 && layer <= SL_NUM_LEDS) ? (uint8_t)(1u << (layer - 1)) : 0;
}

enum sl_link {
    SL_LINK_CONNECTED, /* host (left) / left half (right) connected */
    SL_LINK_OPEN,      /* central: profile unpaired, advertising for pairing */
    SL_LINK_SEARCHING, /* central: paired host not connected; right: no link to left */
};

/* What the connection indicator does on each tick (ticks run every
 * SL_CONN_PERIOD_MS while not connected and until the timeout). */
struct sl_conn_step {
    struct sl_pattern pattern; /* count == 0: show nothing this tick */
    bool again;                /* schedule another tick */
};

#define SL_CONN_PERIOD_MS 1500

/* `fresh`: first tick after a state change / boot / IND_CON press.
 * `in_window`: still within CONN_TIMEOUT of that. `central`: left half. */
static inline struct sl_conn_step sl_conn_tick(enum sl_link link, int profile, bool central,
                                               bool fresh, bool in_window,
                                               uint16_t confirm_ms) {
    struct sl_conn_step s = {0};
    uint8_t mask = central ? sl_profile_mask(profile) : SL_ALL;

    if (link == SL_LINK_CONNECTED) {
        if (fresh) { /* one confirmation, then dark */
            s.pattern = (struct sl_pattern){.mask = mask, .count = 1, .on_ms = confirm_ms};
        }
        return s;
    }
    if (!in_window) {
        return s; /* gave up showing it: dark until the next change */
    }
    s.again = true;
    if (link == SL_LINK_OPEN) { /* pairing: fast triple blink of the profile LED */
        s.pattern = (struct sl_pattern){.mask = mask, .count = 3, .on_ms = 80, .off_ms = 120};
    } else if (central) { /* known host, not connected: one short blip */
        s.pattern = (struct sl_pattern){.mask = mask, .count = 1, .on_ms = 60};
    } else { /* right half looking for the left half: quick LED1->LED4 chase */
        s.pattern =
            (struct sl_pattern){.mask = SL_ALL, .count = 1, .chase = true, .on_ms = 60};
    }
    return s;
}
