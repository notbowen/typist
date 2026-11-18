zephyr_include_directories(include)

if(CONFIG_SWEEP_STATUS_LEDS)
  target_sources(app PRIVATE src/status_leds.c)
  target_sources_ifdef(CONFIG_SWEEP_BEHAVIOR_STATUS_IND app PRIVATE src/behavior_status_ind.c)
endif()
