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

#include "crc32.h"

// zlib's CRC32 polynomial
#define CRC32_POLY 0xEDB88320

__attribute__((always_inline)) static inline uint32_t crc32_update(uint32_t crc,
                                                                   uint32_t k) {
  crc ^= k;
  for (uint32_t i = 0; i < 32; i++)
    crc = (crc >> 1) ^ (CRC32_POLY & (uint32_t)(-(int32_t)(crc & 1)));

  return crc;
}

__attribute__((weak)) void crc32_init(void) {}

__attribute__((weak)) uint32_t crc32_compute(const void *buf, uint32_t len,
                                             uint32_t crc) {
  const uint8_t *buf8 = buf;
  uint32_t k;

  crc = ~crc;
  for (uint32_t i = len >> 2; i; i--) {
    memcpy(&k, buf8, sizeof(k));
    buf8 += sizeof(k);
    crc = crc32_update(crc, k);
  }

  if (len & 3) {
    k = 0;
    memcpy(&k, buf8, len & 3);
    crc = crc32_update(crc, k);
  }

  return ~crc;
}
