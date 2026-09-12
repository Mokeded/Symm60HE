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

#include "wear_leveling.h"

#include "crc32.h"
#include "hardware/hardware.h"

typedef enum {
  WL_STATUS_FAILED = 0,
  WL_STATUS_OK,
  // Same as WL_STATUS_OK, but the backing store was consolidated while
  // performing the operation
  WL_STATUS_CONSOLIDATED,
} wear_leveling_status_t;

// Reserve 4 bytes of CRC32 checksum for the consolidated data
#define WL_CRC_ADDR WL_VIRTUAL_SIZE
// The write log starts after the CRC32 checksum.
#define WL_LOG_START_ADDR (WL_CRC_ADDR + 4)

uint8_t wl_cache[WL_VIRTUAL_SIZE];

static uint32_t starting_sector;
static uint32_t base_address;
static uint32_t write_address;

/**
 * @brief Erase the flash memory used by the wear leveling module
 *
 * @return true if the erase was successful, false otherwise
 */
__attribute__((always_inline)) static inline bool
wear_leveling_flash_erase(void) {
  for (uint32_t i = starting_sector; i < FLASH_NUM_SECTORS; i++) {
    if (!flash_erase(i))
      return false;
  }

  return true;
}

__attribute__((always_inline)) static inline bool
wear_leveling_flash_read(uint32_t addr, void *buf, uint32_t len) {
  return flash_read(base_address + addr, buf, len);
}

__attribute__((always_inline)) static inline bool
wear_leveling_flash_write(uint32_t addr, const void *buf, uint32_t len) {
  return flash_write(base_address + addr, buf, len);
}

static void wear_leveling_clear_cache(void) {
  // Fill the cache with flash empty values
  uint32_t *wl_cache32 = (uint32_t *)wl_cache;
  for (uint32_t i = 0; i < WL_VIRTUAL_SIZE / 4; i++)
    wl_cache32[i] = FLASH_EMPTY_VAL;
  // Skip the 4 bytes reserved for the CRC32 checksum of the consolidated data.
  write_address = WL_LOG_START_ADDR;
}

/**
 * @brief Update the cache with the consolidated data
 *
 * This function clears the cache if the consolidated data is corrupted.
 *
 * @return Wear leveling status
 */
static wear_leveling_status_t wear_leveling_read_consolidated(void) {
  wear_leveling_status_t status = WL_STATUS_OK;

  // Read the consolidated data from flash
  if (!wear_leveling_flash_read(0, wl_cache, WL_VIRTUAL_SIZE / 4))
    status = WL_STATUS_FAILED;

  if (status != WL_STATUS_FAILED) {
    // Check the CRC32 checksum
    const uint32_t expected = crc32_compute(wl_cache, WL_VIRTUAL_SIZE, 0);
    uint32_t actual;

    if (!wear_leveling_flash_read(WL_CRC_ADDR, &actual, 1) ||
        actual != expected)
      status = WL_STATUS_FAILED;
  }

  if (status == WL_STATUS_FAILED)
    // Clear the cache if the consolidated data is corrupted
    wear_leveling_clear_cache();

  return status;
}

/**
 * @brief Consolidate the cache with the flash memory
 *
 * This function writes the cache to flash and updates the CRC32 checksum.
 * The flash memory must be erased before calling this function.
 *
 * @return Wear leveling status
 */
static wear_leveling_status_t wear_leveling_write_consolidated(void) {
  wear_leveling_status_t status = WL_STATUS_CONSOLIDATED;

  // Write the cache to flash
  if (!wear_leveling_flash_write(0, wl_cache, WL_VIRTUAL_SIZE / 4))
    status = WL_STATUS_FAILED;

  if (status != WL_STATUS_FAILED) {
    // Write the CRC32 checksum
    const uint32_t checksum = crc32_compute(wl_cache, WL_VIRTUAL_SIZE, 0);

    if (!wear_leveling_flash_write(WL_CRC_ADDR, &checksum, 1))
      status = WL_STATUS_FAILED;
  }

  return status;
}

static wear_leveling_status_t wear_leveling_consolidate_force(void) {
  if (!wear_leveling_flash_erase())
    return WL_STATUS_FAILED;

  const wear_leveling_status_t status = wear_leveling_write_consolidated();
  write_address = WL_LOG_START_ADDR;

  return status;
}

static wear_leveling_status_t wear_leveling_consolidate_if_needed(void) {
  if (write_address >= WL_BACKING_STORE_SIZE)
    // Consolidate the cache if the write log is full
    return wear_leveling_consolidate_force();

  return WL_STATUS_OK;
}

/**
 * @brief Replay the write log
 *
 * This function replays the write log to update the cache with the latest
 * changes. The cache must be consolidated before calling this function.
 *
 * @return Wear leveling status
 */
static wear_leveling_status_t wear_leveling_replay_log(void) {
  wear_leveling_status_t status = WL_STATUS_OK;
  uint32_t addr = WL_LOG_START_ADDR;

  while (addr < WL_BACKING_STORE_SIZE) {
    uint32_t value;

    if (!wear_leveling_flash_read(addr, &value, 1)) {
      status = WL_STATUS_FAILED;
      break;
    }
    if (value == FLASH_EMPTY_VAL)
      // No more entries in the write log
      break;
    addr += 4;

    wl_log_entry_t entry;
    entry.raw[0] = value;

    if (entry.fields.len == 0 || entry.fields.len > WL_MAX_BYTES_PER_ENTRY ||
        entry.fields.addr + entry.fields.len > WL_VIRTUAL_SIZE) {
      // The entry is invalid
      status = WL_STATUS_FAILED;
      break;
    }

    if (entry.fields.len > 2) {
      // More data in the second word
      if (!wear_leveling_flash_read(addr, &entry.raw[1], 1)) {
        status = WL_STATUS_FAILED;
        break;
      }
      addr += 4;
    }

    // Update the cache with the entry
    memcpy(wl_cache + entry.fields.addr, entry.fields.data, entry.fields.len);
  }

  write_address = addr;
  if (status == WL_STATUS_FAILED)
    // If the replay failed, we stick with the current cache
    status = wear_leveling_consolidate_force();
  else
    // Otherwise, we consolidate the cache if needed
    status = wear_leveling_consolidate_if_needed();

  return status;
}

static wear_leveling_status_t wear_leveling_append(uint32_t value) {
  // Append the value to the write log
  if (!wear_leveling_flash_write(write_address, &value, 1))
    return WL_STATUS_FAILED;
  write_address += 4;

  return wear_leveling_consolidate_if_needed();
}

static wear_leveling_status_t
wear_leveling_write_raw(uint32_t addr, const void *buf, uint32_t len) {
  const uint8_t *buf8 = buf;

  while (len > 0) {
    const uint32_t write_len = M_MIN(len, WL_MAX_BYTES_PER_ENTRY);
    wl_log_entry_t entry = {0};

    entry.fields.addr = addr;
    entry.fields.len = write_len;
    memcpy(entry.fields.data, buf8, write_len);

    wear_leveling_status_t status = wear_leveling_append(entry.raw[0]);
    if (status != WL_STATUS_OK)
      // If we consolidate the cache, the changes have been applied to the
      // consolidated data so no need to continue the write operation.
      return status;

    if (write_len > 2) {
      // More data in the second word
      status = wear_leveling_append(entry.raw[1]);
      if (status != WL_STATUS_OK)
        // Same as above
        return status;
    }

    addr += write_len;
    buf8 += write_len;
    len -= write_len;
  }

  return WL_STATUS_OK;
}

void wear_leveling_init(void) {
  // Find the first sector from the end of the flash that is large enough to
  // hold the backing store
  uint32_t reserved_size = 0;
  for (uint32_t i = FLASH_NUM_SECTORS; i-- > 0;) {
    reserved_size += flash_sector_size(i);
    if (reserved_size >= WL_BACKING_STORE_SIZE) {
      starting_sector = i;
      break;
    }
  }
  base_address = FLASH_SIZE - reserved_size;
  wear_leveling_clear_cache();

  wear_leveling_status_t status = wear_leveling_read_consolidated();
  if (status != WL_STATUS_FAILED)
    status = wear_leveling_replay_log();
  else
    // If the consolidated data is corrupted, we clear the virtual storage
    status = wear_leveling_erase();

  if (status == WL_STATUS_FAILED)
    board_error_handler();
}

bool wear_leveling_erase(void) {
  wear_leveling_clear_cache();

  return wear_leveling_consolidate_force() != WL_STATUS_FAILED;
}

bool wear_leveling_read(uint32_t addr, void *buf, uint32_t len) {
  if (addr + len > WL_VIRTUAL_SIZE)
    return false;

  memcpy(buf, wl_cache + addr, len);

  return true;
}

bool wear_leveling_write(uint32_t addr, const void *buf, uint32_t len) {
  if (addr + len > WL_VIRTUAL_SIZE)
    return false;

  const uint8_t *buf8 = buf;

  // Trim the start and end of the buffer
  while (len > 0 && *buf8 == wl_cache[addr]) {
    buf8++;
    addr++;
    len--;
  }
  while (len > 0 && buf8[len - 1] == wl_cache[addr + len - 1])
    len--;

  if (len == 0)
    // No need to write anything
    return true;

  // Update the cache first so if the cache is consolidated, we don't need to
  // continue the write operation
  memcpy(wl_cache + addr, buf8, len);

  wear_leveling_status_t status = wear_leveling_write_raw(addr, buf8, len);
  if (status == WL_STATUS_OK)
    status = wear_leveling_consolidate_if_needed();

  return status != WL_STATUS_FAILED;
}
