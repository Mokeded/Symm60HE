/*
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the GNU General Public License as published by the Free Software
 * Foundation, either version 3 of the License, or (at your option) any later
 * version.
 */

#include "hardware/rgb_api.h"

#if defined(RGB_ENABLE)

#include "at32f402_405.h"

static const uint16_t output_pins[RGB_NUM_OUTPUTS] = RGB_OUTPUT_PINS;
static uint16_t output_mask;
static volatile bool transfer_active;

// TMR2 clocks DMA2 at about 2.5 MHz. Each 1.2 us SK6812 bit uses three DMA
// words: raise all active outputs, clear the zero outputs after about 0.4 us,
// then clear the one outputs after about 0.8 us. Writing GPIO SCR only touches
// the two RGB pins; the Hall mux select pins on the same GPIO port continue to
// operate normally. The transfer runs asynchronously, so animated lighting
// does not pause matrix scanning or USB interrupts.
#define RGB_TIMER_FREQUENCY 2500000u
#define RGB_TIMER_CYCLES                                                    \
  ((F_CPU + RGB_TIMER_FREQUENCY / 2u) / RGB_TIMER_FREQUENCY)
#define RGB_TICKS_PER_BIT 3u
#define RGB_BITS_PER_LED 24u
#define RGB_RESET_US 90u
#define RGB_RESET_TICKS                                                     \
  ((RGB_RESET_US * (F_CPU / 1000000u) + RGB_TIMER_CYCLES - 1u) /            \
   RGB_TIMER_CYCLES)
#define RGB_DMA_WORDS                                                       \
  (RGB_MAX_LED_COUNT * RGB_BITS_PER_LED * RGB_TICKS_PER_BIT +               \
   RGB_RESET_TICKS)

_Static_assert(RGB_TIMER_CYCLES > 0, "Invalid RGB timer period");
_Static_assert(RGB_DMA_WORDS <= UINT16_MAX, "RGB DMA buffer is too large");

__attribute__((aligned(4))) static uint32_t waveform[RGB_DMA_WORDS];

static uint8_t pixel_byte(const rgb_pixel_t *pixel, uint8_t component) {
  switch (component) {
  case 0:
    return pixel->green;
  case 1:
    return pixel->red;
  case 2:
    return pixel->blue;
  default:
    return 0;
  }
}

void rgb_driver_init(void) {
  crm_periph_clock_enable(RGB_OUTPUT_PORT_CLOCK, TRUE);
  crm_periph_clock_enable(CRM_DMA2_PERIPH_CLOCK, TRUE);
  crm_periph_clock_enable(CRM_TMR2_PERIPH_CLOCK, TRUE);

  gpio_init_type gpio_init_struct;
  gpio_default_para_init(&gpio_init_struct);
  gpio_init_struct.gpio_pins = 0;
  for (uint32_t output = 0; output < RGB_NUM_OUTPUTS; output++)
    gpio_init_struct.gpio_pins |= output_pins[output];
  output_mask = gpio_init_struct.gpio_pins;
  gpio_init_struct.gpio_mode = GPIO_MODE_OUTPUT;
  gpio_init_struct.gpio_pull = GPIO_PULL_NONE;
  gpio_init_struct.gpio_out_type = GPIO_OUTPUT_PUSH_PULL;
  gpio_init_struct.gpio_drive_strength = GPIO_DRIVE_STRENGTH_STRONGER;
  gpio_init(RGB_OUTPUT_PORT, &gpio_init_struct);
  RGB_OUTPUT_PORT->clr = output_mask;

  // Timer overflow produces one DMA request per waveform tick.
  tmr_base_init(TMR2, RGB_TIMER_CYCLES - 1u, 0);
  tmr_cnt_dir_set(TMR2, TMR_COUNT_UP);
  tmr_dma_request_enable(TMR2, TMR_OVERFLOW_DMA_REQUEST, TRUE);

  dma_init_type dma_init_struct;
  dma_reset(DMA2_CHANNEL1);
  dma_default_para_init(&dma_init_struct);
  dma_init_struct.buffer_size = RGB_DMA_WORDS;
  dma_init_struct.direction = DMA_DIR_MEMORY_TO_PERIPHERAL;
  dma_init_struct.memory_base_addr = (uint32_t)waveform;
  dma_init_struct.memory_data_width = DMA_MEMORY_DATA_WIDTH_WORD;
  dma_init_struct.memory_inc_enable = TRUE;
  dma_init_struct.peripheral_base_addr = (uint32_t)&RGB_OUTPUT_PORT->scr;
  dma_init_struct.peripheral_data_width = DMA_PERIPHERAL_DATA_WIDTH_WORD;
  dma_init_struct.peripheral_inc_enable = FALSE;
  dma_init_struct.priority = DMA_PRIORITY_MEDIUM;
  dma_init_struct.loop_mode_enable = FALSE;
  dma_init(DMA2_CHANNEL1, &dma_init_struct);
  dma_interrupt_enable(DMA2_CHANNEL1, DMA_FDT_INT | DMA_DTERR_INT, TRUE);

  dmamux_enable(DMA2, TRUE);
  dmamux_init(DMA2MUX_CHANNEL1, DMAMUX_DMAREQ_ID_TMR2_OVERFLOW);
  nvic_irq_enable(DMA2_Channel1_IRQn, 3, 0);
}

void rgb_driver_write(
    const rgb_pixel_t pixels[RGB_NUM_OUTPUTS][RGB_MAX_LED_COUNT],
    const uint16_t led_counts[RGB_NUM_OUTPUTS]) {
  // Back-to-back host changes can arrive while the previous frame is still on
  // the wire. This wait is bounded by one roughly 1.1 ms LED frame and is not
  // taken during normal 30 Hz animation updates.
  while (transfer_active)
    ;

  uint32_t index = 0;

  for (uint32_t led = 0; led < RGB_MAX_LED_COUNT; led++) {
    for (uint8_t component = 0; component < 3; component++) {
      for (uint8_t bit = 8; bit > 0; bit--) {
        uint16_t active_mask = 0;
        uint16_t one_mask = 0;
        for (uint32_t output = 0; output < RGB_NUM_OUTPUTS; output++) {
          if (led >= led_counts[output])
            continue;
          active_mask |= output_pins[output];
          if (pixel_byte(&pixels[output][led], component) &
              (1u << (bit - 1u)))
            one_mask |= output_pins[output];
        }

        waveform[index++] = active_mask;
        waveform[index++] =
            (uint32_t)((uint16_t)(active_mask & ~one_mask)) << 16;
        waveform[index++] = (uint32_t)one_mask << 16;
      }
    }
  }

  while (index < RGB_DMA_WORDS)
    waveform[index++] = 0;

  RGB_OUTPUT_PORT->clr = output_mask;
  tmr_counter_enable(TMR2, FALSE);
  dma_channel_enable(DMA2_CHANNEL1, FALSE);
  dma_flag_clear(DMA2_GL1_FLAG);
  dma_data_number_set(DMA2_CHANNEL1, RGB_DMA_WORDS);
  tmr_counter_value_set(TMR2, 0);
  tmr_flag_clear(TMR2, TMR_OVF_FLAG);

  transfer_active = true;
  dma_channel_enable(DMA2_CHANNEL1, TRUE);
  tmr_counter_enable(TMR2, TRUE);
}

//--------------------------------------------------------------------+
// Interrupt Handlers
//--------------------------------------------------------------------+

void DMA2_Channel1_IRQHandler(void) {
  if (dma_interrupt_flag_get(DMA2_FDT1_FLAG) == SET ||
      dma_interrupt_flag_get(DMA2_DTERR1_FLAG) == SET) {
    tmr_counter_enable(TMR2, FALSE);
    dma_channel_enable(DMA2_CHANNEL1, FALSE);
    dma_flag_clear(DMA2_GL1_FLAG);
    RGB_OUTPUT_PORT->clr = output_mask;
    transfer_active = false;
  }
}

#endif
