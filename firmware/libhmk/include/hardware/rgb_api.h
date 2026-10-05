/*
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the GNU General Public License as published by the Free Software
 * Foundation, either version 3 of the License, or (at your option) any later
 * version.
 */

#pragma once

#include "rgb.h"

#if defined(RGB_ENABLE)
void rgb_driver_init(void);
void rgb_driver_write(
    const rgb_pixel_t pixels[RGB_NUM_OUTPUTS][RGB_MAX_LED_COUNT],
    const uint16_t led_counts[RGB_NUM_OUTPUTS]);
#endif
