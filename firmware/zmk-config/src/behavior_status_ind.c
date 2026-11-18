/*
 * &status_ind IND_BAT / IND_CON: show battery level / connection state on the
 * status LEDs. Global locality: a press on either half runs on both halves, so
 * each half shows its own battery and its own link.
 */
#define DT_DRV_COMPAT sweep_behavior_status_ind

#include <zephyr/device.h>
#include <drivers/behavior.h>
#include <zephyr/logging/log.h>

#include <zmk/behavior.h>
#include <dt-bindings/sweep/status_leds.h>

#include "status_leds.h"

LOG_MODULE_DECLARE(sweep_status_leds, CONFIG_ZMK_LOG_LEVEL);

#if DT_HAS_COMPAT_STATUS_OKAY(DT_DRV_COMPAT)

static int status_ind_pressed(struct zmk_behavior_binding *binding,
                              struct zmk_behavior_binding_event event) {
    LOG_DBG("&status_ind %s", binding->param1 == IND_BAT ? "IND_BAT" : "IND_CON");
    switch (binding->param1) {
    case IND_BAT:
        sweep_status_leds_show_battery();
        return ZMK_BEHAVIOR_OPAQUE;
    case IND_CON:
        sweep_status_leds_show_connection();
        return ZMK_BEHAVIOR_OPAQUE;
    default:
        LOG_ERR("unknown &status_ind parameter %d", binding->param1);
        return -ENOTSUP;
    }
}

static int status_ind_released(struct zmk_behavior_binding *binding,
                       struct zmk_behavior_binding_event event) {
    return ZMK_BEHAVIOR_OPAQUE;
}

static const struct behavior_driver_api behavior_status_ind_api = {
    .binding_pressed = status_ind_pressed,
    .binding_released = status_ind_released,
    .locality = BEHAVIOR_LOCALITY_GLOBAL,
};

BEHAVIOR_DT_INST_DEFINE(0, NULL, NULL, NULL, NULL, POST_KERNEL,
                        CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &behavior_status_ind_api);

#endif
