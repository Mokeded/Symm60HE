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

//---------------------------------------------------------------------+
// Migration Types
//---------------------------------------------------------------------+

// Migration metadata. Each configuration version should have a
// corresponding migration metadata structure.
typedef struct __attribute__((packed)) {
  // Configuration version this migration applies to
  uint16_t version;
  // Size of the global configuration part of the configuration in bytes. This
  // value is also the offset of the first profile configuration.
  uint32_t global_config_size;
  // Size of each profile configuration in bytes
  uint32_t profile_config_size;
  // Migration function for the global configuration. This function should
  // return true if the migration was successful, false otherwise. `dst` and
  // `src` point to the start of the global configuration.
  bool (*global_config_func)(uint8_t *dst, const uint8_t *src);
  // Migration function for each profile configuration. This function should
  // return true if the migration was successful, false otherwise. `dst` and
  // `src` point to the start of the profile configuration.
  bool (*profile_config_func)(uint8_t profile, uint8_t *dst,
                              const uint8_t *src);
} migration_t;

//--------------------------------------------------------------------+
// Persistent Configuration Migration API
//--------------------------------------------------------------------+

/**
 * @brief Try to migrate the persistent configuration to the latest format
 *
 * @return true if migration was successful, false otherwise
 */
bool migration_try_migrate(void);
