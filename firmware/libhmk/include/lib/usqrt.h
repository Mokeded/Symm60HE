/*
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the GNU General Public License as published by the Free Software
 * Foundation, either version 3 of the License, or (at your option) any later
 * version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
 * details.
 *
 * You should have received a copy of the GNU General Public License along with
 * this program. If not, see <https://www.gnu.org/licenses/>.
 */

#pragma once

#include "common.h"

//--------------------------------------------------------------------+
// Fast Integer Square Root
// Adapted from https://www.azillionmonkeys.com/qed/ulerysqroot.pdf
//--------------------------------------------------------------------+

static uint16_t usqrt16(uint16_t x) {
  uint16_t t, g = 0;

#define USQRT16_STEP(n)                                                        \
  do {                                                                         \
    t = (g << (n + 1)) + (1 << (n << 1));                                      \
    if (x >= t) {                                                              \
      g += 1 << n;                                                             \
      x -= t;                                                                  \
    }                                                                          \
  } while (0)

  USQRT16_STEP(7);
  USQRT16_STEP(6);
  USQRT16_STEP(5);
  USQRT16_STEP(4);
  USQRT16_STEP(3);
  USQRT16_STEP(2);
  USQRT16_STEP(1);
  USQRT16_STEP(0);

#undef USQRT16_STEP

  return g;
}

static uint32_t usqrt32(uint32_t x) {
  uint32_t t, g = 0;

#define USQRT32_STEP(n)                                                        \
  do {                                                                         \
    t = (g << (n + 1)) + (1 << (n << 1));                                      \
    if (x >= t) {                                                              \
      g += 1 << n;                                                             \
      x -= t;                                                                  \
    }                                                                          \
  } while (0)

  USQRT32_STEP(15);
  USQRT32_STEP(14);
  USQRT32_STEP(13);
  USQRT32_STEP(12);
  USQRT32_STEP(11);
  USQRT32_STEP(10);
  USQRT32_STEP(9);
  USQRT32_STEP(8);
  USQRT32_STEP(7);
  USQRT32_STEP(6);
  USQRT32_STEP(5);
  USQRT32_STEP(4);
  USQRT32_STEP(3);
  USQRT32_STEP(2);
  USQRT32_STEP(1);
  USQRT32_STEP(0);

#undef USQRT32_STEP

  return g;
}
