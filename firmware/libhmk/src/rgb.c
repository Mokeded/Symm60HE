/*
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the GNU General Public License as published by the Free Software
 * Foundation, either version 3 of the License, or (at your option) any later
 * version.
 */

#include "rgb.h"

#if defined(RGB_ENABLE)

#include "eeconfig.h"
#include "hardware/hardware.h"
#include "hardware/rgb_api.h"

static const uint16_t led_counts[RGB_NUM_OUTPUTS] = RGB_LED_COUNTS;
static rgb_pixel_t pixels[RGB_NUM_OUTPUTS][RGB_MAX_LED_COUNT];
static bool dirty;
static uint32_t last_frame_time;

static rgb_pixel_t rgb_wheel(uint8_t position) {
  if (position < 85) {
    return (rgb_pixel_t){
        .red = (uint8_t)(255 - position * 3),
        .green = (uint8_t)(position * 3),
        .blue = 0,
    };
  }
  if (position < 170) {
    position = (uint8_t)(position - 85);
    return (rgb_pixel_t){
        .red = 0,
        .green = (uint8_t)(255 - position * 3),
        .blue = (uint8_t)(position * 3),
    };
  }

  position = (uint8_t)(position - 170);
  return (rgb_pixel_t){
      .red = (uint8_t)(position * 3),
      .green = 0,
      .blue = (uint8_t)(255 - position * 3),
  };
}

static uint8_t triangle_wave(uint8_t position) {
  if (position < 128)
    return (uint8_t)(position * 2);
  return (uint8_t)((255 - position) * 2);
}

static uint8_t scale_channel(uint8_t channel, uint8_t scale) {
  return (uint8_t)(((uint16_t)channel * scale + 127) / 255);
}

static void apply_current_limit(void) {
  uint32_t channel_sum = 0;
  for (uint32_t output = 0; output < RGB_NUM_OUTPUTS; output++) {
    for (uint32_t led = 0; led < led_counts[output]; led++) {
      channel_sum += pixels[output][led].red;
      channel_sum += pixels[output][led].green;
      channel_sum += pixels[output][led].blue;
    }
  }

  const uint32_t estimated_ma =
      (channel_sum * RGB_CHANNEL_CURRENT_MA + 254) / 255;
  if (estimated_ma <= RGB_CURRENT_LIMIT_MA || estimated_ma == 0)
    return;

  const uint8_t limiter =
      (uint8_t)M_MIN(255, RGB_CURRENT_LIMIT_MA * 255 / estimated_ma);
  for (uint32_t output = 0; output < RGB_NUM_OUTPUTS; output++) {
    for (uint32_t led = 0; led < led_counts[output]; led++) {
      pixels[output][led].red =
          scale_channel(pixels[output][led].red, limiter);
      pixels[output][led].green =
          scale_channel(pixels[output][led].green, limiter);
      pixels[output][led].blue =
          scale_channel(pixels[output][led].blue, limiter);
    }
  }
}

static void render_frame(uint32_t now) {
  const rgb_config_t *config = &eeconfig->rgb;
  memset(pixels, 0, sizeof(pixels));
  if (!config->enabled)
    return;

  uint8_t animation_phase =
      (uint8_t)(((now / 8) * ((uint32_t)config->speed + 16)) >> 7);
  uint8_t frame_brightness = config->brightness;
  if (config->effect == RGB_EFFECT_BREATHING) {
    const uint8_t breath = triangle_wave(animation_phase);
    frame_brightness =
        scale_channel(config->brightness, (uint8_t)(32 + breath * 7 / 8));
  }

  for (uint32_t output = 0; output < RGB_NUM_OUTPUTS; output++) {
    for (uint32_t led = 0; led < led_counts[output]; led++) {
      uint32_t effect_led = led;
      if (config->split_mirror && (output & 1u))
        effect_led = led_counts[output] - 1 - led;

      rgb_pixel_t color = {
          .red = config->red,
          .green = config->green,
          .blue = config->blue,
      };
      uint8_t led_brightness = frame_brightness;

      if (config->effect == RGB_EFFECT_RAINBOW) {
        color = rgb_wheel((uint8_t)(animation_phase + effect_led * 7));
      } else if (config->effect == RGB_EFFECT_WAVE) {
        const uint8_t wave =
            triangle_wave((uint8_t)(animation_phase + effect_led * 12));
        led_brightness =
            scale_channel(frame_brightness, (uint8_t)(24 + wave * 231 / 255));
      }

      pixels[output][led] = (rgb_pixel_t){
          .red = scale_channel(color.red, led_brightness),
          .green = scale_channel(color.green, led_brightness),
          .blue = scale_channel(color.blue, led_brightness),
      };
    }
  }

  apply_current_limit();
}

bool rgb_config_valid(const rgb_config_t *config) {
  return config && config->enabled <= 1 &&
         config->effect < RGB_EFFECT_COUNT && config->split_mirror <= 1;
}

void rgb_config_changed(void) { dirty = true; }

void rgb_init(void) {
  rgb_driver_init();
  dirty = true;
  last_frame_time = 0;
}

void rgb_task(void) {
  const uint32_t now = timer_read();
  const bool animated = eeconfig->rgb.enabled &&
                        eeconfig->rgb.effect != RGB_EFFECT_SOLID;
  const uint32_t frame_interval = 1000 / RGB_REFRESH_HZ;
  if (!dirty && (!animated || now - last_frame_time < frame_interval))
    return;

  render_frame(now);
  rgb_driver_write(pixels, led_counts);
  last_frame_time = now;
  dirty = false;
}

#else

bool rgb_config_valid(const rgb_config_t *config) { return false; }
void rgb_config_changed(void) {}
void rgb_init(void) {}
void rgb_task(void) {}

#endif
