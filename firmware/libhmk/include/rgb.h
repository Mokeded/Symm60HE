/*
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the GNU General Public License as published by the Free Software
 * Foundation, either version 3 of the License, or (at your option) any later
 * version.
 */

#pragma once

#include "common.h"

typedef enum {
  RGB_EFFECT_SOLID = 0,
  RGB_EFFECT_BREATHING,
  RGB_EFFECT_RAINBOW,
  RGB_EFFECT_WAVE,
  RGB_EFFECT_COUNT,
} rgb_effect_t;

typedef struct __attribute__((packed)) {
  uint8_t enabled;
  uint8_t effect;
  uint8_t brightness;
  uint8_t speed;
  uint8_t red;
  uint8_t green;
  uint8_t blue;
  uint8_t split_mirror;
} rgb_config_t;

_Static_assert(sizeof(rgb_config_t) == 8, "Invalid rgb_config_t size");

typedef struct __attribute__((packed)) {
  uint8_t red;
  uint8_t green;
  uint8_t blue;
} rgb_pixel_t;

#define DEFAULT_RGB_CONFIG                                                     \
  {                                                                            \
      .enabled = 0,                                                            \
      .effect = RGB_EFFECT_SOLID,                                              \
      .brightness = 64,                                                        \
      .speed = 128,                                                            \
      .red = 91,                                                               \
      .green = 74,                                                             \
      .blue = 232,                                                             \
      .split_mirror = 1,                                                       \
  }

bool rgb_config_valid(const rgb_config_t *config);
void rgb_config_changed(void);
void rgb_init(void);
void rgb_task(void);
