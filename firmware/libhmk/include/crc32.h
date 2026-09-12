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
// CRC32 API
//--------------------------------------------------------------------+

/**
 * @brief Initialize the CRC32 module
 *
 * A default implementation is provided but can be overriden.
 * acceleration.
 *
 * @return None
 */
void crc32_init(void);

/**
 * @brief Compute the CRC32 of a buffer
 *
 * A default implementation is provided but can be overridden. There is no
 * requirement to output the same CRC32 value as the default implementation
 * since it is only used for checking the integrity of the data.
 *
 * @param buf Pointer to the buffer
 * @param len Length of the buffer in bytes
 * @param crc Initial CRC value
 *
 * @return CRC32 value
 */
uint32_t crc32_compute(const void *buf, uint32_t len, uint32_t crc);
