/* Host unit test of src/status_logic.h:  cc -I../../src test_status_logic.c && ./a.out */
#include <stdio.h>
#include "status_logic.h"

static int fails;
#define CHECK(c)                                                                        \
    do {                                                                                \
        if (!(c)) {                                                                     \
            printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c);                         \
            fails++;                                                                    \
        }                                                                               \
    } while (0)

int main(void) {
    /* battery: quarters -> 1-4 LEDs solid for show_ms; low -> LED1 blinks 5x */
    struct { uint8_t soc, mask, count; } bat[] = {
        {100, 0x0F, 1}, {76, 0x0F, 1}, {75, 0x07, 1}, {51, 0x07, 1}, {50, 0x03, 1},
        {26, 0x03, 1},  {25, 0x01, 1}, {11, 0x01, 1}, {10, 0x01, 5}, {1, 0x01, 5},
        {0, 0x01, 5}, /* unknown */
    };
    for (unsigned i = 0; i < sizeof(bat) / sizeof(bat[0]); i++) {
        struct sl_pattern p = sl_battery_pattern(bat[i].soc, 10, 2000);
        CHECK(p.mask == bat[i].mask);
        CHECK(p.count == bat[i].count);
        CHECK(p.count == 1 ? p.on_ms == 2000 : p.on_ms == 100 && p.off_ms == 100);
        CHECK(!p.chase);
    }

    /* profiles 0-3 -> one LED each, others -> all */
    CHECK(sl_profile_mask(0) == 0x1 && sl_profile_mask(1) == 0x2);
    CHECK(sl_profile_mask(2) == 0x4 && sl_profile_mask(3) == 0x8);
    CHECK(sl_profile_mask(4) == 0xF && sl_profile_mask(-1) == 0xF);

    /* layers: base off, 1-4 -> LED1-4, beyond -> off */
    CHECK(sl_layer_mask(0) == 0 && sl_layer_mask(5) == 0);
    for (int l = 1; l <= 4; l++) {
        CHECK(sl_layer_mask(l) == 1 << (l - 1));
    }

    struct sl_conn_step s;
    /* central, connected: confirmation once (fresh), nothing afterwards, no re-tick */
    s = sl_conn_tick(SL_LINK_CONNECTED, 2, true, true, true, 1000);
    CHECK(s.pattern.mask == 0x4 && s.pattern.count == 1 && s.pattern.on_ms == 1000 && !s.again);
    s = sl_conn_tick(SL_LINK_CONNECTED, 2, true, false, true, 1000);
    CHECK(s.pattern.count == 0 && !s.again);
    /* central, open profile: triple blink of the profile LED, keeps ticking in window */
    s = sl_conn_tick(SL_LINK_OPEN, 1, true, true, true, 1000);
    CHECK(s.pattern.mask == 0x2 && s.pattern.count == 3 && s.again);
    s = sl_conn_tick(SL_LINK_OPEN, 1, true, false, true, 1000);
    CHECK(s.pattern.count == 3 && s.again);
    /* ... and goes dark after the window */
    s = sl_conn_tick(SL_LINK_OPEN, 1, true, false, false, 1000);
    CHECK(s.pattern.count == 0 && !s.again);
    /* central, bonded host missing: one short blip */
    s = sl_conn_tick(SL_LINK_SEARCHING, 0, true, false, true, 1000);
    CHECK(s.pattern.mask == 0x1 && s.pattern.count == 1 && s.pattern.on_ms <= 100 && s.again);
    /* peripheral: connected -> all four once; searching -> chase; window end -> dark */
    s = sl_conn_tick(SL_LINK_CONNECTED, 0, false, true, true, 1000);
    CHECK(s.pattern.mask == 0xF && s.pattern.count == 1 && !s.pattern.chase && !s.again);
    s = sl_conn_tick(SL_LINK_SEARCHING, 0, false, false, true, 1000);
    CHECK(s.pattern.mask == 0xF && s.pattern.chase && s.again);
    s = sl_conn_tick(SL_LINK_SEARCHING, 0, false, true, false, 1000);
    CHECK(s.pattern.count == 0 && !s.again);

    /* power: every periodic pattern is lit well under half of the tick period */
    s = sl_conn_tick(SL_LINK_OPEN, 0, true, false, true, 1000);
    CHECK(s.pattern.count * s.pattern.on_ms * 4 < SL_CONN_PERIOD_MS);
    s = sl_conn_tick(SL_LINK_SEARCHING, 0, false, false, true, 1000);
    CHECK(4 * s.pattern.on_ms * 4 < SL_CONN_PERIOD_MS);

    printf(fails ? "status_logic: %d FAILED\n" : "status_logic: all checks passed\n", fails);
    return fails != 0;
}
