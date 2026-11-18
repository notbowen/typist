/*
 * Sweep XIAO status LEDs: 4 plain GPIO LEDs (gpio-leds node `status_leds`).
 *
 * One thread plays short LED patterns from a queue; between patterns the LEDs
 * show the steady state, which is "all off" except while a non-base layer is
 * active (central). Decisions (which LEDs, how long) live in status_logic.h.
 *
 *   boot            battery level, 1-4 LEDs for 2 s (each half its own)
 *   left  (central) BLE profile change / host connect / disconnect:
 *                     connected      -> profile LED on 1 s, then dark
 *                     open profile   -> profile LED triple-blinks every 1.5 s
 *                     host missing   -> profile LED short blip every 1.5 s
 *                   (blinking stops after CONFIG_SWEEP_STATUS_LEDS_CONN_TIMEOUT_S)
 *                   layer 1-4 active -> LED1-LED4 lit while it is active
 *   right           link to left half: connected -> all 4 on 1 s;
 *                   searching -> LED1..4 chase every 1.5 s (same timeout)
 *   low battery     LED1 blinks 5x fast when the level drops to <= 10 %
 */
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/led.h>
#include <zephyr/sys/atomic.h>
#include <zephyr/logging/log.h>

#include <zmk/event_manager.h>
#include <zmk/events/activity_state_changed.h>
#include <zmk/activity.h>

#include "status_leds.h"
#include "status_logic.h"

LOG_MODULE_REGISTER(sweep_status_leds, CONFIG_ZMK_LOG_LEVEL);

#define IS_CENTRAL (!IS_ENABLED(CONFIG_ZMK_SPLIT) || IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL))
#define HOST_BLE (IS_ENABLED(CONFIG_ZMK_BLE) && IS_CENTRAL)
#define PERIPH_BLE (IS_ENABLED(CONFIG_ZMK_SPLIT_BLE) && !IS_CENTRAL)

#if IS_ENABLED(CONFIG_ZMK_BATTERY_REPORTING)
#include <zmk/battery.h>
#include <zmk/events/battery_state_changed.h>
#endif
#if HOST_BLE
#include <zmk/ble.h>
#include <zmk/events/ble_active_profile_changed.h>
#endif
#if PERIPH_BLE
#include <zmk/split/bluetooth/peripheral.h>
#include <zmk/events/split_peripheral_status_changed.h>
#endif
#if IS_ENABLED(CONFIG_SWEEP_STATUS_LEDS_LAYER)
#include <zmk/keymap.h>
#include <zmk/events/layer_state_changed.h>
#endif

#define LEDS_NODE DT_NODELABEL(status_leds)
BUILD_ASSERT(DT_CHILD_NUM(LEDS_NODE) == SL_NUM_LEDS, "status_leds must have 4 LEDs");

static const struct device *const leds = DEVICE_DT_GET(LEDS_NODE);

K_MSGQ_DEFINE(sl_queue, sizeof(struct sl_pattern), 8, 4);
K_MUTEX_DEFINE(sl_lock);

static atomic_t bg_mask;   /* steady-state LEDs (active layer) */
static atomic_t suspended; /* going to deep sleep: everything off */
static uint8_t current = 0xFF;

static void set_leds(uint8_t mask) {
    k_mutex_lock(&sl_lock, K_FOREVER);
    if (atomic_get(&suspended)) {
        mask = 0;
    }
    if (mask != current) {
        for (int i = 0; i < SL_NUM_LEDS; i++) {
            if (mask & BIT(i)) {
                led_on(leds, i);
            } else {
                led_off(leds, i);
            }
        }
        current = mask;
        LOG_DBG("%c%c%c%c at %u ms", mask & 1 ? '1' : '.', mask & 2 ? '2' : '.',
                mask & 4 ? '3' : '.', mask & 8 ? '4' : '.', k_uptime_get_32());
    }
    k_mutex_unlock(&sl_lock);
}

static void play(const struct sl_pattern *p) {
    for (int c = 0; c < p->count && !atomic_get(&suspended); c++) {
        if (p->chase) {
            for (int i = 0; i < SL_NUM_LEDS; i++) {
                if (p->mask & BIT(i)) {
                    set_leds(BIT(i));
                    k_msleep(p->on_ms);
                }
            }
        } else {
            set_leds(p->mask);
            k_msleep(p->on_ms);
        }
        if (p->off_ms && c + 1 < p->count) {
            set_leds(0);
            k_msleep(p->off_ms);
        }
    }
    set_leds((uint8_t)atomic_get(&bg_mask));
}

static int enqueue(struct sl_pattern p) {
    int err = k_msgq_put(&sl_queue, &p, K_NO_WAIT);
    if (err) {
        LOG_DBG("queue full, pattern dropped");
    }
    return err;
}

/* ---- battery ---- */

#if IS_ENABLED(CONFIG_ZMK_BATTERY_REPORTING)
static int64_t last_low_warning;
static bool warned_once;

static struct sl_pattern battery_pattern(void) {
    return sl_battery_pattern(zmk_battery_state_of_charge(), CONFIG_SWEEP_STATUS_LEDS_BATTERY_LOW,
                              CONFIG_SWEEP_STATUS_LEDS_BATTERY_MS);
}
#endif

void sweep_status_leds_show_battery(void) {
#if IS_ENABLED(CONFIG_ZMK_BATTERY_REPORTING)
    LOG_DBG("battery %u %%", zmk_battery_state_of_charge());
    enqueue(battery_pattern());
#endif
}

/* ---- connection ---- */

#if HOST_BLE || PERIPH_BLE
static int64_t conn_window_end;
static bool conn_fresh;

static void conn_tick(struct k_work *work);
static K_WORK_DELAYABLE_DEFINE(conn_work, conn_tick);

static void conn_tick(struct k_work *work) {
    enum sl_link link;
    int profile = 0;
#if HOST_BLE
    profile = zmk_ble_active_profile_index();
    link = zmk_ble_active_profile_is_connected() ? SL_LINK_CONNECTED
           : zmk_ble_active_profile_is_open()    ? SL_LINK_OPEN
                                                 : SL_LINK_SEARCHING;
#else
    link = zmk_split_bt_peripheral_is_connected() ? SL_LINK_CONNECTED : SL_LINK_SEARCHING;
#endif
    struct sl_conn_step step =
        sl_conn_tick(link, profile, IS_CENTRAL, conn_fresh, k_uptime_get() < conn_window_end,
                     CONFIG_SWEEP_STATUS_LEDS_CONFIRM_MS);
    LOG_DBG("link %d profile %d fresh %d -> %d blink(s), again %d", link, profile, conn_fresh,
            step.pattern.count, step.again);
    /* periodic blinks only when nothing else is playing, so they never pile up */
    if (step.pattern.count && (conn_fresh || k_msgq_num_used_get(&sl_queue) == 0)) {
        enqueue(step.pattern);
    }
    conn_fresh = false;
    if (step.again && !atomic_get(&suspended)) {
        k_work_schedule(&conn_work, K_MSEC(SL_CONN_PERIOD_MS));
    }
}
#endif

void sweep_status_leds_show_connection(void) {
#if HOST_BLE || PERIPH_BLE
    conn_window_end = k_uptime_get() + CONFIG_SWEEP_STATUS_LEDS_CONN_TIMEOUT_S * 1000LL;
    conn_fresh = true;
    /* short debounce: profile switches raise several events in a row */
    k_work_reschedule(&conn_work, K_MSEC(150));
#endif
}

/* ---- thread ---- */

static void sl_thread(void *a, void *b, void *c) {
    if (!device_is_ready(leds)) {
        LOG_ERR("status LEDs not ready");
        return;
    }
    set_leds(0);

#if IS_ENABLED(CONFIG_SWEEP_STATUS_LEDS_BOOT_BATTERY) && IS_ENABLED(CONFIG_ZMK_BATTERY_REPORTING)
    /* the first battery sample is taken at init; give it up to 1 s */
    for (int i = 0; i < 20 && zmk_battery_state_of_charge() == 0; i++) {
        k_msleep(50);
    }
    struct sl_pattern boot = battery_pattern();
    last_low_warning = k_uptime_get();
    warned_once = true;
    play(&boot);
#endif
#if HOST_BLE || PERIPH_BLE
    if (conn_window_end == 0) { /* no connection event during boot yet */
        sweep_status_leds_show_connection();
    }
#endif

    struct sl_pattern p;
    for (;;) {
        k_msgq_get(&sl_queue, &p, K_FOREVER);
        play(&p);
    }
}

K_THREAD_DEFINE(sweep_status_leds_tid, CONFIG_SWEEP_STATUS_LEDS_STACK_SIZE, sl_thread, NULL, NULL,
                NULL, CONFIG_SWEEP_STATUS_LEDS_PRIORITY, 0, 100);

/* ---- events ---- */

static int sl_listener(const zmk_event_t *eh) {
    const struct zmk_activity_state_changed *act = as_zmk_activity_state_changed(eh);
    if (act) {
        if (act->state == ZMK_ACTIVITY_SLEEP) {
            atomic_set(&suspended, 1);
            k_msgq_purge(&sl_queue);
#if HOST_BLE || PERIPH_BLE
            k_work_cancel_delayable(&conn_work);
#endif
            set_leds(0);
        } else {
            atomic_set(&suspended, 0);
        }
        return ZMK_EV_EVENT_BUBBLE;
    }

#if IS_ENABLED(CONFIG_ZMK_BATTERY_REPORTING)
    const struct zmk_battery_state_changed *bat = as_zmk_battery_state_changed(eh);
    if (bat) {
        int64_t now = k_uptime_get();
        if (bat->state_of_charge > 0 &&
            bat->state_of_charge <= CONFIG_SWEEP_STATUS_LEDS_BATTERY_LOW &&
            (!warned_once ||
             now - last_low_warning >= CONFIG_SWEEP_STATUS_LEDS_LOW_WARN_INTERVAL_S * 1000LL)) {
            last_low_warning = now;
            warned_once = true;
            enqueue(battery_pattern());
        }
        return ZMK_EV_EVENT_BUBBLE;
    }
#endif

#if HOST_BLE
    if (as_zmk_ble_active_profile_changed(eh)) {
        sweep_status_leds_show_connection();
        return ZMK_EV_EVENT_BUBBLE;
    }
#endif
#if PERIPH_BLE
    if (as_zmk_split_peripheral_status_changed(eh)) {
        sweep_status_leds_show_connection();
        return ZMK_EV_EVENT_BUBBLE;
    }
#endif
#if IS_ENABLED(CONFIG_SWEEP_STATUS_LEDS_LAYER)
    if (as_zmk_layer_state_changed(eh)) {
        uint8_t mask = sl_layer_mask(zmk_keymap_highest_layer_active());
        if (atomic_set(&bg_mask, mask) != mask) {
            enqueue((struct sl_pattern){.count = 0}); /* thread re-applies bg_mask */
        }
        return ZMK_EV_EVENT_BUBBLE;
    }
#endif
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(sweep_status_leds, sl_listener);
ZMK_SUBSCRIPTION(sweep_status_leds, zmk_activity_state_changed);
#if IS_ENABLED(CONFIG_ZMK_BATTERY_REPORTING)
ZMK_SUBSCRIPTION(sweep_status_leds, zmk_battery_state_changed);
#endif
#if HOST_BLE
ZMK_SUBSCRIPTION(sweep_status_leds, zmk_ble_active_profile_changed);
#endif
#if PERIPH_BLE
ZMK_SUBSCRIPTION(sweep_status_leds, zmk_split_peripheral_status_changed);
#endif
#if IS_ENABLED(CONFIG_SWEEP_STATUS_LEDS_LAYER)
ZMK_SUBSCRIPTION(sweep_status_leds, zmk_layer_state_changed);
#endif
