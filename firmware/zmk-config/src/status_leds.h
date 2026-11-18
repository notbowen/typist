#pragma once

/* Show this half's battery level (1-4 LEDs for CONFIG_SWEEP_STATUS_LEDS_BATTERY_MS). */
void sweep_status_leds_show_battery(void);
/* Show the connection state again and restart the 'searching' timeout window. */
void sweep_status_leds_show_connection(void);
